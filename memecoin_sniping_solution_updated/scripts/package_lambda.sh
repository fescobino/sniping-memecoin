#!/bin/bash

# Script para empacotar Lambda functions para deploy
# Uso: ./scripts/package_lambda.sh [agent_name] [s3_bucket]

set -e

AGENT_NAME=${1:-"all"}
S3_BUCKET=${2:-$S3_BUCKET_LAMBDA_CODE}

if [ -z "$S3_BUCKET" ]; then
    echo "❌ Erro: S3_BUCKET_LAMBDA_CODE não definido"
    echo "Uso: ./scripts/package_lambda.sh [agent_name] [s3_bucket]"
    exit 1
fi

echo "🚀 Empacotando Lambda functions..."
echo "📦 Bucket S3: $S3_BUCKET"

package_agent() {
    local agent=$1
    echo "📦 Empacotando $agent..."
    
    cd "src/$agent"
    
    # Criar diretório temporário
    mkdir -p temp_package
    
    # Copiar código fonte
    cp *.py temp_package/
    cp requirements.txt temp_package/
    
    cd temp_package
    
    # Instalar dependências
    pip install -r requirements.txt -t . --quiet
    
    # Criar ZIP
    zip -r "../${agent}.zip" . -x "test_*" "__pycache__/*" "*.pyc" > /dev/null
    
    # Limpar diretório temporário
    cd ..
    rm -rf temp_package
    
    # Upload para S3
    aws s3 cp "${agent}.zip" "s3://$S3_BUCKET/${agent}.zip"
    
    echo "✅ $agent empacotado e enviado para S3"
    
    cd ../..
}

if [ "$AGENT_NAME" = "all" ]; then
    echo "📦 Empacotando todos os agentes..."
    package_agent "discoverer"
    package_agent "analyzer"
    package_agent "trader"
    package_agent "optimizer"
    package_agent "executor"
    package_agent "etl_processor"
    package_agent "model_trainer"
    package_agent "model_deployer"
else
    if [ -d "src/$AGENT_NAME" ]; then
        package_agent "$AGENT_NAME"
    else
        echo "❌ Erro: Agente \'$AGENT_NAME\' não encontrado"
        echo "Agentes disponíveis: discoverer, analyzer, trader, optimizer, executor, etl_processor, model_trainer, model_deployer"
        exit 1
    fi
fi

echo "🎉 Empacotamento concluído!"


