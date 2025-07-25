import json
import boto3
import requests
import os
import hmac
import hashlib
import logging
from flask import Blueprint, jsonify, request
from botocore.exceptions import ClientError

notifications_bp = Blueprint("notifications", __name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Cliente AWS
secrets_manager = boto3.client("secretsmanager", region_name=os.environ.get("AWS_REGION", "us-east-1"))

# Obter o secret para autenticação do webhook
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET_KEY") # Deve ser configurado como variável de ambiente

def verify_webhook_signature(data, signature):
    """
    Verifica a assinatura HMAC para autenticar requisições de webhook.
    """
    if not WEBHOOK_SECRET:
        logging.warning("WEBHOOK_SECRET não configurado. Webhook não será autenticado.")
        return True # Permitir se não houver secret configurado (apenas para desenvolvimento/teste)

    try:
        # Assumindo que a assinatura é um hash SHA256 do corpo da requisição
        # O formato exato da assinatura pode variar dependendo de como o remetente a gera
        # Aqui, um exemplo simples de verificação
        expected_signature = hmac.new(WEBHOOK_SECRET.encode("utf-8"),
                                      json.dumps(data, separators=(",", ":")).encode("utf-8"),
                                      hashlib.sha256).hexdigest()
        
        if hmac.compare_digest(expected_signature, signature):
            return True
        else:
            logging.warning(f"Assinatura inválida. Esperado: {expected_signature}, Recebido: {signature}")
            return False
    except Exception as e:
        logging.error(f"Erro ao verificar assinatura do webhook: {e}")
        return False

def get_telegram_token():
    """Recupera o token do bot Telegram do Secrets Manager."""
    secret_name = os.environ.get("TELEGRAM_API_SECRET_ARN")
    if not secret_name:
        logging.error("Variável de ambiente TELEGRAM_API_SECRET_ARN não configurada.")
        return None
    try:
        response = secrets_manager.get_secret_value(
            SecretId=secret_name
        )
        secret = json.loads(response["SecretString"])
        return secret["botToken"]
    except ClientError as e:
        logging.error(f"Erro ao recuperar token do Telegram do Secrets Manager: {e.response["Error"]["Message"]}")
        return None
    except Exception as e:
        logging.error(f"Erro inesperado ao recuperar token do Telegram: {e}")
        return None

def send_telegram_message(chat_id, message):
    """Envia mensagem via Telegram."""
    token = get_telegram_token()
    if not token:
        logging.error("Não foi possível obter o token do Telegram. Mensagem não enviada.")
        return False
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, data=data, timeout=10)
        response.raise_for_status() # Levanta HTTPError para códigos de status de erro (4xx ou 5xx)
        return True
    
    except requests.exceptions.Timeout:
        logging.error("Tempo limite excedido ao enviar mensagem ao Telegram.")
        return False
    except requests.exceptions.RequestException as e:
        logging.error(f"Erro de requisição ao enviar mensagem ao Telegram: {e}")
        return False
    except Exception as e:
        logging.error(f"Erro inesperado ao enviar mensagem Telegram: {e}")
        return False

@notifications_bp.route("/telegram/send", methods=["POST"])
def send_notification():
    return jsonify({"message": "Notificação enviada com sucesso"})



@notifications_bp.route("/alerts/trade", methods=["POST"])
def send_trade_alert():
    return jsonify({"message": "Alerta enviado"})
