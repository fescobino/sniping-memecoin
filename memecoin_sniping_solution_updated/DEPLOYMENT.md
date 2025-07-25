# Guia de Deploy - Solução de Sniping de Memecoins

Este guia fornece instruções completas para fazer o deploy da solução de sniping de memecoins na AWS, com foco na detecção de tokens migrados da Pump.Fun para a **PumpSwap**.

## Pré-requisitos

### 1. Ferramentas Necessárias
- AWS CLI v2 configurado com credenciais adequadas
- Python 3.9+
- Git
- `pip install pyarrow` (necessário para manipulação de dados Parquet)
- Conta GitHub (para CI/CD, opcional)

### 2. Permissões AWS Necessárias
Sua conta AWS deve ter permissões para:
- CloudFormation (criar/atualizar stacks)
- Lambda (criar/atualizar functions)
- SQS (criar/gerenciar filas)
- DynamoDB (criar/gerenciar tabelas)
- S3 (criar/gerenciar buckets)
- Secrets Manager (criar/gerenciar secrets)
- SNS (criar/gerenciar tópicos)
- EventBridge (criar/gerenciar rules)
- CloudWatch (criar/gerenciar alarms e dashboards)
- IAM (criar/gerenciar roles e policies)
- SageMaker (para treinamento de modelos, se aplicável)

### 3. Configuração Inicial
```bash
# Verificar configuração AWS
aws sts get-caller-identity

# Configurar credenciais AWS (se ainda não o fez)
aws configure

# Definir variáveis de ambiente (substitua 'us-east-1' pela sua região preferida)
export AWS_REGION="us-east-1"
export S3_BUCKET_LAMBDA_CODE="memecoin-sniping-lambda-code-$(aws sts get-caller-identity --query Account --output text)"
```

## Deploy Manual

### 1. Clone do Repositório
```bash
git clone <repository-url>
cd memecoin-sniping-solution
```

### 2. Deploy da Infraestrutura

Os templates CloudFormation foram atualizados para incluir melhorias como GSIs, PITR e tags para DynamoDB; filas dedicadas para o Trader e DLQs para SQS; tags para Secrets Manager; permissões mais granulares, runtimes e variáveis de ambiente para Lambdas; e configurações aprimoradas para SageMaker e EventBridge.

```bash
# Tornar scripts executáveis
chmod +x scripts/*.sh

# Deploy completo da infraestrutura (substitua 'dev' pelo seu ambiente)
./scripts/deploy_infrastructure.sh dev

# Ou deploy individual das stacks (após tornar os scripts executáveis)
# Exemplo: aws cloudformation deploy --template-file iac/cloudformation/sqs.yaml --stack-name MemecoinSniping-SQS-dev --capabilities CAPABILITY_IAM
# Continue com as demais stacks: dynamodb.yaml, lambda.yaml, s3.yaml, secrets_manager.yaml, sns.yaml, eventbridge.yaml, monitoring.yaml, sagemaker.yaml
```

### 3. Empacotamento e Deploy dos Lambda Functions
```bash
# Empacotar todos os agentes (incluindo as atualizações de código)
./scripts/package_lambda.sh all

# Ou empacotar individualmente
./scripts/package_lambda.sh discoverer
./scripts/package_lambda.sh analyzer
./scripts/package_lambda.sh trader
./scripts/package_lambda.sh optimizer
```

### 4. Configuração dos Secrets

Certifique-se de substituir os placeholders (`YOUR_HELIUS_API_KEY`, `YOUR_SOLANA_PRIVATE_KEY_HEX`, etc.) pelos seus valores reais e de usar a `sua-regiao-aws` correta.

```bash
# Helius API Key
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/helius-api-key \
    --secret-string \'{"apiKey":"YOUR_HELIUS_API_KEY"}\' \
    --region sua-regiao-aws

# Solana Wallet Private Key
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/solana-wallet-private-key \
    --secret-string \'{"privateKey":"YOUR_SOLANA_PRIVATE_KEY_HEX"}\' \
    --region sua-regiao-aws

# Twitter API Secrets (Opcional)
aws secretsmanager put-secret-secret-value \
    --secret-id /memecoin-sniping/twitter-api-secrets \
    --secret-string \'{"consumerKey":"YOUR_CONSUMER_KEY","consumerSecret":"YOUR_CONSUMER_SECRET","accessToken":"YOUR_ACCESS_TOKEN","accessTokenSecret":"YOUR_ACCESS_TOKEN_SECRET"}\' \
    --region sua-regiao-aws

# Telegram Bot Token
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/telegram-api-secret \
    --secret-string \'{"botToken":"YOUR_TELEGRAM_BOT_TOKEN"}\' \
    --region sua-regiao-aws
```

### 5. Configuração de Monitoramento
```bash
# Configurar alertas (substitua pelo seu email e ambiente)
./scripts/setup_monitoring.sh your-email@example.com dev
```

## Deploy Automatizado (CI/CD)

### 1. Configuração do GitHub Actions

#### Secrets Necessários no GitHub:
- `AWS_ACCESS_KEY_ID`: Access Key ID da AWS
- `AWS_SECRET_ACCESS_KEY`: Secret Access Key da AWS
- `S3_BUCKET_LAMBDA_CODE`: Nome do bucket S3 para código Lambda

#### Configuração dos Secrets:
1. Vá para Settings > Secrets and variables > Actions no seu repositório GitHub
2. Adicione os secrets listados acima

### 2. Workflow Automático
O deploy automático é acionado quando:
- Push para branch `main` (deploy completo)
- Push para branch `develop` (apenas testes)
- Pull Request para `main` (apenas testes)

### 3. Monitoramento do Deploy
- Acompanhe o progresso na aba "Actions" do GitHub
- Verifique os logs de cada step do workflow
- Confirme o deploy no AWS CloudFormation Console

## Configuração Pós-Deploy

### 1. Verificação dos Recursos
```bash
# Listar stacks criadas
aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE

# Verificar Lambda functions
aws lambda list-functions --query 'Functions[?starts_with(FunctionName, `MemecoinSniping`)].FunctionName'

# Verificar filas SQS
aws sqs list-queues --query 'QueueUrls[?contains(@, `MemecoinSniping`) || contains(@, `Discoverer`) || contains(@, `Analyzer`)]'

# Verificar tabelas DynamoDB (incluindo GSIs)
aws dynamodb list-tables
aws dynamodb describe-table --table-name MemecoinSnipingTraderTable --query 'Table.GlobalSecondaryIndexes'

# Verificar buckets S3
aws s3 ls

# Verificar secrets no Secrets Manager
aws secretsmanager list-secrets --query 'SecretList[?starts_with(Name, `/memecoin-sniping/`)].Name'
```

### 2. Teste dos Agentes
```bash
# Testar Discoverer (simulação)
aws lambda invoke \
    --function-name MemecoinSnipingDiscoverer \
    --payload '{"source":"aws.events"}' \
    response.json

# Verificar logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/MemecoinSniping
```

### 3. Configuração Inicial
```bash
# Verificar configuração padrão no S3
CONFIG_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name MemecoinSniping-S3-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`ConfigBucketName`].OutputValue' \
    --output text)

aws s3 cp "s3://$CONFIG_BUCKET/agent_config.json" - | jq .
```

## Monitoramento e Manutenção

### 1. Dashboard CloudWatch
Acesse o dashboard criado automaticamente:
```bash
# Obter URL do dashboard
aws cloudformation describe-stacks \
    --stack-name MemecoinSniping-Monitoring-dev \
    --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
    --output text
```

### 2. Logs dos Agentes
```bash
# Ver logs do Discoverer
aws logs tail /aws/lambda/MemecoinSnipingDiscoverer --follow

# Ver logs do Analyzer
aws logs tail /aws/lambda/MemecoinSnipingAnalyzer --follow

# Ver logs do Trader
aws logs tail /aws/lambda/MemecoinSnipingTrader --follow

# Ver logs do Optimizer
aws logs tail /aws/lambda/MemecoinSnipingOptimizer --follow
```

### 3. Métricas de Trading
```bash
# Verificar trades no DynamoDB
aws dynamodb scan --table-name MemecoinSnipingTraderTable --max-items 10

# Verificar otimizações
aws dynamodb scan --table-name MemecoinSnipingOptimizerTable --max-items 5
```

## Configurações Avançadas

### 1. Modo Dry-Run vs Live
Por padrão, o sistema inicia em modo dry-run. Para ativar trading real:

```bash
# Atualizar variável de ambiente do Trader
aws lambda update-function-configuration \
    --function-name MemecoinSnipingTrader \
    --environment Variables=\'{
        "IS_DRY_RUN":"false",
        "INITIAL_CAPITAL":"500",
        "ANALYZER_QUEUE_URL":"https://sqs.us-east-1.amazonaws.com/ACCOUNT/AnalyzerQueue",
        "TRADER_TABLE_NAME":"MemecoinSnipingTraderTable",
        "SOLANA_RPC_URL":"https://api.mainnet-beta.solana.com"
    }\'
```

### 2. Ajuste de Parâmetros
Edite o arquivo de configuração no S3:
```bash
# Download da configuração atual
aws s3 cp "s3://$CONFIG_BUCKET/agent_config.json" config.json

# Editar config.json conforme necessário

# Upload da configuração atualizada
aws s3 cp config.json "s3://$CONFIG_BUCKET/agent_config.json"
```

### 3. Scaling e Performance
```bash
# Ajustar concorrência do Lambda
aws lambda put-provisioned-concurrency-config \
    --function-name MemecoinSnipingTrader \
    --provisioned-concurrency-config ProvisionedConcurrencyConfig=10

# Ajustar timeout dos Lambda functions
aws lambda update-function-configuration \
    --function-name MemecoinSnipingAnalyzer \
    --timeout 120
```

## Troubleshooting

### 1. Problemas Comuns

#### Lambda Function Timeout
```bash
# Aumentar timeout
aws lambda update-function-configuration \
    --function-name FUNCTION_NAME \
    --timeout 300
```

#### Permissões Insuficientes
```bash
# Verificar role do Lambda
aws lambda get-function-configuration \
    --function-name FUNCTION_NAME \
    --query 'Role'

# Verificar policies anexadas
aws iam list-attached-role-policies --role-name ROLE_NAME
```

#### Filas SQS com Muitas Mensagens
```bash
# Verificar profundidade da fila
aws sqs get-queue-attributes \
    --queue-url QUEUE_URL \
    --attribute-names ApproximateNumberOfMessages

# Purgar fila se necessário (CUIDADO!)
aws sqs purge-queue --queue-url QUEUE_URL
```

### 2. Logs de Debug
```bash
# Habilitar logs detalhados
aws lambda update-function-configuration \
    --function-name FUNCTION_NAME \
    --environment Variables=\'{"LOG_LEVEL":"DEBUG"}\'
```

### 3. Rollback
```bash
# Rollback de uma stack específica
aws cloudformation cancel-update-stack --stack-name STACK_NAME

# Ou deletar e recriar
aws cloudformation delete-stack --stack-name STACK_NAME
```

## Segurança

### 1. Rotação de Secrets
```bash
# Rotacionar API keys periodicamente
aws secretsmanager update-secret \
    --secret-id /memecoin-sniping/helius-api-key \
    --secret-string \'{"apiKey":"NEW_API_KEY"}\'
```

### 2. Monitoramento de Segurança
- Configure AWS CloudTrail para auditoria
- Use AWS Config para compliance
- Monitore tentativas de acesso não autorizadas

### 3. Backup
```bash
# Backup da configuração
aws s3 sync "s3://$CONFIG_BUCKET" ./config-backup/

# Backup das tabelas DynamoDB
aws dynamodb create-backup \
    --table-name MemecoinSnipingTraderTable \
    --backup-name "trader-backup-$(date +%Y%m%d)"
```

## Custos Estimados

### AWS Free Tier (primeiros 12 meses):
- Lambda: 1M requests/mês grátis
- DynamoDB: 25GB storage grátis
- SQS: 1M requests/mês grátis
- CloudWatch: 10 métricas customizadas grátis

### Custos Mensais Estimados (após Free Tier):
- Lambda: $5-20 (dependendo do volume)
- DynamoDB: $2-10 (dependendo dos dados)
- SQS: $1-5 (dependendo das mensagens)
- S3: $1-3 (configuração e logs)
- CloudWatch: $2-5 (métricas e logs)
- SageMaker: Custos adicionais se utilizado para treinamento ou inferência. (Ex: ml.m5.large por 1h custa aproximadamente $0.11)

**Total Estimado: $10-60/mês** (dependendo do volume de trading e uso do SageMaker)

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs do CloudWatch
2. Consulte a documentação da AWS
3. Revise as configurações dos secrets
4. Verifique as permissões IAM

## Próximos Passos

Após o deploy bem-sucedido:
1. Configure os secrets com suas chaves reais
2. Teste em modo dry-run
3. Monitore as métricas por alguns dias
4. Gradualmente ative o trading real
5. Ajuste parâmetros baseado na performance

REV 002


