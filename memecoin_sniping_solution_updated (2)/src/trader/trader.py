import json
import uuid
import os
import logging
import boto3
from solana.rpc.api import Client
from solders.keypair import Keypair
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class InMemoryTable:
    """Simple in-memory table to emulate DynamoDB for local tests."""

    def __init__(self):
        self.items = {}

    def scan(self):
        return {'Items': list(self.items.values())}

    def put_item(self, Item):
        self.items[Item['trade_id']] = Item

    def get_item(self, Key):
        trade_id = Key.get('trade_id')
        return {'Item': self.items.get(trade_id)}

    def update_item(self, Key, Updates):
        trade_id = Key.get('trade_id')
        if trade_id in self.items:
            self.items[trade_id].update(Updates)


MODE = os.environ.get("MODE", "paper")
TRADER_TABLE_NAME = os.environ.get("TRADER_TABLE_NAME", "MemecoinSnipingTraderTable")
SOLANA_WALLET_SECRET_ARN = os.environ.get("SOLANA_WALLET_SECRET_ARN")
SOLANA_RPC_URL = os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")

dynamodb = boto3.resource("dynamodb")
secrets_manager = boto3.client("secretsmanager")
solana_client = Client(SOLANA_RPC_URL)

try:
    trader_table = dynamodb.Table(TRADER_TABLE_NAME)
except Exception:
    trader_table = InMemoryTable()

def get_token_price(token_address: str) -> float:
    """Return the current token price."""
    if MODE == "real":
        try:
            # Placeholder for real price lookup using on-chain data or DEX API
            return 0.0
        except Exception as e:
            logger.error(f"Erro ao buscar preço real: {e}")
            return 0.0
    # Paper mode uses a fixed simulated price
    return 0.0

def get_solana_keypair():
    """Retrieve the Solana keypair for signing transactions."""
    if MODE == "real" and SOLANA_WALLET_SECRET_ARN:
        try:
            secret = secrets_manager.get_secret_value(SecretId=SOLANA_WALLET_SECRET_ARN)
            key_data = json.loads(secret["SecretString"])
            private_key = key_data.get("privateKey")
            if private_key:
                try:
                    return Keypair.from_base58_string(private_key)
                except Exception:
                    return Keypair.from_secret_key(bytes.fromhex(private_key))
        except Exception as e:
            logger.error(f"Erro ao carregar chave Solana: {e}")
    # Em modo paper, retorna um keypair aleatório (não usado para transações reais)
    return Keypair()

def execute_buy_order(token_address: str, position_pct: float, price: float, keypair):
    """Execute a buy order or simulate it depending on MODE."""
    if MODE == "real":
        try:
            # Placeholder for real DEX interaction via solana_client
            tx_sig = str(uuid.uuid4())
            return {
                'success': True,
                'transaction_signature': tx_sig,
                'amount_tokens': position_pct,
                'price_per_token': price,
                'slippage': 0.0
            }
        except Exception as e:
            logger.error(f"Erro ao executar compra real: {e}")
            return {'success': False}
    # Paper mode simula a ordem
    return {
        'success': True,
        'transaction_signature': str(uuid.uuid4()),
        'amount_tokens': position_pct,
        'price_per_token': price,
        'slippage': 0.0
    }

def execute_sell_order(token_address: str, amount_tokens: float, price: float, keypair):
    """Execute a sell order or simulate it depending on MODE."""
    if MODE == "real":
        try:
            tx_sig = str(uuid.uuid4())
            return {
                'success': True,
                'transaction_signature': tx_sig,
                'amount_tokens': amount_tokens,
                'price_per_token': price,
                'slippage': 0.0
            }
        except Exception as e:
            logger.error(f"Erro ao executar venda real: {e}")
            return {'success': False}
    return {
        'success': True,
        'transaction_signature': str(uuid.uuid4()),
        'amount_tokens': amount_tokens,
        'price_per_token': price,
        'slippage': 0.0
    }

def save_trade_to_db(trade: dict) -> None:
    """Stub that would persist trade data."""
    trader_table.put_item(Item=trade)


def monitor_position(trade_id: str) -> None:
    """Monitor an open position and execute sell orders when targets hit."""
    record_resp = trader_table.get_item({'trade_id': trade_id})
    trade = record_resp.get('Item')
    if not trade:
        return

    current_price = get_token_price(trade['token_address'])
    if not current_price:
        return

    entry_price = trade['price_per_token']
    sl_threshold = entry_price * (1 - trade['stop_loss_pct'])
    tp_threshold = entry_price * (1 + trade['take_profit_pct'])

    if current_price <= sl_threshold:
        result = execute_sell_order(trade['token_address'], trade.get('amount_tokens', 0), current_price, get_solana_keypair())
        if result.get('success'):
            trader_table.update_item({'trade_id': trade_id}, {
                'status': 'closed',
                'close_reason': 'stop_loss',
                'close_price': current_price
            })
    elif current_price >= tp_threshold:
        result = execute_sell_order(trade['token_address'], trade.get('amount_tokens', 0), current_price, get_solana_keypair())
        if result.get('success'):
            trader_table.update_item({'trade_id': trade_id}, {
                'status': 'closed',
                'close_reason': 'take_profit',
                'close_price': current_price
            })


def calculate_trade_parameters(quality_score: int, price: float):
    """Return trading parameters based on quality score."""
    if quality_score >= 80:
        return {
            'stop_loss_pct': 0.10,
            'take_profit_pct': 0.30,
            'position_size_pct': 0.15,
        }
    elif quality_score >= 60:
        return {
            'stop_loss_pct': 0.15,
            'take_profit_pct': 0.25,
            'position_size_pct': 0.10,
        }
    else:
        return {
            'stop_loss_pct': 0.20,
            'take_profit_pct': 0.20,
            'position_size_pct': 0.05,
        }


def process_approved_token(analysis: dict):
    """Process a token approved for trading."""
    price = get_token_price(analysis['tokenAddress'])
    if not price:
        return None

    params = calculate_trade_parameters(analysis['qualityScore'], price)
    keypair = get_solana_keypair()
    trade = execute_buy_order(analysis['tokenAddress'], params['position_size_pct'], price, keypair)
    if not trade.get('success'):
        return None

    trade_record = {
        'trade_id': trade['transaction_signature'],
        'token_address': analysis['tokenAddress'],
        'status': 'open',
        'price_per_token': trade['price_per_token'],
        'quality_score': analysis['qualityScore'],
        'stop_loss_pct': params['stop_loss_pct'],
        'take_profit_pct': params['take_profit_pct'],
        'position_size_pct': params['position_size_pct'],
        'is_dry_run': MODE != 'real',
        'amount_tokens': trade.get('amount_tokens', 0)
    }
    save_trade_to_db(trade_record)
    return trade_record


def lambda_handler(event, context):
    """Entry point for the Trader lambda."""
    if 'Records' in event:
        body = json.loads(event['Records'][0]['body'])
        result = process_approved_token(body)
        return {'statusCode': 200, 'body': json.dumps(result)}
    if event.get('source') == 'aws.events':
        response = trader_table.scan()
        for item in response.get('Items', []):
            if item.get('status') == 'open':
                monitor_position(item['trade_id'])
        return {'statusCode': 200, 'body': json.dumps({'message': 'positions monitored'})}
    return {'statusCode': 400, 'body': json.dumps({'message': 'invalid event'})}
