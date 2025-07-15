import json
import uuid
from decimal import Decimal

# Simplified in-memory table used for tests
trader_table = type('Table', (), {
    'scan': lambda self: {'Items': []},
    'put_item': lambda self, Item: None
})()

def get_token_price(token_address: str) -> float:
    """Stub for getting token price."""
    return 0.0

def get_solana_keypair():
    """Stub returning a dummy keypair."""
    return object()

def execute_buy_order(token_address: str, position_pct: float, price: float, keypair):
    """Stub executing a buy order and returning simulated trade data."""
    return {
        'success': True,
        'transaction_signature': str(uuid.uuid4()),
        'amount_tokens': 0,
        'price_per_token': price,
        'slippage': 0.0
    }

def save_trade_to_db(trade: dict) -> None:
    """Stub that would persist trade data."""
    trader_table.put_item(Item=trade)


def monitor_position(trade_id: str) -> None:
    """Stub monitoring a trade."""
    pass


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
        'quality_score': analysis['qualityScore']
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
