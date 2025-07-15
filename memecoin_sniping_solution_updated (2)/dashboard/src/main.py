from flask import Flask, render_template, request, jsonify, Blueprint
import logging
import pandas as pd
import os
import json

app = Flask(__name__)

# Configuração de logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Importar blueprints
from .routes.trading import trading_bp
from .routes.notifications import notifications_bp

app.register_blueprint(trading_bp, url_prefix="/api/trading")
app.register_blueprint(notifications_bp, url_prefix="/api/notifications")

# Caminho para salvar dados históricos
HISTORICAL_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "optimizer", "processed", "historical_data.parquet")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status", methods=["GET"])
def get_status():
    try:
        # Simulação de status do sistema
        status = {
            "system_status": "operational", # Mudado para minúsculas para consistência com CSS
            "last_update": "2025-07-10 10:00:00",
            "active_strategies": 3
        }
        logging.info("Status do sistema solicitado e retornado com sucesso.")
        return jsonify(status)
    except Exception as e:
        logging.error(f"Erro ao obter status do sistema: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@app.route("/api/data/upload_historical", methods=["POST"])
def upload_historical_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nenhum dado JSON fornecido"}), 400

        df_new = pd.DataFrame(data)

        # Verificar se o arquivo já existe e carregar para append
        if os.path.exists(HISTORICAL_DATA_PATH):
            df_existing = pd.read_parquet(HISTORICAL_DATA_PATH)
            df_combined = pd.concat([df_existing, df_new], ignore_index=True)
            # Remover duplicatas se houver uma chave única, por exemplo, 'timestamp'
            # df_combined.drop_duplicates(subset=['timestamp'], inplace=True)
            df_combined.to_parquet(HISTORICAL_DATA_PATH, index=False)
            logging.info(f"Dados históricos anexados ao arquivo existente: {HISTORICAL_DATA_PATH}")
        else:
            df_new.to_parquet(HISTORICAL_DATA_PATH, index=False)
            logging.info(f"Novo arquivo de dados históricos criado: {HISTORICAL_DATA_PATH}")

        return jsonify({"message": "Dados históricos recebidos e salvos com sucesso!"}), 200

    except json.JSONDecodeError:
        logging.error("Erro ao decodificar JSON na requisição de dados históricos.")
        return jsonify({"error": "Formato JSON inválido"}), 400
    except Exception as e:
        logging.error(f"Erro ao processar upload de dados históricos: {e}")
        return jsonify({"error": f"Erro interno do servidor: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)


