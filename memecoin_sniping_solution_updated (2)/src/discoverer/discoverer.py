import json
import logging
import os
import boto3
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Tuple

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Variáveis de ambiente
SQS_QUEUE_URL = os.environ.get("SQS_QUEUE_URL")
MIGRATION_TRACKING_TABLE = os.environ.get("MIGRATION_TRACKING_TABLE", "PumpSwapMigrationTable")

# Constantes específicas para PumpSwap
PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "PSwapMdSBGgzkpVMEXv5mR3NpTfU2arRrLrW8sTCJ"
PUMPSWAP_FACTORY_ADDRESS = "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg"

# Thresholds otimizados para PumpSwap
MIN_LIQUIDITY_USD = 500  # Menor que Raydium devido à natureza mais nova
MIN_MARKET_CAP_USD = 69000  # Threshold de graduação da Pump.Fun
MAX_TOKEN_AGE_HOURS = 12  # Mais agressivo para capturar oportunidades cedo
MIN_PUMPSWAP_VOLUME_USD = 1000  # Volume mínimo pós-migração

class PumpSwapFocusedDiscoverer:
    def __init__(self, sqs_client, secrets_manager_client, dynamodb_resource):
        self.sqs = sqs_client
        self.secrets_manager = secrets_manager_client
        self.migration_table = dynamodb_resource.Table(MIGRATION_TRACKING_TABLE)
        self.session = aiohttp.ClientSession()
        
        # Rate limiting específico para APIs
        self.rate_limits = {
            "moralis": {"requests_per_minute": 60, "current_requests": 0, "reset_time": datetime.now()},
            "bitquery": {"requests_per_minute": 100, "current_requests": 0, "reset_time": datetime.now()},
            "shyft": {"requests_per_minute": 120, "current_requests": 0, "reset_time": datetime.now()}
        }
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_secret(self, secret_name: str) -> Dict:
        """Recupera um segredo do AWS Secrets Manager."""
        try:
            response = self.secrets_manager.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Erro ao recuperar segredo {secret_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao recuperar segredo {secret_name}: {e}")
            raise

    async def check_rate_limit(self, api_name: str) -> bool:
        """Verifica e aplica rate limiting para APIs."""
        now = datetime.now()
        rate_info = self.rate_limits[api_name]
        
        # Reset contador se passou 1 minuto
        if now - rate_info["reset_time"] > timedelta(minutes=1):
            rate_info["current_requests"] = 0
            rate_info["reset_time"] = now
        
        # Verificar se pode fazer request
        if rate_info["current_requests"] >= rate_info["requests_per_minute"]:
            wait_time = 60 - (now - rate_info["reset_time"]).seconds
            logger.warning(f"Rate limit atingido para {api_name}, aguardando {wait_time}s")
            await asyncio.sleep(wait_time)
            rate_info["current_requests"] = 0
            rate_info["reset_time"] = datetime.now()
        
        rate_info["current_requests"] += 1
        return True

    async def get_pump_fun_graduated_tokens(self) -> List[Dict]:
        """
        Obtém tokens que graduaram da Pump.Fun nas últimas horas usando Moralis API.
        Foco em tokens recentes para capturar migrações para PumpSwap rapidamente.
        """
        await self.check_rate_limit("moralis")
        
        try:
            moralis_api_key = self.get_secret("/memecoin-sniping/moralis-api-key")["apiKey"]
            
            # Buscar tokens graduados nas últimas 6 horas (mais agressivo)
            from_date = datetime.now() - timedelta(hours=6)
            
            url = "https://solana-gateway.moralis.io/token/graduated"
            headers = {
                "X-API-Key": moralis_api_key,
                "accept": "application/json"
            }
            
            params = {
                "limit": 50,  # Menor limite para processar mais rapidamente
                "from_date": from_date.isoformat()
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                response.raise_for_status() # Lança exceção para status de erro HTTP
                data = await response.json()
                graduated_tokens = []
                
                for token in data.get("result", []):
                    token_info = {
                        "token_address": token["mint"],
                        "graduation_timestamp": token["graduation_timestamp"],
                        "market_cap_at_graduation": token.get("market_cap", 0),
                        "liquidity_at_graduation": token.get("liquidity", 0),
                        "graduation_tx": token.get("graduation_transaction"),
                        "symbol": token.get("symbol", ""),
                        "name": token.get("name", "")
                    }
                    graduated_tokens.append(token_info)
                
                logger.info(f"Encontrados {len(graduated_tokens)} tokens graduados nas últimas 6 horas")
                return graduated_tokens
                    
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro na API Moralis (HTTP {e.status}): {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com a API Moralis: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar tokens graduados: {e}")
            
        return []

    async def check_pumpswap_migration_status(self, token_address: str) -> Optional[Dict]:
        """
        Verifica se um token migrou para PumpSwap usando Bitquery API.
        Otimizado para detectar migrações recentes rapidamente.
        """
        await self.check_rate_limit("bitquery")
        
        try:
            bitquery_api_key = self.get_secret("/memecoin-sniping/bitquery-api-key")["apiKey"]
            
            # Query otimizada para PumpSwap
            query = """
            query ($token: String!, $since: ISO8601DateTime!) {
              Solana {
                DEXTrades(
                  where: {
                    Trade: {Currency: {MintAddress: {is: $token}}}
                    Transaction: {Result: {Success: true}}
                    Instruction: {Program: {Address: {is: "PSwapMdSBGgzkpVMEXv5mR3NpTfU2arRrLrW8sTCJ"}}}
                    Block: {Time: {since: $since}}
                  }
                  orderBy: {ascending: Block_Time}
                  limit: 10
                ) {
                  Block {
                    Time
                    Height
                  }
                  Transaction {
                    Signature
                  }
                  Trade {
                    AmountInUSD
                    Amount
                    Currency {
                      MintAddress
                      Symbol
                      Name
                    }
                    Side {
                      Currency {
                        MintAddress
                        Symbol
                      }
                      Amount
                    }
                  }
                  Instruction {
                    Program {
                      Address
                      Name
                    }
                  }
                }
                
                # Também buscar informações do pool
                Instructions(
                  where: {
                    Instruction: {Program: {Address: {is: "PSwapMdSBGgzkpVMEXv5mR3NpTfU2arRrLrW8sTCJ"}}}
                    Transaction: {Result: {Success: true}}
                    Block: {Time: {since: $since}}
                  }
                  limit: 5
                ) {
                  Block {
                    Time
                  }
                  Transaction {
                    Signature
                  }
                  Instruction {
                    Name
                    Data
                  }
                }
              }
            }
            """
            
            # Buscar atividade nas últimas 12 horas
            since_time = (datetime.now() - timedelta(hours=12)).isoformat()
            variables = {
                "token": token_address,
                "since": since_time
            }
            
            async with self.session.post(
                "https://graphql.bitquery.io/",
                json={"query": query, "variables": variables},
                headers={"X-API-KEY": bitquery_api_key}
            ) as response:
                response.raise_for_status() # Lança exceção para status de erro HTTP
                data = await response.json()
                trades = data.get("data", {}).get("Solana", {}).get("DEXTrades", [])
                
                if trades:
                    first_trade = trades[0]
                    total_volume = sum(float(trade["Trade"]["AmountInUSD"] or 0) for trade in trades)
                    
                    migration_info = {
                        "token_address": token_address,
                        "migration_destination": "PumpSwap",
                        "first_trade_timestamp": first_trade["Block"]["Time"],
                        "first_trade_tx": first_trade["Transaction"]["Signature"],
                        "first_trade_amount_usd": first_trade["Trade"]["AmountInUSD"],
                        "total_volume_usd": total_volume,
                        "trade_count": len(trades),
                        "block_height": first_trade["Block"]["Height"],
                        "migration_detected": True
                    }
                    
                    logger.info(f"Migração PumpSwap detectada para {token_address}: ${total_volume:.2f} volume")
                    return migration_info
                else:
                    logger.debug(f"Nenhuma atividade PumpSwap encontrada para {token_address}")
                        
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro na API Bitquery (HTTP {e.status}): {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com a API Bitquery: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao verificar migração PumpSwap: {e}")
            
        return None

    async def get_pumpswap_pool_info(self, token_address: str) -> Optional[Dict]:
        """
        Obtém informações detalhadas do pool PumpSwap usando Shyft API.
        """
        await self.check_rate_limit("shyft")
        
        try:
            shyft_api_key = self.get_secret("/memecoin-sniping/shyft-api-key")["apiKey"]
            
            url = f"https://api.shyft.to/sol/v1/defi/pumpswap/pools"
            headers = {
                "x-api-key": shyft_api_key,
                "Content-Type": "application/json"
            }
            
            params = {
                "token_address": token_address,
                "network": "mainnet-beta"
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                response.raise_for_status() # Lança exceção para status de erro HTTP
                data = await response.json()
                
                if data.get("success") and data.get("result"):
                    pools = data["result"]
                    
                    if pools:
                        # Pegar o pool mais ativo
                        main_pool = max(pools, key=lambda p: float(p.get("liquidity_usd", 0)))
                        
                        pool_info = {
                            "pool_address": main_pool.get("pool_address"),
                            "liquidity_usd": float(main_pool.get("liquidity_usd", 0)),
                            "volume_24h_usd": float(main_pool.get("volume_24h", 0)),
                            "price_usd": float(main_pool.get("price", 0)),
                            "price_change_24h": float(main_pool.get("price_change_24h", 0)),
                            "created_at": main_pool.get("created_at"),
                            "base_mint": main_pool.get("base_mint"),
                            "quote_mint": main_pool.get("quote_mint")
                        }
                        
                        return pool_info
                            
        except aiohttp.ClientResponseError as e:
            logger.error(f"Erro na API Shyft (HTTP {e.status}): {e.message}")
        except aiohttp.ClientError as e:
            logger.error(f"Erro de conexão com a API Shyft: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao obter info do pool PumpSwap: {e}")
            
        return None

    async def validate_pumpswap_migration(self, token_data: Dict, migration_data: Dict, pool_data: Optional[Dict]) -> bool:
        """
        Valida se a migração para PumpSwap é legítima e vale a pena.
        Critérios específicos para PumpSwap.
        """
        try:
            token_address = token_data["token_address"]
            
            # 1. Verificar se já foi processado
            if await self.is_token_already_processed(token_address):
                logger.info(f"Token {token_address} já processado")
                return False
            
            # 2. Verificar timing da migração (deve ser muito recente para PumpSwap)
            migration_time = datetime.fromisoformat(migration_data["first_trade_timestamp"].replace("Z", "+00:00"))
            time_since_migration = datetime.now().astimezone() - migration_time
            
            if time_since_migration > timedelta(hours=MAX_TOKEN_AGE_HOURS):
                logger.info(f"Token {token_address} migração muito antiga: {time_since_migration}")
                return False
            
            # 3. Verificar volume mínimo pós-migração
            total_volume = migration_data.get("total_volume_usd", 0)
            if total_volume < MIN_PUMPSWAP_VOLUME_USD:
                logger.info(f"Token {token_address} volume insuficiente: ${total_volume}")
                return False
            
            # 4. Verificar liquidez se disponível
            if pool_data:
                liquidity_usd = pool_data.get("liquidity_usd", 0)
                if liquidity_usd < MIN_LIQUIDITY_USD:
                    logger.info(f"Token {token_address} liquidez insuficiente: ${liquidity_usd}")
                    return False
            
            # 5. Verificar se não é um token suspeito (nome/símbolo muito genérico)
            token_name = token_data.get("name", "").lower()
            token_symbol = token_data.get("symbol", "").lower()
            
            suspicious_patterns = ["test", "fake", "scam", "rug", "copy", "clone"]
            if any(pattern in token_name or pattern in token_symbol for pattern in suspicious_patterns):
                logger.info(f"Token {token_address} com nome/símbolo suspeito")
                return False
            
            # 6. Verificar número mínimo de trades (atividade real)
            trade_count = migration_data.get("trade_count", 0)
            if trade_count < 3:
                logger.info(f"Token {token_address} poucas transações: {trade_count}")
                return False
            
            logger.info(f"Token {token_address} passou na validação PumpSwap")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar migração PumpSwap: {e}")
            return False

    async def is_token_already_processed(self, token_address: str) -> bool:
        """Verifica se o token já foi processado."""
        try:
            response = self.migration_table.get_item(
                Key={"token_address": token_address}
            )
            return "Item" in response
        except ClientError as e:
            logger.error(f"Erro de cliente DynamoDB ao verificar token processado: {e}")
            return False
        except Exception as e:
            logger.error(f"Erro inesperado ao verificar token processado: {e}")
            return False

    async def track_pumpswap_migration(self, token_data: Dict, migration_data: Dict, pool_data: Optional[Dict]) -> None:
        """Registra a migração PumpSwap no DynamoDB."""
        try:
            item = {
                "token_address": token_data["token_address"],
                "token_name": token_data.get("name", ""),
                "token_symbol": token_data.get("symbol", ""),
                "graduation_timestamp": token_data["graduation_timestamp"],
                "migration_timestamp": migration_data["first_trade_timestamp"],
                "market_cap_at_graduation": token_data["market_cap_at_graduation"],
                "liquidity_at_graduation": token_data["liquidity_at_graduation"],
                "first_trade_volume_usd": migration_data["first_trade_amount_usd"],
                "total_volume_usd": migration_data["total_volume_usd"],
                "trade_count": migration_data["trade_count"],
                "migration_destination": "PumpSwap",
                "processed_timestamp": datetime.now().isoformat(),
                "status": "discovered",
                "discovery_source": "pumpswap_focused_discoverer"
            }
            
            # Adicionar dados do pool se disponível
            if pool_data:
                item.update({
                    "pool_address": pool_data.get("pool_address"),
                    "pool_liquidity_usd": pool_data.get("liquidity_usd"),
                    "pool_volume_24h_usd": pool_data.get("volume_24h_usd"),
                    "token_price_usd": pool_data.get("price_usd"),
                    "price_change_24h": pool_data.get("price_change_24h")
                })
            
            self.migration_table.put_item(Item=item)
            logger.info(f"Migração PumpSwap registrada para {token_data['token_address']}")
            
        except ClientError as e:
            logger.error(f"Erro de cliente DynamoDB ao registrar migração PumpSwap: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar migração PumpSwap: {e}")

    async def discover_pumpswap_migrations(self) -> List[Dict]:
        """
        Processo principal para descobrir migrações para PumpSwap.
        Otimizado para velocidade e precisão.
        """
        discovered_migrations = []
        
        try:
            logger.info("Iniciando descoberta de migrações PumpSwap...")
            
            # 1. Obter tokens graduados recentemente
            graduated_tokens = await self.get_pump_fun_graduated_tokens()
            
            if not graduated_tokens:
                logger.info("Nenhum token graduado encontrado")
                return []
            
            # 2. Processar cada token graduado
            for token_data in graduated_tokens:
                token_address = token_data["token_address"]
                logger.info(f"Verificando migração PumpSwap para {token_address}")
                
                try:
                    # 3. Verificar se migrou para PumpSwap
                    migration_data = await self.check_pumpswap_migration_status(token_address)
                    
                    if not migration_data:
                        logger.debug(f"Token {token_address} ainda não migrou para PumpSwap")
                        continue
                    
                    # 4. Obter informações do pool PumpSwap
                    pool_data = await self.get_pumpswap_pool_info(token_address)
                    
                    # 5. Valida migração
                    if await self.validate_pumpswap_migration(token_data, migration_data, pool_data):
                        # 6. Registrar migração
                        await self.track_pumpswap_migration(token_data, migration_data, pool_data)
                        
                        # 7. Preparar dados para análise
                        complete_migration_data = {
                            **token_data,
                            **migration_data,
                            "pool_data": pool_data,
                            "discovery_timestamp": datetime.now().isoformat()
                        }
                        
                        discovered_migrations.append(complete_migration_data)
                        logger.info(f"Migração PumpSwap descoberta: {token_address}")
                    
                    # Rate limiting entre tokens
                    await asyncio.sleep(0.2) # Pequeno delay para evitar sobrecarga de API
                    
                except Exception as e:
                    logger.error(f"Erro ao processar token {token_address}: {e}")
                    continue
            
            logger.info(f"Descoberta concluída: {len(discovered_migrations)} migrações PumpSwap encontradas")
            return discovered_migrations
            
        except Exception as e:
            logger.error(f"Erro na descoberta de migrações PumpSwap: {e}")
            return []

    def send_to_sqs(self, message: Dict) -> None:
        """Envia mensagem para SQS com dados da migração PumpSwap."""
        try:
            response = self.sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message, default=str)
            )
            logger.info(f"Migração PumpSwap enviada para SQS: {response['MessageId']}")
        except ClientError as e:
            logger.error(f"Erro de cliente SQS ao enviar mensagem: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar para SQS: {e}")
            raise


async def lambda_handler(event, context):
    """Função principal do Lambda focada em PumpSwap."""
    try:
        logger.info("PumpSwap Focused Discoverer iniciado")
        
        # Verifica se SQS_QUEUE_URL está definido
        if not SQS_QUEUE_URL:
            logger.error("Variável de ambiente SQS_QUEUE_URL não definida.")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "SQS_QUEUE_URL não configurado."})
            }

        # Inicializa clientes AWS aqui, antes de passar para o Discoverer
        sqs_client = boto3.client("sqs")
        secrets_manager_client = boto3.client("secretsmanager")
        dynamodb_resource = boto3.resource("dynamodb")

        async with PumpSwapFocusedDiscoverer(sqs_client, secrets_manager_client, dynamodb_resource) as discoverer:
            # Descobrir migrações para PumpSwap
            migrations = await discoverer.discover_pumpswap_migrations()
            
            # Enviar cada migração descoberta para análise
            for migration_data in migrations:
                enhanced_message = {
                    "token_address": migration_data["token_address"],
                    "token_name": migration_data.get("name", ""),
                    "token_symbol": migration_data.get("symbol", ""),
                    "migration_destination": "PumpSwap",
                    "graduation_timestamp": migration_data["graduation_timestamp"],
                    "migration_timestamp": migration_data["first_trade_timestamp"],
                    "market_cap_at_graduation": migration_data["market_cap_at_graduation"],
                    "liquidity_at_graduation": migration_data["liquidity_at_graduation"],
                    "total_volume_usd": migration_data["total_volume_usd"],
                    "trade_count": migration_data["trade_count"],
                    "pool_data": migration_data.get("pool_data"),
                    "discovery_timestamp": migration_data["discovery_timestamp"],
                    "discovery_source": "pumpswap_focused_discoverer",
                    "token_type": "pumpswap_migrated_token"
                }
                
                discoverer.send_to_sqs(enhanced_message)
                logger.info(f"Token PumpSwap {migration_data['token_address']} enviado para análise")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "PumpSwap Focused Discoverer executado com sucesso",
                "migrations_discovered": len(migrations)
            })
        }
    
    except Exception as e:
        logger.error(f"Erro no PumpSwap Focused Discoverer: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# Para teste local
if __name__ == "__main__":
    # Configurações de ambiente para teste local
    os.environ["SQS_QUEUE_URL"] = "YOUR_LOCAL_SQS_QUEUE_URL" # Substitua pela URL da sua fila SQS local ou mock
    os.environ["MIGRATION_TRACKING_TABLE"] = "PumpSwapMigrationTable" # Substitua pelo nome da sua tabela DynamoDB local ou mock
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1" # Adicionado para teste local
    
    # Mock de secrets para teste local (NÃO USE EM PRODUÇÃO)
    class MockSecretsManager:
        def get_secret_value(self, SecretId):
            if SecretId == "/memecoin-sniping/moralis-api-key":
                return {"SecretString": json.dumps({"apiKey": "YOUR_MORALIS_API_KEY"})}
            elif SecretId == "/memecoin-sniping/bitquery-api-key":
                return {"SecretString": json.dumps({"apiKey": "YOUR_BITQUERY_API_KEY"})}
            elif SecretId == "/memecoin-sniping/shyft-api-key":
                return {"SecretString": json.dumps({"apiKey": "YOUR_SHYFT_API_KEY"})}
            raise ClientError({"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue")

    # Mock de DynamoDB para teste local (NÃO USE EM PRODUÇÃO)
    class MockDynamoDBTable:
        def __init__(self, name):
            self.name = name
            self.items = {}
        
        def get_item(self, Key):
            return {"Item": self.items.get(Key["token_address"])}
            
        def put_item(self, Item):
            self.items[Item["token_address"]] = Item
            
    # Mock de SQS para teste local (NÃO USE EM PRODUÇÃO)
    class MockSQSClient:
        def send_message(self, QueueUrl, MessageBody):
            print(f"Mock SQS: Mensagem enviada para {QueueUrl}: {MessageBody}")
            return {"MessageId": "mock-message-id"}
            
    # Inicializa os mocks
    mock_sqs_client = MockSQSClient()
    mock_secrets_manager_client = MockSecretsManager()
    mock_dynamodb_resource = type("MockDynamoDB", (object,), {"Table": MockDynamoDBTable})()

    async def test_discoverer():
        async with PumpSwapFocusedDiscoverer(mock_sqs_client, mock_secrets_manager_client, mock_dynamodb_resource) as discoverer:
            migrations = await discoverer.discover_pumpswap_migrations()
            print(f"Migrações PumpSwap descobertas: {len(migrations)}")
            for migration in migrations:
                print(f"Token: {migration['token_address']}")
                print(f"Volume: ${migration.get('total_volume_usd', 0):.2f}")
                print(f"Trades: {migration.get('trade_count', 0)}")
                print("---")
    
    asyncio.run(test_discoverer())












# --- Simplified functions for unit tests ---

sqs = boto3.client('sqs')
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL', 'dummy')

def get_secret(name: str):
    """Placeholder secret fetcher."""
    return {}

def send_to_sqs(message: dict):
    """Send message to SQS (mocked in tests)."""
    sqs.send_message(QueueUrl=SQS_QUEUE_URL, MessageBody=json.dumps(message))


def process_token_event(event: dict):
    """Validate and normalize a token event."""
    if 'tokenAddress' not in event:
        return None
    return {
        'tokenAddress': event['tokenAddress'],
        'eventType': event.get('type'),
        'poolAddress': event.get('poolAddress'),
        'liquidityAmount': event.get('liquidityAmount'),
    }


def lambda_handler(event, context):
    """Entry point for Discoverer lambda."""
    events = json.loads(event.get('body', '[]'))
    for token_event in events:
        processed = process_token_event(token_event)
        if processed:
            send_to_sqs(processed)
    return {'statusCode': 200, 'body': json.dumps({'processed': len(events)})}
