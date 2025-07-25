import json
import logging
import os
import boto3
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from typing import Dict, List, Optional, Tuple

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
sqs = boto3.client('sqs')
secrets_manager = boto3.client('secretsmanager')
dynamodb = boto3.resource('dynamodb')

# Variáveis de ambiente
SQS_QUEUE_URL = os.environ.get('SQS_QUEUE_URL')
HELIUS_API_SECRET_NAME = os.environ.get('HELIUS_API_SECRET_NAME', '/memecoin-sniping/helius-api-key')
MIGRATION_TRACKING_TABLE = os.environ.get('MIGRATION_TRACKING_TABLE', 'MigrationTrackingTable')

# Constantes para identificação de migração
PUMP_FUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "PSwapMdSBGgzkpVMEXv5mR3NpTfU2arRrLrW8sTCJ"
RAYDIUM_AMM_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"

# Thresholds para filtros
MIN_LIQUIDITY_USD = 1000
MIN_MARKET_CAP_USD = 69000  # Threshold de graduação da Pump.Fun
MAX_TOKEN_AGE_HOURS = 24

class EnhancedDiscoverer:
    def __init__(self):
        self.migration_table = dynamodb.Table(MIGRATION_TRACKING_TABLE)
        self.session = aiohttp.ClientSession()
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_secret(self, secret_name: str) -> Dict:
        """Recupera um segredo do AWS Secrets Manager."""
        try:
            response = secrets_manager.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            logger.error(f"Erro ao recuperar segredo {secret_name}: {e}")
            raise

    async def check_pump_fun_graduation(self, token_address: str) -> Optional[Dict]:
        """
        Verifica se um token graduou da Pump.Fun usando a API Moralis.
        Retorna informações de graduação se encontrado.
        """
        try:
            # Usar API Moralis para verificar tokens graduados
            moralis_api_key = self.get_secret('/memecoin-sniping/moralis-api-key')['apiKey']
            
            url = f"https://solana-gateway.moralis.io/token/{token_address}/graduated"
            headers = {
                'X-API-Key': moralis_api_key,
                'accept': 'application/json'
            }
            
            async with self.session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Verificar se o token realmente graduou
                    if data.get('graduated', False):
                        return {
                            'token_address': token_address,
                            'graduation_timestamp': data.get('graduation_timestamp'),
                            'market_cap_at_graduation': data.get('market_cap'),
                            'liquidity_at_graduation': data.get('liquidity'),
                            'graduation_tx': data.get('graduation_transaction')
                        }
                        
        except Exception as e:
            logger.error(f"Erro ao verificar graduação do token {token_address}: {e}")
            
        return None

    async def check_pumpswap_migration(self, token_address: str) -> Optional[Dict]:
        """
        Verifica se um token migrou para PumpSwap usando a API Bitquery.
        """
        try:
            bitquery_api_key = self.get_secret('/memecoin-sniping/bitquery-api-key')['apiKey']
            
            query = """
            query ($token: String!) {
              Solana {
                DEXTrades(
                  where: {
                    Trade: {Currency: {MintAddress: {is: $token}}}
                    Transaction: {Result: {Success: true}}
                    Instruction: {Program: {Address: {is: "PSwapMdSBGgzkpVMEXv5mR3NpTfU2arRrLrW8sTCJ"}}}
                  }
                  orderBy: {descending: Block_Time}
                  limit: 1
                ) {
                  Block {
                    Time
                  }
                  Transaction {
                    Signature
                  }
                  Trade {
                    AmountInUSD
                    Currency {
                      MintAddress
                      Symbol
                    }
                  }
                }
              }
            }
            """
            
            variables = {"token": token_address}
            
            async with self.session.post(
                'https://graphql.bitquery.io/',
                json={'query': query, 'variables': variables},
                headers={'X-API-KEY': bitquery_api_key}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    trades = data.get('data', {}).get('Solana', {}).get('DEXTrades', [])
                    
                    if trades:
                        first_trade = trades[0]
                        return {
                            'token_address': token_address,
                            'migration_destination': 'PumpSwap',
                            'first_trade_timestamp': first_trade['Block']['Time'],
                            'first_trade_tx': first_trade['Transaction']['Signature'],
                            'first_trade_amount_usd': first_trade['Trade']['AmountInUSD']
                        }
                        
        except Exception as e:
            logger.error(f"Erro ao verificar migração PumpSwap do token {token_address}: {e}")
            
        return None

    async def check_raydium_migration(self, token_address: str) -> Optional[Dict]:
        """
        Verifica se um token migrou para Raydium usando a API Bitquery.
        """
        try:
            bitquery_api_key = self.get_secret('/memecoin-sniping/bitquery-api-key')['apiKey']
            
            query = """
            query ($token: String!) {
              Solana {
                DEXTrades(
                  where: {
                    Trade: {Currency: {MintAddress: {is: $token}}}
                    Transaction: {Result: {Success: true}}
                    Instruction: {Program: {Address: {is: "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"}}}
                  }
                  orderBy: {descending: Block_Time}
                  limit: 1
                ) {
                  Block {
                    Time
                  }
                  Transaction {
                    Signature
                  }
                  Trade {
                    AmountInUSD
                    Currency {
                      MintAddress
                      Symbol
                    }
                  }
                }
              }
            }
            """
            
            variables = {"token": token_address}
            
            async with self.session.post(
                'https://graphql.bitquery.io/',
                json={'query': query, 'variables': variables},
                headers={'X-API-KEY': bitquery_api_key}
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    trades = data.get('data', {}).get('Solana', {}).get('DEXTrades', [])
                    
                    if trades:
                        first_trade = trades[0]
                        return {
                            'token_address': token_address,
                            'migration_destination': 'Raydium',
                            'first_trade_timestamp': first_trade['Block']['Time'],
                            'first_trade_tx': first_trade['Transaction']['Signature'],
                            'first_trade_amount_usd': first_trade['Trade']['AmountInUSD']
                        }
                        
        except Exception as e:
            logger.error(f"Erro ao verificar migração Raydium do token {token_address}: {e}")
            
        return None

    async def validate_migration_authenticity(self, token_data: Dict) -> bool:
        """
        Valida se a migração é autêntica e não um clone/fake.
        """
        try:
            token_address = token_data['token_address']
            
            # 1. Verificar se o token já foi processado
            if await self.is_token_already_processed(token_address):
                logger.info(f"Token {token_address} já foi processado anteriormente")
                return False
            
            # 2. Verificar idade do token (deve ser recente)
            graduation_time = datetime.fromisoformat(token_data.get('graduation_timestamp', '').replace('Z', '+00:00'))
            token_age = datetime.now().astimezone() - graduation_time
            
            if token_age > timedelta(hours=MAX_TOKEN_AGE_HOURS):
                logger.info(f"Token {token_address} muito antigo: {token_age}")
                return False
            
            # 3. Verificar liquidez mínima
            liquidity_usd = token_data.get('liquidity_at_graduation', 0)
            if liquidity_usd < MIN_LIQUIDITY_USD:
                logger.info(f"Token {token_address} com liquidez insuficiente: ${liquidity_usd}")
                return False
            
            # 4. Verificar market cap mínimo (deve ter graduado)
            market_cap_usd = token_data.get('market_cap_at_graduation', 0)
            if market_cap_usd < MIN_MARKET_CAP_USD:
                logger.info(f"Token {token_address} com market cap insuficiente: ${market_cap_usd}")
                return False
            
            # 5. Verificar se não é uma migração reversa (V2 -> V1)
            if await self.is_reverse_migration(token_address):
                logger.info(f"Token {token_address} detectado como migração reversa")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao validar autenticidade da migração: {e}")
            return False

    async def is_token_already_processed(self, token_address: str) -> bool:
        """Verifica se o token já foi processado anteriormente."""
        try:
            response = self.migration_table.get_item(
                Key={'token_address': token_address}
            )
            return 'Item' in response
        except Exception as e:
            logger.error(f"Erro ao verificar token processado: {e}")
            return False

    async def is_reverse_migration(self, token_address: str) -> bool:
        """
        Detecta migrações reversas (projetos que lançam V1 -> V2 rapidamente).
        """
        try:
            # Buscar tokens similares criados recentemente
            # Implementar lógica para detectar padrões de nome/símbolo similares
            # Por simplicidade, retornamos False aqui
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar migração reversa: {e}")
            return False

    async def track_migration(self, migration_data: Dict) -> None:
        """Registra a migração no DynamoDB para tracking."""
        try:
            item = {
                'token_address': migration_data['token_address'],
                'migration_destination': migration_data.get('migration_destination', 'Unknown'),
                'graduation_timestamp': migration_data.get('graduation_timestamp'),
                'migration_timestamp': migration_data.get('first_trade_timestamp'),
                'market_cap_at_graduation': migration_data.get('market_cap_at_graduation'),
                'liquidity_at_graduation': migration_data.get('liquidity_at_graduation'),
                'processed_timestamp': datetime.now().isoformat(),
                'status': 'discovered'
            }
            
            self.migration_table.put_item(Item=item)
            logger.info(f"Migração registrada para token {migration_data['token_address']}")
            
        except Exception as e:
            logger.error(f"Erro ao registrar migração: {e}")

    async def discover_migrated_tokens(self) -> List[Dict]:
        """
        Descobre tokens que migraram da Pump.Fun para PumpSwap ou Raydium.
        """
        migrated_tokens = []
        
        try:
            # 1. Buscar tokens graduados recentemente da Pump.Fun
            graduated_tokens = await self.get_recently_graduated_tokens()
            
            for token_address in graduated_tokens:
                logger.info(f"Verificando migração do token {token_address}")
                
                # 2. Verificar informações de graduação
                graduation_data = await self.check_pump_fun_graduation(token_address)
                if not graduation_data:
                    continue
                
                # 3. Verificar migração para PumpSwap (prioridade)
                pumpswap_migration = await self.check_pumpswap_migration(token_address)
                if pumpswap_migration:
                    migration_data = {**graduation_data, **pumpswap_migration}
                    
                    # 4. Validar autenticidade
                    if await self.validate_migration_authenticity(migration_data):
                        await self.track_migration(migration_data)
                        migrated_tokens.append(migration_data)
                        logger.info(f"Token migrado para PumpSwap descoberto: {token_address}")
                    continue
                
                # 5. Verificar migração para Raydium (fallback)
                raydium_migration = await self.check_raydium_migration(token_address)
                if raydium_migration:
                    migration_data = {**graduation_data, **raydium_migration}
                    
                    # 6. Validar autenticidade
                    if await self.validate_migration_authenticity(migration_data):
                        await self.track_migration(migration_data)
                        migrated_tokens.append(migration_data)
                        logger.info(f"Token migrado para Raydium descoberto: {token_address}")
                
                # Rate limiting para evitar sobrecarga das APIs
                await asyncio.sleep(0.1)
                
        except Exception as e:
            logger.error(f"Erro ao descobrir tokens migrados: {e}")
        
        return migrated_tokens

    async def get_recently_graduated_tokens(self) -> List[str]:
        """
        Obtém lista de tokens que graduaram recentemente da Pump.Fun.
        """
        try:
            moralis_api_key = self.get_secret('/memecoin-sniping/moralis-api-key')['apiKey']
            
            # Buscar tokens graduados nas últimas 24 horas
            url = "https://solana-gateway.moralis.io/token/graduated"
            headers = {
                'X-API-Key': moralis_api_key,
                'accept': 'application/json'
            }
            
            params = {
                'limit': 100,
                'from_date': (datetime.now() - timedelta(hours=24)).isoformat()
            }
            
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    return [token['mint'] for token in data.get('result', [])]
                    
        except Exception as e:
            logger.error(f"Erro ao buscar tokens graduados: {e}")
            
        return []

    def send_to_sqs(self, message: Dict) -> None:
        """Envia uma mensagem para a fila SQS."""
        try:
            response = sqs.send_message(
                QueueUrl=SQS_QUEUE_URL,
                MessageBody=json.dumps(message)
            )
            logger.info(f"Mensagem enviada para SQS: {response['MessageId']}")
        except ClientError as e:
            logger.error(f"Erro ao enviar mensagem para SQS: {e}")
            raise


async def lambda_handler(event, context):
    """Função principal do Lambda para o Enhanced Discoverer."""
    try:
        logger.info("Enhanced Discoverer iniciado - focando em tokens migrados")
        
        async with EnhancedDiscoverer() as discoverer:
            # Descobrir tokens migrados
            migrated_tokens = await discoverer.discover_migrated_tokens()
            
            # Enviar tokens descobertos para análise
            for token_data in migrated_tokens:
                enhanced_message = {
                    'token_address': token_data['token_address'],
                    'migration_destination': token_data['migration_destination'],
                    'graduation_timestamp': token_data['graduation_timestamp'],
                    'migration_timestamp': token_data.get('first_trade_timestamp'),
                    'market_cap_at_graduation': token_data['market_cap_at_graduation'],
                    'liquidity_at_graduation': token_data['liquidity_at_graduation'],
                    'discovery_timestamp': datetime.now().isoformat(),
                    'discovery_source': 'enhanced_discoverer',
                    'token_type': 'migrated_token'
                }
                
                discoverer.send_to_sqs(enhanced_message)
                logger.info(f"Token migrado {token_data['token_address']} enviado para análise")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Enhanced Discoverer executado com sucesso',
                'tokens_discovered': len(migrated_tokens)
            })
        }
    
    except Exception as e:
        logger.error(f"Erro no Enhanced Discoverer: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# Para teste local
if __name__ == "__main__":
    import asyncio
    
    async def test_discoverer():
        async with EnhancedDiscoverer() as discoverer:
            tokens = await discoverer.discover_migrated_tokens()
            print(f"Tokens descobertos: {len(tokens)}")
            for token in tokens:
                print(json.dumps(token, indent=2))
    
    asyncio.run(test_discoverer())

