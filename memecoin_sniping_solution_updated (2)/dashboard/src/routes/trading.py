from flask import Blueprint, jsonify, request
import logging
import os
import boto3
from botocore.exceptions import ClientError

trading_bp = Blueprint('trading', __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do DynamoDB
# As tabelas devem ser criadas via CloudFormation e seus nomes importados via variáveis de ambiente
TRADER_TABLE_NAME = os.environ.get('TRADER_TABLE_NAME', 'MemecoinSnipingTraderTable')
dynamodb = boto3.resource('dynamodb')
trader_table = dynamodb.Table(TRADER_TABLE_NAME)

@trading_bp.route('/api/trades', methods=['GET'])
def get_trades():
    """
    Retorna uma lista de trades registrados no DynamoDB.
    Permite filtragem por status e paginação.
    """
    status = request.args.get('status')
    limit = request.args.get('limit', 10, type=int)
    last_evaluated_key = request.args.get('last_evaluated_key')

    scan_kwargs = {
        'Limit': limit
    }

    if status:
        scan_kwargs['FilterExpression'] = boto3.dynamodb.conditions.Attr('status').eq(status)

    if last_evaluated_key:
        try:
            scan_kwargs['ExclusiveStartKey'] = json.loads(last_evaluated_key)
        except json.JSONDecodeError:
            logging.error(f"Erro ao decodificar last_evaluated_key: {last_evaluated_key}")
            return jsonify({'error': 'Invalid last_evaluated_key format'}), 400

    try:
        response = trader_table.scan(**scan_kwargs)
        trades = response.get('Items', [])
        response_last_evaluated_key = response.get('LastEvaluatedKey')

        # Converter Decimal para float/int para serialização JSON
        for trade in trades:
            for key, value in trade.items():
                if isinstance(value, Decimal):
                    trade[key] = float(value) if value % 1 != 0 else int(value)

        return jsonify({
            'trades': trades,
            'last_evaluated_key': json.dumps(response_last_evaluated_key) if response_last_evaluated_key else None
        })
    except ClientError as e:
        logging.error(f"Erro ao buscar trades do DynamoDB: {e.response['Error']['Message']}")
        return jsonify({'error': 'Could not retrieve trades'}), 500
    except Exception as e:
        logging.error(f"Erro inesperado ao buscar trades: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@trading_bp.route('/api/trade/<string:trade_id>', methods=['GET'])
def get_trade_details(trade_id):
    """
    Retorna os detalhes de um trade específico.
    """
    try:
        response = trader_table.get_item(Key={'tradeId': trade_id})
        trade = response.get('Item')

        if not trade:
            return jsonify({'error': 'Trade not found'}), 404

        # Converter Decimal para float/int para serialização JSON
        for key, value in trade.items():
            if isinstance(value, Decimal):
                trade[key] = float(value) if value % 1 != 0 else int(value)

        return jsonify(trade)
    except ClientError as e:
        logging.error(f"Erro ao buscar detalhes do trade {trade_id} do DynamoDB: {e.response['Error']['Message']}")
        return jsonify({'error': 'Could not retrieve trade details'}), 500
    except Exception as e:
        logging.error(f"Erro inesperado ao buscar detalhes do trade: {e}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

# Adicionar rotas para iniciar/parar trades, se aplicável ao dashboard
# Exemplo: @trading_bp.route('/api/trade/start', methods=['POST'])

