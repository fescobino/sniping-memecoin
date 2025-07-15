# Guia de Uso do Modo Paper (ETL e Treinamento Local)

Este guia detalha como executar o pipeline de ETL (Extração, Transformação, Carga) e o treinamento de modelos de Machine Learning localmente, utilizando dados de exemplo. Este processo é fundamental para entender o fluxo de dados e o ciclo de vida do modelo antes de implantar a solução completa na nuvem.

## 1. Pré-requisitos

Certifique-se de ter Python 3.9+ e `pip` instalados em seu sistema. Você também precisará das bibliotecas listadas no `requirements.txt`.

```bash
pip install -r requirements.txt
```

## 2. Estrutura de Dados de Exemplo

Os dados brutos de exemplo são esperados na pasta `optimizer/raw/` e os dados processados serão salvos em `optimizer/processed/`.

- `optimizer/raw/sample_data.csv`: Arquivo CSV com dados brutos de exemplo.
- `optimizer/processed/sample_features.parquet`: Saída do processo ETL em formato Parquet.

Um arquivo `sample_data.csv` já foi criado para você no diretório `optimizer/raw/`.

## 3. Executando o Pipeline ETL Localmente

O script `etl/process_data.py` é responsável por extrair os dados brutos, transformá-los (neste exemplo, criando uma nova feature) e salvá-los em um formato otimizado (Parquet).

Para executar o script ETL:

1.  Navegue até o diretório raiz do projeto no seu terminal:
    ```bash
    cd /home/ubuntu/memecoin_sniping_solution_updated
    ```

Após a execução, você deverá ver uma mensagem indicando que os dados foram processados e salvos em `optimizer/processed/sample_features.parquet`.

## 4. Executando o Treinamento de Modelo Localmente

O script `train.py` lê os dados processados, divide-os em conjuntos de treinamento e teste, treina modelos de Machine Learning (Random Forest e XGBoost neste exemplo) e salva o modelo treinado.

Para executar o script de treinamento:

1.  Certifique-se de que o script ETL foi executado e que `optimizer/processed/sample_features.parquet` existe.
2.  No diretório raiz do projeto, execute o script `train.py`:
    ```bash
    python3 train.py
    ```

Você verá a acurácia dos modelos impressa no terminal e o modelo treinado será salvo em `models/trained_model.joblib`.

## 5. Usando os Notebooks de Exemplo

Para uma exploração interativa do pipeline ETL e de treinamento, você pode usar os notebooks Jupyter fornecidos:

- `notebooks/process_data.ipynb`: Demonstra o processo ETL passo a passo.
- `notebooks/train_model.ipynb`: Demonstra o treinamento do modelo passo a passo.

Para usar os notebooks:

1.  Instale o Jupyter Notebook:
    ```bash
    pip install jupyter
    ```
2.  Navegue até o diretório raiz do projeto:
    ```bash
    cd /home/ubuntu/memecoin_sniping_solution_updated
    ```
3.  Inicie o Jupyter Notebook:
    ```bash
    jupyter notebook
    ```
4.  No navegador, navegue até a pasta `notebooks/` e abra `process_data.ipynb` ou `train_model.ipynb`. Execute as células para ver o pipeline em ação.

Este modo "paper" é essencial para experimentação e validação de novas features ou modelos antes de integrá-los ao pipeline MLOps completo na nuvem.





REV 001

