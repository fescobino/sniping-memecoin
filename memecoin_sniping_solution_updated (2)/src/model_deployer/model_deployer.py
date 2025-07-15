import json
import logging
import os
import boto3
from botocore.exceptions import ClientError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
sagemaker = boto3.client("sagemaker")
s3 = boto3.client("s3")

# Variáveis de ambiente
MODEL_BUCKET = os.environ.get("MODEL_BUCKET", "memecoin-sniping-models")
PRODUCTION_MODEL_KEY = os.environ.get("PRODUCTION_MODEL_KEY", "optimizer/model/production/model.pkl")
STAGING_SAGEMAKER_MODEL_KEY = os.environ.get("STAGING_SAGEMAKER_MODEL_KEY", "optimizer/model/staging/sagemaker_model.pkl")
SAGEMAKER_ROLE_ARN = os.environ.get("SAGEMAKER_ROLE_ARN")
SAGEMAKER_MODEL_NAME = os.environ.get("SAGEMAKER_MODEL_NAME", "MemecoinOptimizerModel")
SAGEMAKER_ENDPOINT_CONFIG_NAME = os.environ.get("SAGEMAKER_ENDPOINT_CONFIG_NAME", "MemecoinOptimizerEndpointConfig")
SAGEMAKER_ENDPOINT_NAME = os.environ.get("SAGEMAKER_ENDPOINT_NAME", "memecoin-optimizer-endpoint")

class ModelDeployer:
    def __init__(self):
        pass

    def deploy_model_to_sagemaker(self, model_data_url: str) -> str:
        """Implanta um modelo no SageMaker e cria/atualiza um endpoint."""
        try:
            # 1. Criar Modelo SageMaker
            # Verifica se o modelo já existe para evitar recriação desnecessária
            try:
                sagemaker.describe_model(ModelName=SAGEMAKER_MODEL_NAME)
                logger.info(f"Modelo SageMaker {SAGEMAKER_MODEL_NAME} já existe. Atualizando...")
                # Se o modelo já existe, podemos pular a criação e ir direto para a configuração do endpoint
                # ou criar uma nova versão do modelo se necessário para A/B testing etc.
                # Por simplicidade, vamos apenas garantir que o endpoint config aponte para o modelo correto.
            except ClientError as e:
                if e.response["Error"]["Code"] == "ValidationException" and "Could not find model" in str(e):
                    logger.info(f"Criando novo modelo SageMaker: {SAGEMAKER_MODEL_NAME}")
                    create_model_response = sagemaker.create_model(
                        ModelName=SAGEMAKER_MODEL_NAME,
                        PrimaryContainer={
                            "Image": os.environ.get("SAGEMAKER_IMAGE_URI"), # URI da imagem do seu algoritmo
                            "ModelDataUrl": model_data_url
                        },
                        ExecutionRoleArn=SAGEMAKER_ROLE_ARN
                    )
                    logger.info(f"Modelo SageMaker criado: {create_model_response["ModelArn"]}")
                else:
                    raise

            # 2. Criar Configuração de Endpoint
            # Sempre criar uma nova configuração de endpoint para permitir atualizações sem downtime
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            endpoint_config_name = f"{SAGEMAKER_ENDPOINT_CONFIG_NAME}-{timestamp}"
            
            create_endpoint_config_response = sagemaker.create_endpoint_config(
                EndpointConfigName=endpoint_config_name,
                ProductionVariants=[
                    {
                        "VariantName": "AllTraffic",
                        "ModelName": SAGEMAKER_MODEL_NAME,
                        "InitialInstanceCount": 1,
                        "InstanceType": "ml.t2.medium", # Tipo de instância, ajustar conforme necessidade
                        "InitialVariantWeight": 1
                    }
                ]
            )
            logger.info(f"Configuração de Endpoint SageMaker criada: {create_endpoint_config_response["EndpointConfigArn"]}")

            # 3. Criar/Atualizar Endpoint
            try:
                sagemaker.describe_endpoint(EndpointName=SAGEMAKER_ENDPOINT_NAME)
                logger.info(f"Endpoint SageMaker {SAGEMAKER_ENDPOINT_NAME} já existe. Atualizando...")
                update_endpoint_response = sagemaker.update_endpoint(
                    EndpointName=SAGEMAKER_ENDPOINT_NAME,
                    EndpointConfigName=endpoint_config_name
                )
                logger.info(f"Endpoint SageMaker atualizado: {update_endpoint_response["EndpointArn"]}")
                return update_endpoint_response["EndpointArn"]
            except ClientError as e:
                if e.response["Error"]["Code"] == "ValidationException" and "Could not find endpoint" in str(e):
                    logger.info(f"Criando novo endpoint SageMaker: {SAGEMAKER_ENDPOINT_NAME}")
                    create_endpoint_response = sagemaker.create_endpoint(
                        EndpointName=SAGEMAKER_ENDPOINT_NAME,
                        EndpointConfigName=endpoint_config_name
                    )
                    logger.info(f"Endpoint SageMaker criado: {create_endpoint_response["EndpointArn"]}")
                    return create_endpoint_response["EndpointArn"]
                else:
                    raise

        except ClientError as e:
            logger.error(f"Erro de cliente SageMaker ao implantar modelo: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao implantar modelo no SageMaker: {e}")
            raise

    def promote_model(self, source_key: str, destination_key: str) -> None:
        """Promove um modelo de staging para produção no S3."""
        try:
            s3.copy_object(
                Bucket=MODEL_BUCKET,
                CopySource={
                    "Bucket": MODEL_BUCKET,
                    "Key": source_key
                },
                Key=destination_key
            )
            logger.info(f"Modelo promovido de s3://{MODEL_BUCKET}/{source_key} para s3://{MODEL_BUCKET}/{destination_key}")
        except ClientError as e:
            logger.error(f"Erro de cliente S3 ao promover modelo: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao promover modelo: {e}")
            raise

def lambda_handler(event, context):
    """Função principal do Lambda para o Model Deployer."""
    try:
        logger.info("Model Deployer iniciado.")
        deployer = ModelDeployer()

        # O evento deve conter informações sobre qual modelo implantar/promover
        # Exemplo de evento: {"action": "deploy_sagemaker", "model_s3_key": "optimizer/model/staging/sagemaker_model.pkl"}
        # Ou: {"action": "promote_model", "source": "staging/sagemaker_model.pkl", "destination": "production/model.pkl"}
        
        action = event.get("action")

        if action == "deploy_sagemaker":
            model_s3_key = event.get("model_s3_key")
            if not model_s3_key:
                raise ValueError("model_s3_key é obrigatório para a ação deploy_sagemaker.")
            
            model_data_url = f"s3://{MODEL_BUCKET}/{model_s3_key}"
            endpoint_arn = deployer.deploy_model_to_sagemaker(model_data_url)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Modelo implantado no SageMaker", "endpoint_arn": endpoint_arn})
            }
        elif action == "promote_model":
            source_key = event.get("source")
            destination_key = event.get("destination")
            if not source_key or not destination_key:
                raise ValueError("source e destination são obrigatórios para a ação promote_model.")
            
            deployer.promote_model(source_key, destination_key)
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Modelo promovido com sucesso."})
            }
        else:
            raise ValueError(f"Ação desconhecida: {action}")

    except Exception as e:
        logger.error(f"Erro no Model Deployer: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Para teste local
if __name__ == "__main__":
    # Configurações de ambiente para teste local
    os.environ["MODEL_BUCKET"] = "memecoin-sniping-models-local"
    os.environ["SAGEMAKER_ROLE_ARN"] = "arn:aws:iam::123456789012:role/service-role/AmazonSageMaker-ExecutionRole-20231231T123456"
    os.environ["SAGEMAKER_IMAGE_URI"] = "123456789012.dkr.ecr.us-east-1.amazonaws.com/sagemaker-sklearn-container:latest"

    # Mock de S3 e SageMaker para teste local
    class MockS3Client:
        def copy_object(self, Bucket, CopySource, Key):
            print(f"Mock S3: Copiando {CopySource["Key"]} para {Key} no bucket {Bucket}")

    class MockSageMakerClient:
        def describe_model(self, ModelName):
            if ModelName == os.environ["SAGEMAKER_MODEL_NAME"]:
                # Simula que o modelo existe
                return {"ModelArn": "arn:aws:sagemaker:us-east-1:123456789012:model/MemecoinOptimizerModel"}
            raise ClientError({"Error": {"Code": "ValidationException"}}, "DescribeModel")

        def create_model(self, ModelName, PrimaryContainer, ExecutionRoleArn):
            print(f"Mock SageMaker: Criando modelo {ModelName}")
            return {"ModelArn": f"arn:aws:sagemaker:us-east-1:123456789012:model/{ModelName}"}

        def create_endpoint_config(self, EndpointConfigName, ProductionVariants):
            print(f"Mock SageMaker: Criando configuração de endpoint {EndpointConfigName}")
            return {"EndpointConfigArn": f"arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/{EndpointConfigName}"}

        def describe_endpoint(self, EndpointName):
            if EndpointName == os.environ["SAGEMAKER_ENDPOINT_NAME"]:
                # Simula que o endpoint existe
                return {"EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/memecoin-optimizer-endpoint"}
            raise ClientError({"Error": {"Code": "ValidationException"}}, "DescribeEndpoint")

        def update_endpoint(self, EndpointName, EndpointConfigName):
            print(f"Mock SageMaker: Atualizando endpoint {EndpointName} com config {EndpointConfigName}")
            return {"EndpointArn": f"arn:aws:sagemaker:us-east-1:123456789012:endpoint/{EndpointName}"}

        def create_endpoint(self, EndpointName, EndpointConfigName):
            print(f"Mock SageMaker: Criando endpoint {EndpointName} com config {EndpointConfigName}")
            return {"EndpointArn": f"arn:aws:sagemaker:us-east-1:123456789012:endpoint/{EndpointName}"}

    boto3.client = lambda service_name:
        MockS3Client() if service_name == "s3" else \
        MockSageMakerClient() if service_name == "sagemaker" else \
        boto3.client(service_name)

    print("\n--- Teste de implantação de modelo SageMaker ---")
    test_deploy_event = {
        "action": "deploy_sagemaker",
        "model_s3_key": "optimizer/model/staging/sagemaker_model.pkl"
    }
    result_deploy = lambda_handler(test_deploy_event, None)
    print(json.dumps(result_deploy, indent=2))

    print("\n--- Teste de promoção de modelo ---")
    test_promote_event = {
        "action": "promote_model",
        "source": "optimizer/model/staging/sagemaker_model.pkl",
        "destination": "optimizer/model/production/model.pkl"
    }
    result_promote = lambda_handler(test_promote_event, None)
    print(json.dumps(result_promote, indent=2))










