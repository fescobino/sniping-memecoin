from flask import Blueprint, jsonify, request
import logging
import os
import json
import boto3
from botocore.exceptions import ClientError

trading_bp = Blueprint('trading', __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Configuração do DynamoDB
# As tabelas devem ser criadas via CloudFormation e seus nomes importados via variáveis de ambiente
TRADER_TABLE_NAME = os.environ.get('TRADER_TABLE_NAME', 'MemecoinSnipingTraderTable')
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
trader_table = dynamodb.Table(TRADER_TABLE_NAME)
s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

@trading_bp.route('/trades', methods=['GET'])
def get_trades():
    """Retorna trades simulados para o dashboard de testes."""
    return jsonify([])

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


@trading_bp.route('/metrics', methods=['GET'])
def get_metrics():
    return jsonify({'total_trades': 0, 'win_rate': 0, 'total_pnl': 0})


@trading_bp.route('/performance', methods=['GET'])
def get_performance():
    return jsonify([])


@trading_bp.route('/status', methods=['GET'])
def get_status_api():
    return jsonify({'system_status': 'ok'})
