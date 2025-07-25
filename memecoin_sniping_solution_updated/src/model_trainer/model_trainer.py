import json
import logging
import os
import pandas as pd
import numpy as np
import joblib
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import f1_score, roc_auc_score
import boto3
from botocore.exceptions import ClientError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Variáveis de ambiente
PROCESSED_DATA_BUCKET = os.environ.get("PROCESSED_DATA_BUCKET", "memecoin-sniping-processed-data")
MODEL_BUCKET = os.environ.get("MODEL_BUCKET", "memecoin-sniping-models")
STAGING_LOCAL_MODEL_KEY = os.environ.get("STAGING_LOCAL_MODEL_KEY", "optimizer/model/staging/local_model.pkl")
STAGING_SAGEMAKER_MODEL_KEY = os.environ.get("STAGING_SAGEMAKER_MODEL_KEY", "optimizer/model/staging/sagemaker_model.pkl")
SAGEMAKER_TRAINING_JOB_ROLE_ARN = os.environ.get("SAGEMAKER_TRAINING_JOB_ROLE_ARN")
SAGEMAKER_TRAINING_IMAGE = os.environ.get("SAGEMAKER_TRAINING_IMAGE") # Ex: 'your-ecr-repo/sagemaker-sklearn-container:latest'

class ModelTrainer:
    def __init__(self):
        # Inicializa os clientes AWS aqui para que o mock possa ser aplicado antes
        self.s3 = boto3.client("s3", region_name="us-east-1")
        self.sagemaker = boto3.client("sagemaker", region_name="us-east-1")

    def load_processed_data(self, days_back: int = 7) -> pd.DataFrame:
        """Carrega dados processados do S3 para treinamento."""
        try:
            # Simula o carregamento de dados processados
            # Em um cenário real, você listaria objetos no bucket e concatenaria
            # Para este exemplo, vamos criar um DataFrame simulado
            data = {
                'feature1': np.random.rand(100),
                'feature2': np.random.rand(100) * 10,
                'target': np.random.randint(0, 2, 100) # 0 ou 1 para classificação
            }
            df = pd.DataFrame(data)
            logger.info(f"Dados processados simulados carregados. Shape: {df.shape}")
            return df
        except Exception as e:
            logger.error(f"Erro ao carregar dados processados: {e}")
            raise

    def train_local_model(self, df: pd.DataFrame) -> dict:
        """Treina um modelo localmente e avalia seu desempenho."""
        logger.info("Iniciando treinamento de modelo local...")
        
        X = df[["feature1", "feature2"]]
        y = df["target"]
        
        X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, random_state=42)
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        predictions = model.predict(X_val)
        f1 = f1_score(y_val, predictions)
        
        # Simular ROI (exemplo: se target=1, ganha 10%; se target=0, perde 5%)
        simulated_roi = np.mean([0.10 if p == 1 else -0.05 for p in predictions])
        
        logger.info(f"Treinamento local concluído. F1-Score: {f1:.4f}, ROI Simulado: {simulated_roi:.4f}")
        
        # Salvar modelo localmente
        local_model_path = "/tmp/local_model.pkl"
        joblib.dump(model, local_model_path)
        
        # Upload para S3 staging
        self.s3.upload_file(local_model_path, MODEL_BUCKET, STAGING_LOCAL_MODEL_KEY)
        logger.info(f"Modelo local salvo em S3: s3://{MODEL_BUCKET}/{STAGING_LOCAL_MODEL_KEY}")
        
        return {
            "f1_score": f1,
            "simulated_roi": simulated_roi,
            "model_s3_key": STAGING_LOCAL_MODEL_KEY
        }

    def trigger_sagemaker_training_job(self, training_data_s3_uri: str) -> str:
        """Aciona um job de treinamento no SageMaker."""
        logger.info(f"Acionando job de treinamento SageMaker com dados de {training_data_s3_uri}...")
        
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        job_name = f"memecoin-optimizer-training-{timestamp}"
        
        try:
            response = self.sagemaker.create_training_job(
                TrainingJobName=job_name,
                HyperParameters={
                    'sagemaker_program': 'train.py', # Seu script de treinamento
                    'sagemaker_submit_directory': f's3://{MODEL_BUCKET}/sagemaker_scripts/source.tar.gz'
                },
                AlgorithmSpecification={
                    'TrainingImage': SAGEMAKER_TRAINING_IMAGE,
                    'TrainingInputMode': 'File'
                },
                RoleArn=SAGEMAKER_TRAINING_JOB_ROLE_ARN,
                InputDataConfig=[
                    {
                        'ChannelName': 'training',
                        'DataSource': {
                            'S3DataSource': {
                                'S3DataType': 'S3Prefix',
                                'S3Uri': training_data_s3_uri,
                                'S3DataDistributionType': 'FullyReplicated'
                            }
                        },
                        'ContentType': 'text/csv'
                    }
                ],
                OutputDataConfig={
                    'S3OutputPath': f's3://{MODEL_BUCKET}/sagemaker_output/'
                },
                ResourceConfig={
                    'InstanceType': 'ml.m5.large',
                    'InstanceCount': 1,
                    'VolumeSizeInGB': 20
                },
                StoppingCondition={
                    'MaxRuntimeInSeconds': 3600 # 1 hora
                }
            )
            logger.info(f"Job de treinamento SageMaker acionado: {response['TrainingJobArn']}")
            return response['TrainingJobArn']
        except ClientError as e:
            logger.error(f"Erro de cliente SageMaker ao acionar job de treinamento: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao acionar job de treinamento SageMaker: {e}")
            raise

    def evaluate_model(self, model_s3_key: str, df: pd.DataFrame) -> dict:
        """Avalia um modelo carregado do S3."""
        logger.info(f"Avaliando modelo de s3://{MODEL_BUCKET}/{model_s3_key}...")
        
        # Baixar modelo do S3
        local_model_path = "/tmp/model_to_evaluate.pkl"
        self.s3.download_file(MODEL_BUCKET, model_s3_key, local_model_path)
        model = joblib.load(local_model_path)
        
        X = df[["feature1", "feature2"]]
        y = df["target"]
        
        # Usar o mesmo split de validação ou um novo conjunto de teste
        _, X_val, _, y_val = train_test_split(X, y, test_size=0.3, random_state=42)
        
        predictions = model.predict(X_val)
        f1 = f1_score(y_val, predictions)
        simulated_roi = np.mean([0.10 if p == 1 else -0.05 for p in predictions])
        
        logger.info(f"Avaliação concluída. F1-Score: {f1:.4f}, ROI Simulado: {simulated_roi:.4f}")
        return {"f1_score": f1, "simulated_roi": simulated_roi}

    def promote_model_if_improved(self, new_model_metrics: dict, current_production_model_key: str) -> bool:
        """Compara o novo modelo com o de produção e promove se houver melhoria significativa."""
        logger.info("Verificando se o novo modelo deve ser promovido...")
        
        # Para simplificar, vamos carregar um modelo de produção simulado
        # Em um cenário real, você teria métricas históricas do modelo de produção
        current_prod_metrics = {"f1_score": 0.60, "simulated_roi": 0.03} # Métricas simuladas do modelo em produção
        
        f1_improvement = (new_model_metrics["f1_score"] - current_prod_metrics["f1_score"]) / current_prod_metrics["f1_score"]
        roi_improvement = (new_model_metrics["simulated_roi"] - current_prod_metrics["simulated_roi"]) / current_prod_metrics["simulated_roi"]
        
        if f1_improvement >= 0.30 or roi_improvement >= 0.30:
            logger.info(f"Melhoria significativa detectada! F1-Score: {f1_improvement:.2%}, ROI: {roi_improvement:.2%}")
            # Chamar o ModelDeployer para promover o modelo
            # Isso seria uma chamada a outro Lambda ou serviço
            logger.info(f"Modelo {new_model_metrics['model_s3_key']} qualificado para promoção.")
            return True
        else:
            logger.info(f"Melhoria insuficiente para promoção. F1-Score: {f1_improvement:.2%}, ROI: {roi_improvement:.2%}")
            return False

def lambda_handler(event, context):
    """Função principal do Lambda para o Model Trainer."""
    try:
        logger.info("Model Trainer iniciado.")
        trainer = ModelTrainer()
        
        mode = os.environ.get("MODE", "paper")
        
        if mode == "paper":
            logger.info("Modo Paper: Treinamento local semanal.")
            df = trainer.load_processed_data()
            if df.empty:
                logger.warning("Nenhum dado para treinamento no modo paper.")
                return {"statusCode": 200, "body": json.dumps({"message": "Nenhum dado para treinamento."})}
            
            train_results = trainer.train_local_model(df)
            
            # Simular promoção para produção no modo paper (apenas para teste)
            # Em um cenário real, o modelo local seria usado para testes A/B ou validação
            # antes de ser considerado para produção real.
            if trainer.promote_model_if_improved(train_results, "optimizer/model/production/model.pkl"):
                logger.info("Modelo local simulado promovido para produção (apenas para teste em paper mode).")
                # Aqui você chamaria o ModelDeployer para copiar o modelo local para production/model.pkl
                # self.s3.copy_object(Bucket=MODEL_BUCKET, CopySource={'Bucket': MODEL_BUCKET, 'Key': STAGING_LOCAL_MODEL_KEY}, Key=PRODUCTION_MODEL_KEY)
            
        elif mode == "real":
            logger.info("Modo Real: Acionando job de treinamento SageMaker.")
            # Assumindo que os dados de treinamento já estão no S3
            training_data_s3_uri = f"s3://{PROCESSED_DATA_BUCKET}/processed/"
            trainer.trigger_sagemaker_training_job(training_data_s3_uri)
            
            # Em um cenário real, você esperaria o job do SageMaker terminar
            # e então avaliaria o modelo resultante antes de promover.
            # Isso geralmente é feito por outro Lambda acionado pelo status do job SageMaker.
            
        else:
            logger.warning(f"Modo desconhecido: {mode}. Nenhuma ação de treinamento executada.")
            
        return {
            "statusCode": 200,
            "body": json.dumps({"message": f"Model Trainer executado em modo {mode}."})
        }

    except Exception as e:
        logger.error(f"Erro no Model Trainer: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Para teste local
if __name__ == "__main__":
    # Configurações de ambiente para teste local
    os.environ["PROCESSED_DATA_BUCKET"] = "memecoin-sniping-processed-data-local"
    os.environ["MODEL_BUCKET"] = "memecoin-sniping-models-local"
    os.environ["STAGING_LOCAL_MODEL_KEY"] = "optimizer/model/staging/local_model.pkl"
    os.environ["STAGING_SAGEMAKER_MODEL_KEY"] = "optimizer/model/staging/sagemaker_model.pkl"
    os.environ["SAGEMAKER_TRAINING_JOB_ROLE_ARN"] = "arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-ExecutionRole-20231231T123456"
    os.environ["SAGEMAKER_TRAINING_IMAGE"] = "123456789012.dkr.ecr.us-east-1.amazonaws.com/sagemaker-sklearn-container:latest"

    # Mock de S3 e SageMaker para teste local
    class MockS3Client:
        def upload_file(self, Filename, Bucket, Key):
            print(f"Mock S3: Upload de {Filename} para s3://{Bucket}/{Key}")
        def download_file(self, Bucket, Key, Filename):
            print(f"Mock S3: Download de s3://{Bucket}/{Key} para {Filename}")
            # Criar um arquivo dummy para simular o download
            with open(Filename, 'wb') as f:
                joblib.dump(RandomForestClassifier(), f) # Salva um modelo dummy

    class MockSageMakerClient:
        def create_training_job(self, **kwargs):
            print(f"Mock SageMaker: Criando job de treinamento {kwargs['TrainingJobName']}")
            return {"TrainingJobArn": "arn:aws:sagemaker:us-east-1:123456789012:training-job/mock-job"}

    # Atribui o mock ao boto3.client ANTES de instanciar ModelTrainer
    boto3_original_client = boto3.client
    def mock_boto3_client(service_name, region_name=None):
        if service_name == "s3":
            return MockS3Client()
        elif service_name == "sagemaker":
            return MockSageMakerClient()
        else:
            return boto3_original_client(service_name, region_name=region_name)

    boto3.client = mock_boto3_client

    print("\n--- Teste de treinamento em Paper Mode ---")
    os.environ["MODE"] = "paper"
    result_paper = lambda_handler({}, None)
    print(json.dumps(result_paper, indent=2))

    print("\n--- Teste de treinamento em Real Mode ---")
    os.environ["MODE"] = "real"
    result_real = lambda_handler({}, None)
    print(json.dumps(result_real, indent=2))


