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
    """Envia notificação via Telegram. Requer autenticação via header 'X-Webhook-Signature'."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not verify_webhook_signature(request.json, signature):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        if not data or "chat_id" not in data or "message" not in data:
            return jsonify({"error": "chat_id e message são obrigatórios"}), 400
        
        chat_id = data["chat_id"]
        message = data["message"]
        
        success = send_telegram_message(chat_id, message)
        
        if success:
            return jsonify({"message": "Notificação enviada com sucesso"})
        else:
            return jsonify({"error": "Falha ao enviar notificação"}), 500
    
    except Exception as e:
        logging.error(f"Erro ao processar requisição de envio de notificação: {e}")
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/telegram/test", methods=["POST"])
def test_telegram():
    """Testa a configuração do Telegram. Requer autenticação via header 'X-Webhook-Signature'."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not verify_webhook_signature(request.json, signature):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        chat_id = data.get("chat_id", os.environ.get("DEFAULT_TELEGRAM_CHAT_ID", "@memecoin_sniping_alerts"))
        
        test_message = """
🤖 *Teste de Notificação - Memecoin Sniping Bot*

✅ Sistema operacional
📊 Dashboard funcionando
🔔 Notificações ativas

_Este é um teste automático do sistema de alertas._
        """
        
        success = send_telegram_message(chat_id, test_message)
        
        if success:
            return jsonify({"message": "Teste enviado com sucesso"})
        else:
            return jsonify({"error": "Falha no teste"}), 500
    
    except Exception as e:
        logging.error(f"Erro ao processar requisição de teste do Telegram: {e}")
        return jsonify({"error": str(e)}), 500

def format_trade_alert(trade_data, alert_type="new_trade"):
    """Formata alerta de trade para Telegram."""
    token_short = trade_data.get("token_address", "Unknown")[:8] + "..." if trade_data.get("token_address") else "Unknown"
    
    if alert_type == "new_trade":
        return f"""
🚀 *Novo Trade Executado*

🪙 Token: `{token_short}`
💰 Valor: ${trade_data.get("amount_usd", 0):.2f}
📊 Score: {trade_data.get("quality_score", 0):.0f}/100
💵 Preço: ${trade_data.get("entry_price", 0):.6f}
🎯 Take Profit: ${trade_data.get("take_profit_price", 0):.6f}
🛑 Stop Loss: ${trade_data.get("stop_loss_price", 0):.6f}
🔄 Modo: {"Paper" if trade_data.get("is_dry_run") else "Live"}

_Trade ID: {trade_data.get("trade_id", "N/A")}_
        """
    
    elif alert_type == "trade_closed":
        pnl = trade_data.get("pnl", 0)
        pnl_emoji = "🟢" if pnl >= 0 else "🔴"
        exit_reason = trade_data.get("exit_reason", "manual")
        
        return f"""
{pnl_emoji} *Trade Fechado*

🪙 Token: `{token_short}`
💰 P&L: ${pnl:.2f} ({trade_data.get("pnl_pct", 0):.1f}%)
📈 Entrada: ${trade_data.get("entry_price", 0):.6f}
📉 Saída: ${trade_data.get("exit_price", 0):.6f}
🎯 Motivo: {exit_reason.replace("_", " ").title()}
🔄 Modo: {"Paper" if trade_data.get("is_dry_run") else "Live"}

_Trade ID: {trade_data.get("trade_id", "N/A")}_
        """
    
    elif alert_type == "high_drawdown":
        return f"""
⚠️ *Alerta de Drawdown Alto*

📉 Drawdown atual: {trade_data.get("drawdown", 0):.1f}%
💰 P&L total: ${trade_data.get("total_pnl", 0):.2f}
📊 Win rate: {trade_data.get("win_rate", 0):.1f}%

_Revisar estratégia recomendado_
        """
    
    return "Alerta do sistema de trading"

@notifications_bp.route("/alerts/trade", methods=["POST"])
def send_trade_alert():
    """Envia alerta específico de trade. Requer autenticação via header 'X-Webhook-Signature'."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not verify_webhook_signature(request.json, signature):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        if not data or "trade_data" not in data:
            return jsonify({"error": "trade_data é obrigatório"}), 400
        
        trade_data = data["trade_data"]
        alert_type = data.get("alert_type", "new_trade")
        chat_id = data.get("chat_id", os.environ.get("DEFAULT_TELEGRAM_CHAT_ID", "@memecoin_sniping_alerts"))
        
        message = format_trade_alert(trade_data, alert_type)
        success = send_telegram_message(chat_id, message)
        
        if success:
            return jsonify({"message": "Alerta de trade enviado"})
        else:
            return jsonify({"error": "Falha ao enviar alerta"}), 500
    
    except Exception as e:
        logging.error(f"Erro ao processar requisição de alerta de trade: {e}")
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/alerts/system", methods=["POST"])
def send_system_alert():
    """Envia alerta de sistema. Requer autenticação via header 'X-Webhook-Signature'."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not verify_webhook_signature(request.json, signature):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        if not data or "message" not in data:
            return jsonify({"error": "message é obrigatório"}), 400
        
        alert_level = data.get("level", "info")  # info, warning, error
        message = data["message"]
        chat_id = data.get("chat_id", os.environ.get("DEFAULT_TELEGRAM_CHAT_ID", "@memecoin_sniping_alerts"))
        
        # Emojis baseados no nível
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "🚨"
        }
        
        formatted_message = f"""
{emoji_map.get(alert_level, "ℹ️")} *Alerta do Sistema*

{message}

_Timestamp: {data.get("timestamp", "N/A")}_
        """
        
        success = send_telegram_message(chat_id, formatted_message)
        
        if success:
            return jsonify({"message": "Alerta de sistema enviado"})
        else:
            return jsonify({"error": "Falha ao enviar alerta"}), 500
    
    except Exception as e:
        logging.error(f"Erro ao processar requisição de alerta de sistema: {e}")
        return jsonify({"error": str(e)}), 500

@notifications_bp.route("/webhook/telegram", methods=["POST"])
def telegram_webhook():
    """Webhook para receber comandos do Telegram. Requer autenticação via header 'X-Webhook-Signature'."""
    signature = request.headers.get("X-Webhook-Signature")
    if not signature or not verify_webhook_signature(request.json, signature):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = request.get_json()
        
        # Processar comandos básicos
        if "message" in data:
            message = data["message"]
            chat_id = message["chat"]["id"]
            text = message.get("text", "")
            
            if text.startswith("/status"):
                # Comando para verificar status
                status_message = """
🤖 *Status do Sistema*

✅ Bot ativo
📊 Dashboard online
🔄 Agentes funcionando

Use /help para ver comandos disponíveis.
                """
                send_telegram_message(chat_id, status_message)
            
            elif text.startswith("/help"):
                # Comando de ajuda
                help_message = """
🤖 *Comandos Disponíveis*

/status - Status do sistema
/metrics - Métricas de trading
/help - Esta mensagem

_Bot de monitoramento Memecoin Sniping_
                """
                send_telegram_message(chat_id, help_message)
            
            elif text.startswith("/metrics"):
                # Comando para métricas (simplificado)
                metrics_message = """
📊 *Métricas Rápidas*

Para métricas detalhadas, acesse o dashboard web.

_Use o comando /status para verificar o sistema._
                """
                send_telegram_message(chat_id, metrics_message)
        
        return jsonify({"status": "ok"})
    
    except Exception as e:
        logging.error(f"Erro no webhook Telegram: {e}")
        return jsonify({"error": str(e)}), 500


