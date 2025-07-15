import json
import logging
import os
import boto3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, NoCredentialsError
from decimal import Decimal
import io

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Mocks para boto3
class MockDynamoDBTable:
    def __init__(self, name):
        self.name = name
        self.items = {}
    
    def get_item(self, Key):
        return {"Item": self.items.get(Key["trade_id"])}
        
    def put_item(self, Item):
        self.items[Item["trade_id"]] = Item

    def scan(self, FilterExpression, ExpressionAttributeValues):
        # Simula um scan simples para o teste
        # Em um ambiente real, isso seria mais complexo
        return {"Items": list(self.items.values())}

class MockS3Client:
    def get_object(self, Bucket, Key):
        if Key == "agent_config.json":
            return {"Body": io.BytesIO(json.dumps(get_default_config()).encode("utf-8"))}
        raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")

    def put_object(self, Bucket, Key, Body, ContentType):
        print(f"Mock S3: Objeto salvo no bucket {Bucket} com a chave {Key}")

class MockSageMakerRuntime:
    def invoke_endpoint(self, EndpointName, ContentType, Body):
        simulated_best_params = {
            "quality_threshold": 70.0,
            "high_score_sl": 0.12,
            "high_score_tp": 0.35,
            "medium_score_sl": 0.18,
            "medium_score_tp": 0.28
        }
        simulated_best_value = 0.75
        return {"Body": io.BytesIO(json.dumps({"best_params": simulated_best_params, "best_value": simulated_best_value}).encode())}

# Substitui os clientes AWS pelos mocks para teste local
boto3_client_original = boto3.client
boto3_resource_original = boto3.resource

def mock_boto3_client(service_name, region_name=None):
    if service_name == "s3":
        return MockS3Client()
    elif service_name == "sagemaker-runtime":
        return MockSageMakerRuntime()
    return boto3_client_original(service_name, region_name)

def mock_boto3_resource(service_name, region_name=None):
    if service_name == "dynamodb":
        return type("MockDynamoDB", (object,), {"Table": MockDynamoDBTable})()
    return boto3_resource_original(service_name, region_name)

boto3.client = mock_boto3_client
boto3.resource = mock_boto3_resource

# Clientes AWS (agora usando os mocks)
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")
sagemaker_runtime = boto3.client("sagemaker-runtime")

# Variáveis de ambiente
TRADER_TABLE_NAME = os.environ.get("TRADER_TABLE_NAME", "MemecoinSnipingTraderTable")
OPTIMIZER_TABLE_NAME = os.environ.get("OPTIMIZER_TABLE_NAME", "MemecoinSnipingOptimizerTable")
CONFIG_BUCKET = os.environ.get("CONFIG_BUCKET", "memecoin-sniping-config-bucket")
CONFIG_KEY = os.environ.get("CONFIG_KEY", "agent_config.json")
SAGEMAKER_OPTIMIZER_ENDPOINT_NAME = os.environ.get("SAGEMAKER_OPTIMIZER_ENDPOINT_NAME", "memecoin-optimizer-endpoint")

# Tabelas DynamoDB
trader_table = dynamodb.Table(TRADER_TABLE_NAME)
optimizer_table = dynamodb.Table(OPTIMIZER_TABLE_NAME)

def get_historical_trades(days_back=30):
    """Recupera dados históricos de trades do DynamoDB."""
    try:
        # Calcular data de início
        start_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        # Scan da tabela de trades
        response = trader_table.scan(
            FilterExpression="entry_time >= :start_date",
            ExpressionAttributeValues={":start_date": start_date}
        )
        
        trades = response["Items"]
        
        # Converter Decimal para float para compatibilidade com pandas
        for trade in trades:
            for key, value in trade.items():
                if isinstance(value, Decimal):
                    trade[key] = float(value)
        
        logger.info(f"Recuperados {len(trades)} trades dos últimos {days_back} dias.")
        return trades
    
    except ClientError as e:
        logger.error(f"Erro de cliente DynamoDB ao recuperar trades históricos: {e}")
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao recuperar trades históricos: {e}")
        return []

def calculate_performance_metrics(trades):
    """Calcula métricas de performance dos trades."""
    try:
        if not trades:
            return {}
        
        df = pd.DataFrame(trades)
        
        # Filtrar apenas trades fechados
        closed_trades = df[df["status"] == "closed"]
        
        if closed_trades.empty:
            return {
                "total_trades": len(trades),
                "closed_trades": 0,
                "win_rate": 0,
                "avg_pnl": 0,
                "total_pnl": 0,
                "max_drawdown": 0,
                "sharpe_ratio": 0,
                "avg_trade_duration": 0
            }
        
        # Calcular métricas
        total_trades = len(closed_trades)
        winning_trades = len(closed_trades[closed_trades["pnl"] > 0])
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        avg_pnl = closed_trades["pnl"].mean()
        total_pnl = closed_trades["pnl"].sum()
        
        # Calcular drawdown máximo
        cumulative_pnl = closed_trades["pnl"].cumsum()
        running_max = cumulative_pnl.expanding().max()
        drawdown = (cumulative_pnl - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calcular Sharpe ratio simplificado
        if closed_trades["pnl"].std() > 0:
            sharpe_ratio = avg_pnl / closed_trades["pnl"].std()
        else:
            sharpe_ratio = 0
        
        metrics = {
            "total_trades": total_trades,
            "closed_trades": len(closed_trades),
            "win_rate": win_rate,
            "avg_pnl": avg_pnl,
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
            "sharpe_ratio": sharpe_ratio,
            "avg_trade_duration": calculate_avg_trade_duration(closed_trades)
        }
        
        logger.info(f"Métricas calculadas: Win Rate: {win_rate:.2%}, Total P&L: ${total_pnl:.2f}")
        return metrics
    
    except Exception as e:
        logger.error(f"Erro ao calcular métricas de performance: {e}")
        return {}

def calculate_avg_trade_duration(trades_df):
    """Calcula a duração média dos trades em horas."""
    try:
        if trades_df.empty:
            return 0
        
        durations = []
        for _, trade in trades_df.iterrows():
            if "entry_time" in trade and "exit_time" in trade:
                entry_time = pd.to_datetime(trade["entry_time"])
                exit_time = pd.to_datetime(trade["exit_time"])
                duration = (exit_time - entry_time).total_seconds() / 3600  # em horas
                durations.append(duration)
        
        return np.mean(durations) if durations else 0
    
    except Exception as e:
        logger.error(f"Erro ao calcular duração média: {e}")
        return 0

def load_current_config():
    """Carrega a configuração atual do S3."""
    try:
        response = s3.get_object(Bucket=CONFIG_BUCKET, Key=CONFIG_KEY)
        config = json.loads(response["Body"].read().decode("utf-8"))
        logger.info("Configuração atual carregada do S3.")
        return config
    
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            # Configuração padrão se não existir
            logger.info("Configuração não encontrada, usando padrão.")
            return get_default_config()
        else:
            logger.error(f"Erro ao carregar configuração: {e}")
            raise
    
    except Exception as e:
        logger.error(f"Erro ao carregar configuração: {e}")
        return get_default_config()

def get_default_config():
    """Retorna a configuração padrão dos agentes."""
    return {
        "discoverer": {
            "webhook_timeout": 30,
            "retry_attempts": 3
        },
        "analyzer": {
            "quality_score_threshold": 60,
            "sentiment_weight": 0.15,
            "on_chain_weight": 0.60,
            "social_weight": 0.25
        },
        "trader": {
            "high_score_sl": 0.10,
            "high_score_tp": 0.30,
            "high_score_position": 0.15,
            "medium_score_sl": 0.15,
            "medium_score_tp": 0.25,
            "medium_score_position": 0.10,
            "low_score_sl": 0.20,
            "low_score_tp": 0.20,
            "low_score_position": 0.05,
            "max_slippage": 0.02
        },
        "optimizer": {
            "optimization_frequency": "weekly",
            "ab_test_percentage": 0.15,
            "min_trades_for_optimization": 50
        }
    }

def invoke_sagemaker_optimizer_endpoint(historical_data, current_metrics):
    """Invoca o endpoint do SageMaker para otimização de parâmetros."""
    try:
        # Preparar os dados históricos e métricas atuais para o modelo SageMaker
        # O formato exato do payload depende do que o modelo espera.
        # Aqui, estamos enviando uma lista de trades e as métricas atuais.
        payload = {
            "historical_data": historical_data,
            "current_metrics": current_metrics
        }
        
        response = sagemaker_runtime.invoke_endpoint(
            EndpointName=SAGEMAKER_OPTIMIZER_ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(payload)
        )
        
        result = json.loads(response["Body"].read().decode())
        
        # O modelo deve retornar os melhores parâmetros e o valor objetivo
        best_params = result.get("best_params", {})
        best_value = result.get("best_value", 0.0)
        
        logger.info(f"Otimização do SageMaker: Melhores parâmetros: {best_params}, Melhor valor: {best_value:.4f}")
        return best_params, best_value
        
    except ClientError as e:
        logger.error(f"Erro ao invocar endpoint SageMaker para otimização: {e}")
        return {}, 0
    except Exception as e:
        logger.error(f"Erro inesperado ao invocar endpoint SageMaker para otimização: {e}")
        return {}, 0

def create_ab_test_config(current_config, optimized_params):
    """Cria configuração para A/B testing."""
    try:
        # Configuração A (atual)
        config_a = current_config.copy()
        
        # Configuração B (otimizada)
        config_b = current_config.copy()
        
        # Aplicar parâmetros otimizados à configuração B
        if "quality_threshold" in optimized_params:
            config_b["analyzer"]["quality_score_threshold"] = optimized_params["quality_threshold"]
        
        if "high_score_sl" in optimized_params:
            config_b["trader"]["high_score_sl"] = optimized_params["high_score_sl"]
        
        if "high_score_tp" in optimized_params:
            config_b["trader"]["high_score_tp"] = optimized_params["high_score_tp"]
        
        if "medium_score_sl" in optimized_params:
            config_b["trader"]["medium_score_sl"] = optimized_params["medium_score_sl"]
        
        if "medium_score_tp" in optimized_params:
            config_b["trader"]["medium_score_tp"] = optimized_params["medium_score_tp"]
        
        # Adicionar metadados de A/B test
        ab_test_config = {
            "ab_test_active": True,
            "ab_test_start_time": datetime.utcnow().isoformat(),
            "ab_test_percentage": current_config["optimizer"]["ab_test_percentage"],
            "config_a": config_a,
            "config_b": config_b
        }
        
        return ab_test_config
    
    except Exception as e:
        logger.error(f"Erro ao criar configuração A/B test: {e}")
        return current_config

def save_config_to_s3(config):
    """Salva a configuração atualizada no S3."""
    try:
        config_json = json.dumps(config, indent=2, default=str)
        
        s3.put_object(
            Bucket=CONFIG_BUCKET,
            Key=CONFIG_KEY,
            Body=config_json,
            ContentType="application/json"
        )
        
        logger.info("Configuração atualizada salva no S3.")
        
        # Criar backup com timestamp
        backup_key = f"config_backups/config_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}.json"
        s3.put_object(
            Bucket=CONFIG_BUCKET,
            Key=backup_key,
            Body=config_json,
            ContentType="application/json"
        )
        
        logger.info(f"Backup da configuração salvo: {backup_key}")
    
    except Exception as e:
        logger.error(f"Erro ao salvar configuração no S3: {e}")
        raise

def save_optimization_results(optimization_id, results):
    """Salva os resultados da otimização no DynamoDB."""
    try:
        item = {
            "optimizationId": optimization_id,
            "timestamp": datetime.utcnow().isoformat(),
            "best_params": results["best_params"],
            "best_value": Decimal(str(results["best_value"])),
            "historical_metrics": results["historical_metrics"],
            "optimization_type": "sagemaker_ml",
            "status": "completed"
        }
        
        # Converter valores float para Decimal
        for key, value in item.items():
            if isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, float):
                        value[k] = Decimal(str(v))
        
        optimizer_table.put_item(Item=item)
        logger.info(f"Resultados da otimização {optimization_id} salvos.")
    
    except ClientError as e:
        logger.error(f"Erro de cliente DynamoDB ao salvar resultados da otimização: {e}")
    except Exception as e:
        logger.error(f"Erro inesperado ao salvar resultados da otimização: {e}")

def lambda_handler(event, context):
    """Função principal do Lambda para o Agente Optimizer."""
    try:
        logger.info("Agente Optimizer iniciado.")
        
        # Recuperar dados históricos
        historical_trades = get_historical_trades(days_back=30)
        
        if len(historical_trades) < 10:
            logger.warning("Dados históricos insuficientes para otimização.")
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Dados insuficientes para otimização."}) 
            }
        
        # Calcular métricas atuais
        current_metrics = calculate_performance_metrics(historical_trades)
        
        # Carregar configuração atual
        current_config = load_current_config()
        
        # Executar otimização via SageMaker
        best_params, best_value = invoke_sagemaker_optimizer_endpoint(historical_trades, current_metrics)
        
        if best_params:
            # Criar configuração para A/B testing
            ab_test_config = create_ab_test_config(current_config, best_params)
            
            # Salvar nova configuração
            save_config_to_s3(ab_test_config)
            
            # Salvar resultados da otimização
            optimization_id = f"opt_{int(datetime.utcnow().timestamp())}"
            optimization_results = {
                "best_params": best_params,
                "best_value": best_value,
                "historical_metrics": current_metrics
            }
            
            save_optimization_results(optimization_id, optimization_results)
            
            logger.info(f"Otimização concluída. A/B test iniciado com {ab_test_config["ab_test_percentage"]:.0%} do tráfego.")
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Agente Optimizer executado com sucesso.",
                "optimization_id": optimization_id if best_params else None,
                "current_metrics": current_metrics
            }, default=str)
        }
    
    except Exception as e:
        logger.error(f"Erro no Agente Optimizer: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Para teste local
if __name__ == "__main__":
    # Simula dados históricos para teste
    test_trades = [
        {
            "trade_id": "test_1",
            "quality_score": 75,
            "entry_price": 1.0,
            "exit_price": 1.2,
            "pnl": 20,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T10:00:00Z",
            "exit_time": "2024-07-01T11:00:00Z"
        },
        {
            "trade_id": "test_2",
            "quality_score": 65,
            "entry_price": 1.0,
            "exit_price": 0.9,
            "pnl": -10,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T12:00:00Z",
            "exit_time": "2024-07-01T13:00:00Z"
        },
        {
            "trade_id": "test_3",
            "quality_score": 80,
            "entry_price": 1.0,
            "exit_price": 1.3,
            "pnl": 30,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T14:00:00Z",
            "exit_time": "2024-07-01T15:00:00Z"
        },
        {
            "trade_id": "test_4",
            "quality_score": 50,
            "entry_price": 1.0,
            "exit_price": 0.8,
            "pnl": -20,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T16:00:00Z",
            "exit_time": "2024-07-01T17:00:00Z"
        },
        {
            "trade_id": "test_5",
            "quality_score": 90,
            "entry_price": 1.0,
            "exit_price": 1.5,
            "pnl": 50,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T18:00:00Z",
            "exit_time": "2024-07-01T19:00:00Z"
        },
        {
            "trade_id": "test_6",
            "quality_score": 70,
            "entry_price": 1.0,
            "exit_price": 1.1,
            "pnl": 10,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T20:00:00Z",
            "exit_time": "2024-07-01T21:00:00Z"
        },
        {
            "trade_id": "test_7",
            "quality_score": 60,
            "entry_price": 1.0,
            "exit_price": 0.95,
            "pnl": -5,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-01T22:00:00Z",
            "exit_time": "2024-07-01T23:00:00Z"
        },
        {
            "trade_id": "test_8",
            "quality_score": 85,
            "entry_price": 1.0,
            "exit_price": 1.4,
            "pnl": 40,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-02T00:00:00Z",
            "exit_time": "2024-07-02T01:00:00Z"
        },
        {
            "trade_id": "test_9",
            "quality_score": 55,
            "entry_price": 1.0,
            "exit_price": 0.7,
            "pnl": -30,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-02T02:00:00Z",
            "exit_time": "2024-07-02T03:00:00Z"
        },
        {
            "trade_id": "test_10",
            "quality_score": 95,
            "entry_price": 1.0,
            "exit_price": 1.6,
            "pnl": 60,
            "amount_usd": 100,
            "status": "closed",
            "entry_time": "2024-07-02T04:00:00Z",
            "exit_time": "2024-07-02T05:00:00Z"
        }
    ]
    
    # Testar cálculo de métricas
    metrics = calculate_performance_metrics(test_trades)
    print("Métricas de teste:", json.dumps(metrics, indent=2, default=str))
    
    # Simular invocação do SageMaker (em um ambiente real, isso chamaria o endpoint)
    # Aqui, vamos simular um retorno para o teste local
    simulated_best_params = {
        "quality_threshold": 70.0,
        "high_score_sl": 0.12,
        "high_score_tp": 0.35,
        "medium_score_sl": 0.18,
        "medium_score_tp": 0.28
    }
    simulated_best_value = 0.75
    
    # Testar o lambda_handler com dados simulados
    
    # Simula um evento de execução do Lambda
    test_event = {}
    
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))














