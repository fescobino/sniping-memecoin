import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
import xgboost as xgb
import os
import joblib
# boto3 is opcional para rodar localmente em modo gratuito
try:
    import boto3
    from botocore.exceptions import NoCredentialsError, ClientError
except Exception:  # pragma: no cover - boto3 pode nao estar instalado
    boto3 = None
    class NoCredentialsError(Exception):
        pass
    class ClientError(Exception):
        pass

# Permite desativar o uso do S3 para treinamento 100% local
USE_S3 = bool(int(os.environ.get("USE_S3", "0")))

# Configurações do S3 (podem ser carregadas de variáveis de ambiente ou um arquivo de configuração)
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME", "memecoin-sniping-models")
S3_MODEL_PREFIX = os.environ.get("S3_MODEL_PREFIX", "models/")

# Caminho para os dados históricos
HISTORICAL_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "optimizer", "processed", "historical_data.parquet")

def load_model_from_s3(bucket, key, local_path):
    """Baixa modelo do S3 se boto3 estiver disponível e o uso estiver habilitado."""
    if not USE_S3 or boto3 is None:
        return None
    s3 = boto3.client("s3")
    try:
        s3.download_file(bucket, key, local_path)
        print(f"Modelo baixado de s3://{bucket}/{key} para {local_path}")
        return joblib.load(local_path)
    except NoCredentialsError:
        print("Credenciais da AWS não encontradas.")
        return None
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            print(f"Modelo não encontrado em s3://{bucket}/{key}")
        else:
            print(f"Erro do cliente S3 ao baixar modelo: {e}")
        return None
    except Exception as e:
        print(f"Erro ao carregar modelo do S3: {e}")
        return None

def save_model_to_s3(model, bucket, key, local_path):
    """Salva modelo no S3 se o uso estiver habilitado."""
    if not USE_S3 or boto3 is None:
        return False
    s3 = boto3.client("s3")
    try:
        joblib.dump(model, local_path)
        s3.upload_file(local_path, bucket, key)
        print(f"Modelo salvo em s3://{bucket}/{key}")
        return True
    except NoCredentialsError:
        print("Credenciais da AWS não encontradas. Não foi possível salvar o modelo no S3.")
        return False
    except ClientError as e:
        print(f"Erro do cliente S3 ao salvar modelo: {e}")
        return False
    except Exception as e:
        print(f"Erro ao salvar modelo no S3: {e}")
        return False

def load_historical_data(path):
    """
    Carrega dados históricos de um arquivo parquet.
    Retorna um DataFrame vazio se o arquivo não existir ou estiver vazio.
    """
    if not os.path.exists(path):
        print(f"Arquivo de dados históricos não encontrado em {path}. Retornando DataFrame vazio.")
        return pd.DataFrame()
    try:
        df = pd.read_parquet(path)
        print(f"Dados históricos carregados de: {path} ({len(df)} linhas)")
        return df
    except Exception as e:
        print(f"Erro ao carregar dados históricos de {path}: {e}. Retornando DataFrame vazio.")
        return pd.DataFrame()

def train_model(input_df, local_model_path, s3_model_key):
    """
    Treina um modelo com base nos dados fornecidos e salva localmente e no S3.
    """
    if input_df.empty:
        print("DataFrame de entrada vazio. Não é possível treinar o modelo.")
        return

    # As features agora são todas as colunas exceto 'target'
    if 'target' not in input_df.columns:
        print("Erro: Coluna 'target' não encontrada no DataFrame.")
        return

    X = input_df.drop("target", axis=1)
    y = input_df["target"]

    if X.empty or y.empty:
        print("Dados de treino ou target vazios. Não é possível treinar o modelo.")
        return

    # Dividir os dados em 70% treino / 30% validação
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.3, random_state=42)

    # Treinar RandomForestClassifier
    print("Treinando RandomForestClassifier...")
    rf_model = RandomForestClassifier(n_estimators=100, random_state=42)
    rf_model.fit(X_train, y_train)
    rf_predictions = rf_model.predict(X_val)
    rf_f1 = f1_score(y_val, rf_predictions)
    print(f"F1-score do RandomForest: {rf_f1}")

    # Treinar XGBoostClassifier
    print("Treinando XGBoost...")
    xgb_model = xgb.XGBClassifier(n_estimators=100, use_label_encoder=False, eval_metric='logloss', random_state=42)
    xgb_model.fit(X_train, y_train)
    xgb_predictions = xgb_model.predict(X_val)
    xgb_f1 = f1_score(y_val, xgb_predictions)
    print(f"F1-score do XGBoost: {xgb_f1}")

    # Escolher o melhor modelo com base no F1-score
    if rf_f1 >= xgb_f1:
        best_model = rf_model
        current_f1_score = rf_f1
        model_name = "RandomForest"
    else:
        best_model = xgb_model
        current_f1_score = xgb_f1
        model_name = "XGBoost"

    print(f"Melhor modelo atual: {model_name} com F1-score: {current_f1_score}")

    # Carregar modelo existente (primeiro do S3, depois local) para comparação
    existing_model = None
    existing_f1_score = -1.0 # Inicializa com um valor baixo

    # Tenta carregar do S3 se habilitado
    if USE_S3:
        print("Tentando carregar modelo existente do S3...")
        s3_local_temp_path = local_model_path + ".s3_temp"
        s3_existing_model = load_model_from_s3(S3_BUCKET_NAME, s3_model_key, s3_local_temp_path)
        if s3_existing_model:
            try:
                s3_existing_predictions = s3_existing_model.predict(X_val)
                existing_f1_score = f1_score(y_val, s3_existing_predictions)
                existing_model = s3_existing_model
                print(f"F1-score do modelo existente no S3: {existing_f1_score}")
            except Exception as e:
                print(f"Erro ao avaliar modelo do S3: {e}")
                existing_model = None  # Invalida o modelo se não puder ser avaliado

    # Se não carregou do S3 ou se o do S3 não pôde ser avaliado, tenta carregar localmente
    if not existing_model and os.path.exists(local_model_path):
        print("Tentando carregar modelo existente localmente...")
        try:
            local_existing_model = joblib.load(local_model_path)
            local_existing_predictions = local_existing_model.predict(X_val)
            local_existing_f1_score = f1_score(y_val, local_existing_predictions)
            if local_existing_f1_score > existing_f1_score: # Prioriza o melhor entre S3 e local
                existing_f1_score = local_existing_f1_score
                existing_model = local_existing_model
            print(f"F1-score do modelo existente local: {local_existing_f1_score}")
        except Exception as e:
            print(f"Erro ao carregar ou comparar modelo existente local: {e}")

    # Lógica de salvamento condicional
    if current_f1_score > existing_f1_score:
        print("Novo modelo é melhor. Salvando localmente" + (" e no S3..." if USE_S3 else "..."))
        model_output_dir = os.path.dirname(local_model_path)
        os.makedirs(model_output_dir, exist_ok=True)
        joblib.dump(best_model, local_model_path)
        print(f"Novo modelo salvo localmente em: {local_model_path}")
        if USE_S3:
            save_model_to_s3(best_model, S3_BUCKET_NAME, s3_model_key, local_model_path)
    else:
        print("Modelo existente é igual ou melhor. Não salvando o novo modelo.")

if __name__ == "__main__":
    output_model_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "trained_model.joblib")
    s3_model_key = S3_MODEL_PREFIX + "trained_model.joblib"

    if not USE_S3:
        print("\u26A0\ufe0f Executando em modo local. Salvamento em S3 desativado.")

    # Carregar dados históricos
    historical_df = load_historical_data(HISTORICAL_DATA_PATH)

    if historical_df.empty:
        print("Nenhum dado histórico disponível para treinamento. Por favor, adicione dados via dashboard ou ETL.")
    else:
        train_model(historical_df, output_model_file, s3_model_key)


