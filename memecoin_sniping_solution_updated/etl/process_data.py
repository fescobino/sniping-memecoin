import pandas as pd
import os
import numpy as np

def process_data(input_path, output_path):
    """
    Extrai dados brutos, transforma e normaliza.
    """
    print(f"Processando dados de: {input_path}")
    df = pd.read_csv(input_path)

    # Exemplo de transformação: criar uma nova feature
    df["new_feature"] = df["feature1"] * df["feature2"]

    # Adicionando as novas features com valores de exemplo/placeholder
    df["token_age_hours"] = np.random.uniform(1, 720, len(df)) # 1 hora a 30 dias
    df["snif_score"] = np.random.randint(0, 101, len(df)) # 0 a 100
    df["whale_buy_activity"] = np.random.uniform(0, 1, len(df))
    df["whale_sell_activity"] = np.random.uniform(0, 1, len(df))
    df["new_whale_entries"] = np.random.randint(0, 10, len(df))
    df["total_supply"] = np.random.uniform(1e9, 1e12, len(df))
    df["circulating_supply"] = df["total_supply"] * np.random.uniform(0.5, 1, len(df))
    df["liquidity_usd"] = np.random.uniform(1000, 1000000, len(df))
    df["volume_24h_usd"] = np.random.uniform(10000, 10000000, len(df))

    # Features existentes do test_endpoint do model_deployer.py
    df["amount_usd"] = np.random.uniform(10, 1000, len(df))
    df["price_per_token"] = np.random.uniform(0.000001, 0.1, len(df))
    df["slippage"] = np.random.uniform(0.01, 0.1, len(df))
    df["gas_price_avg"] = np.random.uniform(10, 100, len(df))
    df["gas_price_std"] = np.random.uniform(1, 10, len(df))
    df["rpc_latency"] = np.random.uniform(50, 200, len(df))
    df["security_score"] = np.random.uniform(0.1, 0.9, len(df))
    df["failure_rate"] = np.random.uniform(0.01, 0.2, len(df))
    df["social_sentiment_score"] = np.random.uniform(-1, 1, len(df))
    df["hour"] = np.random.randint(0, 24, len(df))
    df["day_of_week"] = np.random.randint(0, 7, len(df))
    df["is_weekend"] = df["day_of_week"].apply(lambda x: 1 if x >= 5 else 0)
    df["liquidity_locked"] = np.random.randint(0, 2, len(df))
    df["price_change_pct"] = np.random.uniform(-0.1, 0.2, len(df))
    df["volume_ma_5"] = np.random.uniform(100, 10000, len(df))
    df["slippage_amount_interaction"] = df["slippage"] * df["amount_usd"]
    df["security_sentiment_interaction"] = df["security_score"] * df["social_sentiment_score"]
    df["prev_price"] = np.random.uniform(0.000001, 0.1, len(df))
    df["prev_volume"] = np.random.uniform(1000, 100000, len(df))
    df["price_volatility"] = np.random.uniform(0.01, 0.1, len(df))

    # Reordenar colunas para corresponder à ordem esperada pelo modelo (se houver)
    # Isso é crucial para a inferência do SageMaker
    expected_features = [
        'amount_usd', 'price_per_token', 'slippage', 'gas_price_avg', 'gas_price_std',
        'rpc_latency', 'security_score', 'failure_rate', 'social_sentiment_score',
        'hour', 'day_of_week', 'is_weekend', 'liquidity_locked', 'price_change_pct',
        'volume_ma_5', 'slippage_amount_interaction', 'security_sentiment_interaction',
        'prev_price', 'prev_volume', 'price_volatility', 'token_age_hours', 'snif_score',
        'whale_buy_activity', 'whale_sell_activity', 'new_whale_entries', 'total_supply',
        'circulating_supply', 'liquidity_usd', 'volume_24h_usd'
    ]
    
    # Garantir que todas as colunas esperadas estejam presentes, preenchendo com 0 se ausentes
    for col in expected_features:
        if col not in df.columns:
            df[col] = 0

    # Selecionar e reordenar as colunas
    df = df[expected_features + ['target']]

    # Salvar dados processados em formato parquet
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    df.to_parquet(output_path, index=False)
    print(f"Dados processados salvos em: {output_path}")

if __name__ == "__main__":
    # Exemplo de uso local
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(current_dir, '..', 'optimizer', 'raw', 'sample_data.csv')
    output_file = os.path.join(current_dir, '..', 'optimizer', 'processed', 'sample_features.parquet')
    
    # Criar um arquivo CSV de exemplo se não existir
    if not os.path.exists(input_file):
        print(f"Criando arquivo de exemplo: {input_file}")
        sample_df = pd.DataFrame({
            'feature1': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            'feature2': [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
            'target': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
        })
        os.makedirs(os.path.dirname(input_file), exist_ok=True)
        sample_df.to_csv(input_file, index=False)

    process_data(input_file, output_file)






