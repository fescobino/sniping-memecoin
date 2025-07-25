import json
import logging
import os
import pandas as pd
import boto3
from datetime import datetime
from botocore.exceptions import ClientError

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Variáveis de ambiente (mantidas aqui para clareza, mas podem ser sobrescritas por mocks)
RAW_DATA_BUCKET = os.environ.get("RAW_DATA_BUCKET", "memecoin-sniping-raw-data")
PROCESSED_DATA_BUCKET = os.environ.get("PROCESSED_DATA_BUCKET", "memecoin-sniping-processed-data")

class ETLProcessor:
    def __init__(self):
        # Inicializa o cliente S3 aqui para que o mock possa ser aplicado antes
        self.s3 = boto3.client("s3")

    def process_raw_data(self, raw_file_key: str) -> pd.DataFrame:
        """Lê dados brutos do S3, processa e retorna um DataFrame."""
        try:
            response = self.s3.get_object(Bucket=RAW_DATA_BUCKET, Key=raw_file_key)
            raw_data = response["Body"].read().decode("utf-8")
            
            # Assumindo que o raw_data é um CSV simples para demonstração
            df = pd.read_csv(io.StringIO(raw_data))
            
            # Exemplo de processamento: adicionar uma coluna de timestamp de processamento
            df["processed_timestamp"] = datetime.now().isoformat()
            
            logger.info(f"Dados brutos {raw_file_key} processados com sucesso.")
            return df
            
        except ClientError as e:
            logger.error(f"Erro de cliente S3 ao ler dados brutos {raw_file_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao processar dados brutos {raw_file_key}: {e}")
            raise

    def save_processed_data(self, df: pd.DataFrame, processed_file_key: str) -> None:
        """Salva o DataFrame processado no S3."""
        try:
            # Salvar como Parquet para eficiência
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0)
            
            self.s3.put_object(
                Bucket=PROCESSED_DATA_BUCKET,
                Key=processed_file_key,
                Body=parquet_buffer.getvalue(),
                ContentType="application/x-parquet"
            )
            logger.info(f"Dados processados salvos em s3://{PROCESSED_DATA_BUCKET}/{processed_file_key}")
            
        except ClientError as e:
            logger.error(f"Erro de cliente S3 ao salvar dados processados {processed_file_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar dados processados {processed_file_key}: {e}")
            raise

def lambda_handler(event, context):
    """Função principal do Lambda para o ETL Processor."""
    try:
        logger.info("ETL Processor iniciado.")
        processor = ETLProcessor()

        # O evento deve ser acionado por um novo objeto no bucket RAW_DATA_BUCKET
        for record in event["Records"]:
            bucket_name = record["s3"]["bucket"]["name"]
            object_key = record["s3"]["object"]["key"]
            
            logger.info(f"Processando arquivo: s3://{bucket_name}/{object_key}")
            
            # Processar dados brutos
            processed_df = processor.process_raw_data(object_key)
            
            # Definir chave para o arquivo processado (ex: mudando a extensão)
            processed_file_key = object_key.replace("raw/", "processed/").replace(".csv", ".parquet")
            
            # Salvar dados processados
            processor.save_processed_data(processed_df, processed_file_key)
            
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "ETL Processamento concluído com sucesso."})
        }

    except Exception as e:
        logger.error(f"Erro no ETL Processor: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

# Para teste local
if __name__ == "__main__":
    import io
    
    # Configurações de ambiente para teste local
    os.environ["RAW_DATA_BUCKET"] = "memecoin-sniping-raw-data-local"
    os.environ["PROCESSED_DATA_BUCKET"] = "memecoin-sniping-processed-data-local"

    # Mock de S3 para teste local
    class MockS3Client:
        def get_object(self, Bucket, Key):
            if Key == "raw/test_data.csv":
                return {"Body": io.BytesIO(b"col1,col2\n1,a\n2,b\n3,c")}
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
            
        def put_object(self, Bucket, Key, Body, ContentType=None):
            print(f"Mock S3: Objeto salvo no bucket {Bucket} com chave {Key}")

    # Atribui o mock ao boto3.client ANTES de instanciar ETLProcessor
    boto3_client_original = boto3.client
    boto3.client = lambda service_name: MockS3Client() if service_name == "s3" else boto3_client_original(service_name)

    # Simular um evento S3
    test_event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "memecoin-sniping-raw-data-local"},
                    "object": {"key": "raw/test_data.csv"}
                }
            }
        ]
    }

    print("\n--- Teste de execução do ETL Processor ---")
    result = lambda_handler(test_event, None)
    print(json.dumps(result, indent=2))


