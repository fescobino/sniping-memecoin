import json
import logging
import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError
from web3 import Web3

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mocks para boto3 e Web3
class MockDynamoDBTable:
    def __init__(self, name):
        self.name = name
        self.items = {}

    def put_item(self, Item):
        print(f"Mock DynamoDB: Item salvo na tabela {self.name}: {Item}")
        self.items[Item["tradeId"]] = Item

class MockS3Client:
    def put_object(self, Bucket, Key, Body, ContentType=None):
        print(f"Mock S3: Objeto salvo no bucket {Bucket} com chave {Key}")

class MockWeb3:
    def __init__(self, provider=None):
        self.eth = MockEth()

    class HTTPProvider:
        def __init__(self, endpoint_uri):
            self.endpoint_uri = endpoint_uri

class MockEth:
    def get_balance(self, address):
        return 1000000000000000000 # 1 ETH em wei

    def get_transaction_count(self, address):
        return 10 # Número de transações simulado

    def send_raw_transaction(self, signed_transaction):
        print(f"Mock Web3: Transação bruta enviada: {signed_transaction}")
        return b'0x' + os.urandom(32).hex().encode('utf-8') # Hash de transação simulado

    def wait_for_transaction_receipt(self, tx_hash):
        print(f"Mock Web3: Aguardando recibo da transação {tx_hash}")
        return {"status": 1} # Recibo de sucesso simulado

# Substitui os clientes AWS e Web3 pelos mocks para teste local
boto3_client_original = boto3.client
boto3_resource_original = boto3.resource
web3_original = Web3

def mock_boto3_client(service_name, region_name=None):
    if service_name == "s3":
        return MockS3Client()
    return boto3_client_original(service_name, region_name)

def mock_boto3_resource(service_name, region_name=None):
    if service_name == "dynamodb":
        return type("MockDynamoDB", (object,), {"Table": MockDynamoDBTable})()
    return boto3_resource_original(service_name, region_name)

# Atribui a classe MockWeb3 diretamente a Web3
Web3 = MockWeb3

boto3.client = mock_boto3_client
boto3.resource = mock_boto3_resource

# Clientes AWS (agora usando os mocks)
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

# Variáveis de ambiente
TRADE_LOG_TABLE = os.environ.get("TRADE_LOG_TABLE", "MemecoinSnipingTradeLog")
PRICE_LOG_BUCKET = os.environ.get("PRICE_LOG_BUCKET", "memecoin-sniping-price-logs")
MODE = os.environ.get("MODE", "paper") # 'paper' ou 'real'

class Executor:
    def __init__(self):
        self.trade_log_table = dynamodb.Table(TRADE_LOG_TABLE)
        self.w3 = Web3(Web3.HTTPProvider("http://localhost:8545")) # Conecta ao mock ou nó real

    def fetch_price(self, token_address: str) -> float:
        """Simula a busca do preço atual do token."""
        # Em um ambiente real, isso buscaria o preço de uma API de exchange ou DEX
        # Por enquanto, retorna um valor simulado
        return 0.00000123 # Preço simulado em USD

    def log_price_series(self, token_address: str, timestamp: str, price: float, trade_id: str) -> None:
        """Registra o preço do token em DynamoDB e S3."""
        try:
            # Log no DynamoDB para acesso rápido
            self.trade_log_table.put_item(
                Item={
                    "tradeId": trade_id,
                    "timestamp": timestamp,
                    "tokenAddress": token_address,
                    "price": price,
                    "logType": "price_series"
                }
            )
            logger.info(f"Preço {price} para {token_address} registrado em DynamoDB.")

            # Log em S3 para dados históricos e análises mais profundas
            s3_key = f'price_logs/{token_address}/{datetime.now().strftime("%Y/%m/%d")}/{trade_id}_{timestamp}.json'
            s3.put_object(
                Bucket=PRICE_LOG_BUCKET,
                Key=s3_key,
                Body=json.dumps({"tokenAddress": token_address, "timestamp": timestamp, "price": price})
            )
            logger.info(f"Preço {price} para {token_address} registrado em S3.")

        except ClientError as e:
            logger.error(f"Erro de cliente AWS ao registrar preço: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar preço: {e}")

    def execute_trade(self, token_address: str, confidence_score: float, trade_params: dict) -> dict:
        """Executa ou simula um trade com base no confidence score e modo."""
        trade_id = f"trade_{token_address}_{int(datetime.now().timestamp())}"
        price_before = self.fetch_price(token_address)
        self.log_price_series(token_address, datetime.now().isoformat(), price_before, trade_id)

        if MODE == "paper":
            logger.info(f"[PAPER MODE] Simulação de trade para {token_address} com score {confidence_score:.2f}")
            # Simular execução e resultado
            price_after = price_before * (1 + (confidence_score * 0.1) - 0.02) # Simula um ganho ou perda
            trade_status = "simulated_success" if confidence_score > 0.6 else "simulated_failure"
            pnl = (price_after - price_before) / price_before
            logger.info(f"[PAPER MODE] Preço antes: {price_before}, Preço depois: {price_after}, PnL: {pnl:.2%}")

        elif MODE == "real":
            if confidence_score >= trade_params.get("threshold", 0.7):
                logger.info(f"[REAL MODE] Executando trade para {token_address} com score {confidence_score:.2f}")
                try:
                    # Exemplo de interação com Web3 para um trade real
                    # Isso é um placeholder e precisaria de lógica real de contrato/DEX
                    # from web3.middleware import geth_poa_middleware
                    # self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
                    # account = self.w3.eth.account.from_key("YOUR_PRIVATE_KEY")
                    # nonce = self.w3.eth.get_transaction_count(account.address)
                    # tx = {
                    #     'from': account.address,
                    #     'to': '0xYourDEXRouterAddress',
                    #     'value': self.w3.to_wei(trade_params.get('amount', 0), 'ether'),
                    #     'gas': 2000000,
                    #     'gasPrice': self.w3.to_wei('50', 'gwei'),
                    #     'nonce': nonce,
                    #     'data': '0xYourContractCallData' # Chamada para swap na DEX
                    # }
                    # signed_tx = self.w3.eth.account.sign_transaction(tx, account.key)
                    # tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    # receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

                    trade_status = "executed_success"
                    price_after = self.fetch_price(token_address) # Buscar preço real após trade
                    pnl = (price_after - price_before) / price_before
                    logger.info(f"[REAL MODE] Trade real executado. Preço antes: {price_before}, Preço depois: {price_after}, PnL: {pnl:.2%}")
                except Exception as e:
                    logger.error(f"[REAL MODE] Erro ao executar trade para {token_address}: {e}")
                    trade_status = "executed_failure"
                    price_after = price_before # Preço não mudou se falhou
                    pnl = 0.0
            else:
                logger.info(f"[REAL MODE] Confidence score {confidence_score:.2f} abaixo do threshold. Aplicando fallback heurístico.")
                # Lógica de fallback heurístico
                trade_status = "fallback_applied"
                price_after = price_before
                pnl = 0.0
        else:
            logger.warning(f"Modo desconhecido: {MODE}. Nenhuma ação de trade executada.")
            trade_status = "no_action"
            price_after = price_before
            pnl = 0.0

        self.log_price_series(token_address, datetime.now().isoformat(), price_after, trade_id) # Log do preço após trade

        # Registrar trade no DynamoDB
        try:
            self.trade_log_table.put_item(
                Item={
                    "tradeId": trade_id,
                    "tokenAddress": token_address,
                    "timestamp": datetime.now().isoformat(),
                    "confidenceScore": confidence_score,
                    "mode": MODE,
                    "status": trade_status,
                    "priceBefore": price_before,
                    "priceAfter": price_after,
                    "pnl": pnl,
                    "tradeParams": json.dumps(trade_params) # Armazenar parâmetros como string JSON
                }
            )
            logger.info(f"Trade {trade_id} registrado com status: {trade_status}")
        except ClientError as e:
            logger.error(f"Erro de cliente DynamoDB ao registrar trade: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao registrar trade: {e}")

        return {
            "trade_id": trade_id,
            "status": trade_status,
            "price_before": price_before,
            "price_after": price_after,
            "pnl": pnl
        }

def lambda_handler(event, context):
    """Função principal do Lambda para o Agente Executor."""
    try:
        logger.info("Agente Executor iniciado.")
        executor = Executor()

        # O evento deve conter os dados do Optimizer
        message_body = json.loads(event["Records"][0]["body"])
        token_address = message_body["token_address"]
        confidence_score = message_body["confidence_score"]
        trade_params = message_body["trade_params"]

        result = executor.execute_trade(token_address, confidence_score, trade_params)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Execução de trade processada",
                "trade_id": result["trade_id"],
                "status": result["status"],
                "pnl": result["pnl"]
            }, default=str)
        }

    except Exception as e:
        logger.error(f"Erro no Agente Executor: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Para teste local
if __name__ == "__main__":
    # Configurações de ambiente para teste local
    os.environ["TRADE_LOG_TABLE"] = "MemecoinSnipingTradeLogLocal"
    os.environ["PRICE_LOG_BUCKET"] = "memecoin-sniping-price-logs-local"
    os.environ["MODE"] = "paper" # Testar em paper mode

    # Simular um evento do Optimizer
    test_event = {
        "Records": [
            {
                "body": json.dumps({
                    "token_address": "test_token_executor_123",
                    "confidence_score": 0.85,
                    "trade_params": {"threshold": 0.7, "amount": 100, "slippage": 0.01}
                })
            }
        ]
    }

    print("\n--- Teste de execução em Paper Mode (sucesso esperado) ---")
    result_success = lambda_handler(test_event, None)
    print(json.dumps(result_success, indent=2))

    test_event_fail = {
        "Records": [
            {
                "body": json.dumps({
                    "token_address": "test_token_executor_456",
                    "confidence_score": 0.40,
                    "trade_params": {"threshold": 0.7, "amount": 100, "slippage": 0.01}
                })
            }
        ]
    }

    print("\n--- Teste de execução em Paper Mode (falha esperada, fallback) ---")
    result_fail = lambda_handler(test_event_fail, None)
    print(json.dumps(result_fail, indent=2))

    # Testar em modo real (simulado)
    os.environ["MODE"] = "real"
    print("\n--- Teste de execução em Real Mode (sucesso esperado) ---")
    result_real_success = lambda_handler(test_event, None)
    print(json.dumps(result_real_success, indent=2))

    print("\n--- Teste de execução em Real Mode (falha esperada, fallback) ---")
    result_real_fail = lambda_handler(test_event_fail, None)
    print(json.dumps(result_real_fail, indent=2))


