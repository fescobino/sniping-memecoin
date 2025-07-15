#!/bin/bash

# Script para deploy da infraestrutura AWS
# Uso: ./scripts/deploy_infrastructure.sh [environment]

set -e

ENVIRONMENT=${1:-"dev"}
AWS_REGION=${AWS_REGION:-"us-east-1"}
S3_BUCKET_LAMBDA_CODE=${S3_BUCKET_LAMBDA_CODE:-"memecoin-sniping-lambda-code-$(aws sts get-caller-identity --query Account --output text)"}

echo "🚀 Iniciando deploy da infraestrutura..."
echo "🌍 Environment: $ENVIRONMENT"
echo "📍 Region: $AWS_REGION"
echo "📦 S3 Bucket: $S3_BUCKET_LAMBDA_CODE"

# Função para deploy de stack CloudFormation
deploy_stack() {
    local stack_name=$1
    local template_file=$2
    local parameters=$3
    
    echo "📋 Deploying stack: $stack_name"
    
    if [ -n "$parameters" ]; then
        aws cloudformation deploy \
            --template-file "$template_file" \
            --stack-name "$stack_name" \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION" \
            --parameter-overrides $parameters
    else
        aws cloudformation deploy \
            --template-file "$template_file" \
            --stack-name "$stack_name" \
            --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
            --region "$AWS_REGION"
    fi
    
    echo "✅ Stack $stack_name deployed successfully"
}

# Verificar se AWS CLI está configurado
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ Erro: AWS CLI não configurado ou sem permissões"
    exit 1
fi

# Criar bucket S3 para código Lambda se não existir
echo "📦 Verificando bucket S3 para código Lambda..."
if ! aws s3 ls "s3://$S3_BUCKET_LAMBDA_CODE" > /dev/null 2>&1; then
    echo "📦 Criando bucket S3: $S3_BUCKET_LAMBDA_CODE"
    aws s3 mb "s3://$S3_BUCKET_LAMBDA_CODE" --region "$AWS_REGION"
else
    echo "✅ Bucket S3 já existe: $S3_BUCKET_LAMBDA_CODE"
fi

# Deploy das stacks em ordem de dependência
echo "🏗️ Iniciando deploy das stacks..."

# 1. SQS (sem dependências)
deploy_stack "MemecoinSniping-SQS-$ENVIRONMENT" "iac/cloudformation/sqs.yaml"

# 2. DynamoDB (sem dependências)
deploy_stack "MemecoinSniping-DynamoDB-$ENVIRONMENT" "iac/cloudformation/dynamodb.yaml"

# 3. Secrets Manager (sem dependências)
deploy_stack "MemecoinSniping-SecretsManager-$ENVIRONMENT" "iac/cloudformation/secrets_manager.yaml"

# 4. S3 (sem dependências)
deploy_stack "MemecoinSniping-S3-$ENVIRONMENT" "iac/cloudformation/s3.yaml"

# 5. SNS (sem dependências)
deploy_stack "MemecoinSniping-SNS-$ENVIRONMENT" "iac/cloudformation/sns.yaml"

# 6. Lambda (depende de SQS, DynamoDB, Secrets, S3)
deploy_stack "MemecoinSniping-Lambda-$ENVIRONMENT" "iac/cloudformation/lambda.yaml" "S3BucketLambdaCode=$S3_BUCKET_LAMBDA_CODE"

# 7. EventBridge (depende de Lambda)
deploy_stack "MemecoinSniping-EventBridge-$ENVIRONMENT" "iac/cloudformation/eventbridge.yaml"

# Upload configuração padrão
echo "⚙️ Uploading default configuration..."
CONFIG_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name "MemecoinSniping-S3-$ENVIRONMENT" \
    --query 'Stacks[0].Outputs[?OutputKey==`ConfigBucketName`].OutputValue' \
    --output text \
    --region "$AWS_REGION")

if [ -n "$CONFIG_BUCKET" ]; then
    cat > temp_config.json << EOF
{
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
EOF
    
    aws s3 cp temp_config.json "s3://$CONFIG_BUCKET/agent_config.json"
    rm temp_config.json
    echo "✅ Default configuration uploaded to S3"
else
    echo "⚠️ Warning: Could not find config bucket name"
fi

echo ""
echo "🎉 Deploy concluído com sucesso!"
echo "📊 Para monitorar os recursos:"
echo "   aws cloudformation list-stacks --region $AWS_REGION"
echo ""
echo "🔧 Para configurar os secrets:"
echo "   aws secretsmanager put-secret-value --secret-id /memecoin-sniping/helius-api-key --secret-string '{\"apiKey\":\"YOUR_API_KEY\"}'"
echo "   aws secretsmanager put-secret-value --secret-id /memecoin-sniping/solana-wallet-private-key --secret-string '{\"privateKey\":\"YOUR_PRIVATE_KEY\"}'"
echo "   aws secretsmanager put-secret-value --secret-id /memecoin-sniping/twitter-api-secrets --secret-string '{\"consumerKey\":\"...\",\"consumerSecret\":\"...\",\"accessToken\":\"...\",\"accessTokenSecret\":\"...\"}'"
echo "   aws secretsmanager put-secret-value --secret-id /memecoin-sniping/telegram-api-secret --secret-string '{\"botToken\":\"YOUR_BOT_TOKEN\"}'"

