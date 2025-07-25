# 📁 Estrutura do Projeto - Solução de Sniping de Memecoins

## Visão Geral da Estrutura

```
memecoin-sniping-solution/
├── 📄 README.md                           # Documentação principal
├── 📄 USER_GUIDE.md                       # Guia do usuário
├── 📄 TECHNICAL_DOCUMENTATION.md          # Documentação técnica
├── 📄 DEPLOYMENT.md                       # Guia de deploy
├── 📄 analysis.md                         # Análise detalhada da solução
├── 📄 todo.md                             # Lista de tarefas (desenvolvimento)
│
├── 🤖 src/                                # Código dos agentes
│   ├── discoverer/                        # Agente Discoverer
│   │   ├── discoverer.py                  # Código principal
│   │   ├── requirements.txt               # Dependências
│   │   └── test_discoverer.py             # Testes
│   ├── analyzer/                          # Agente Analyzer
│   │   ├── analyzer.py                    # Código principal
│   │   ├── requirements.txt               # Dependências
│   │   └── test_analyzer.py               # Testes
│   ├── trader/                            # Agente Trader
│   │   ├── trader.py                      # Código principal
│   │   ├── requirements.txt               # Dependências
│   │   └── test_trader.py                 # Testes
│   └── optimizer/                         # Agente Optimizer
│       ├── optimizer.py                   # Código principal
│       ├── requirements.txt               # Dependências
│       └── test_optimizer.py              # Testes
│
├── 🏗️ iac/                               # Infraestrutura como Código
│   ├── cloudformation/                    # Templates CloudFormation
│   │   ├── sqs.yaml                       # Filas SQS
│   │   ├── dynamodb.yaml                  # Tabelas DynamoDB
│   │   ├── lambda.yaml                    # Funções Lambda
│   │   ├── s3.yaml                        # Buckets S3
│   │   ├── secrets_manager.yaml           # Secrets Manager
│   │   ├── sns.yaml                       # Tópicos SNS
│   │   ├── eventbridge.yaml               # EventBridge Rules
│   │   └── monitoring.yaml                # CloudWatch Monitoring
│   └── deploy.sh                          # Script de deploy básico
│
├── 📊 dashboard/                          # Dashboard Web
│   ├── src/                               # Código fonte Flask
│   │   ├── main.py                        # Aplicação principal
│   │   ├── routes/                        # APIs REST
│   │   │   ├── user.py                    # Rotas de usuário (template)
│   │   │   ├── trading.py                 # APIs de trading
│   │   │   └── notifications.py           # APIs de notificações
│   │   ├── models/                        # Modelos de dados
│   │   │   └── user.py                    # Modelo de usuário (template)
│   │   ├── static/                        # Frontend
│   │   │   └── index.html                 # Interface principal
│   │   └── database/                      # Banco de dados local
│   ├── requirements.txt                   # Dependências Python
│   └── test_dashboard.py                  # Testes do dashboard
│
├── 🔧 scripts/                           # Scripts de automação
│   ├── deploy_infrastructure.sh           # Deploy da infraestrutura
│   ├── package_lambda.sh                 # Empacotamento dos Lambdas
│   └── setup_monitoring.sh               # Configuração de monitoramento
│
└── 🚀 .github/workflows/                 # CI/CD GitHub Actions
    └── deploy.yml                        # Pipeline de deploy
```

## Detalhamento dos Componentes

### 📄 Documentação

#### README.md
- **Propósito**: Visão geral do projeto e quick start
- **Audiência**: Desenvolvedores e usuários técnicos
- **Conteúdo**: Arquitetura, tecnologias, instalação básica

#### USER_GUIDE.md
- **Propósito**: Guia completo para usuários finais
- **Audiência**: Usuários não-técnicos
- **Conteúdo**: Configuração, uso, monitoramento, troubleshooting

#### TECHNICAL_DOCUMENTATION.md
- **Propósito**: Documentação técnica detalhada
- **Audiência**: Desenvolvedores e arquitetos
- **Conteúdo**: Especificações, algoritmos, APIs, segurança

#### DEPLOYMENT.md
- **Propósito**: Instruções detalhadas de deploy
- **Audiência**: DevOps e administradores
- **Conteúdo**: Pré-requisitos, configuração AWS, troubleshooting

### 🤖 Agentes (src/)

#### Discoverer
```python
# discoverer.py - Estrutura principal
def lambda_handler(event, context):
    """Handler principal do Lambda"""
    
def process_webhook(webhook_data):
    """Processa webhooks da Helius API"""
    
def periodic_discovery():
    """Descoberta periódica de novos tokens"""
    
def send_to_analyzer(token_data):
    """Envia dados para o Analyzer via SQS"""
```

**Responsabilidades**:
- Receber webhooks da Helius API
- Filtrar novos tokens relevantes
- Enviar dados para análise

#### Analyzer
```python
# analyzer.py - Estrutura principal
def lambda_handler(event, context):
    """Handler principal do Lambda"""
    
def analyze_token(token_data):
    """Análise completa do token"""
    
def calculate_quality_score(metrics):
    """Calcula score de qualidade (0-100)"""
    
def send_to_trader(analysis_result):
    """Envia resultado para o Trader"""
```

**Responsabilidades**:
- Análise on-chain de tokens
- Sentiment analysis
- Cálculo de score de qualidade
- Decisão de trade

#### Trader
```python
# trader.py - Estrutura principal
def lambda_handler(event, context):
    """Handler principal do Lambda"""
    
def execute_trade(token_data, analysis):
    """Executa trade baseado na análise"""
    
def manage_positions():
    """Gerencia posições abertas"""
    
def calculate_trade_parameters(quality_score):
    """Calcula parâmetros de trade"""
```

**Responsabilidades**:
- Execução de trades
- Gerenciamento de risco
- Stop-loss e take-profit
- Monitoramento de posições

#### Optimizer
```python
# optimizer.py - Estrutura principal
def lambda_handler(event, context):
    """Handler principal do Lambda"""
    
def run_bayesian_optimization(historical_data):
    """Otimização bayesiana de parâmetros"""
    
def create_ab_test_config(current_config, optimized_params):
    """Cria configuração para A/B testing"""
    
def save_config_to_s3(config):
    """Salva configuração otimizada"""
```

**Responsabilidades**:
- Análise de performance histórica
- Otimização bayesiana
- A/B testing
- Atualização de configurações

### 🏗️ Infraestrutura (iac/)

#### CloudFormation Templates

**sqs.yaml**
```yaml
# Filas SQS para comunicação entre agentes
Resources:
  DiscovererQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 60
      MessageRetentionPeriod: 1209600
  
  AnalyzerQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 180
      MessageRetentionPeriod: 1209600
```

**dynamodb.yaml**
```yaml
# Tabelas para armazenamento de dados
Resources:
  TraderTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: MemecoinSnipingTraderTable
      BillingMode: PAY_PER_REQUEST
      
  OptimizerTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: MemecoinSnipingOptimizerTable
      BillingMode: PAY_PER_REQUEST
```

**lambda.yaml**
```yaml
# Funções Lambda dos agentes
Resources:
  DiscovererFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: MemecoinSnipingDiscoverer
      Runtime: python3.9
      Handler: discoverer.lambda_handler
      MemorySize: 512
      Timeout: 30
```

### 📊 Dashboard (dashboard/)

#### Backend Flask
```python
# main.py - Aplicação principal
from flask import Flask
from flask_cors import CORS
from src.routes.trading import trading_bp
from src.routes.notifications import notifications_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(trading_bp, url_prefix='/api/trading')
app.register_blueprint(notifications_bp, url_prefix='/api/notifications')
```

#### APIs REST
- **GET /api/trading/metrics**: Métricas de performance
- **GET /api/trading/trades**: Lista de trades
- **GET /api/trading/performance**: Dados para gráficos
- **GET /api/trading/status**: Status do sistema
- **POST /api/notifications/telegram/send**: Enviar notificação

#### Frontend
```html
<!-- index.html - Interface principal -->
<!DOCTYPE html>
<html>
<head>
    <title>Memecoin Sniping Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <!-- Dashboard com métricas, gráficos e tabelas -->
</body>
</html>
```

### 🔧 Scripts de Automação

#### deploy_infrastructure.sh
```bash
#!/bin/bash
# Deploy completo da infraestrutura AWS
deploy_stack() {
    aws cloudformation deploy \
        --template-file "$template_file" \
        --stack-name "$stack_name" \
        --capabilities CAPABILITY_IAM
}
```

#### package_lambda.sh
```bash
#!/bin/bash
# Empacotamento dos Lambda functions
package_agent() {
    cd "src/$agent"
    pip install -r requirements.txt -t .
    zip -r "${agent}.zip" .
    aws s3 cp "${agent}.zip" "s3://$S3_BUCKET/"
}
```

### 🚀 CI/CD (.github/workflows/)

#### deploy.yml
```yaml
name: Deploy Memecoin Sniping Solution

on:
  push:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Test all agents
        run: |
          cd src/discoverer && python test_discoverer.py
          cd src/analyzer && python test_analyzer.py
          # ... outros testes
  
  deploy:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy infrastructure
        run: ./scripts/deploy_infrastructure.sh
```

## Fluxo de Dados

### 1. Descoberta de Tokens
```
Helius API → Webhook → Discoverer Lambda → SQS (DiscovererQueue)
```

### 2. Análise de Qualidade
```
SQS → Analyzer Lambda → ML Analysis → SQS (AnalyzerQueue)
```

### 3. Execução de Trades
```
SQS → Trader Lambda → Solana Blockchain → DynamoDB (TraderTable)
```

### 4. Otimização
```
EventBridge → Optimizer Lambda → Bayesian Optimization → S3 (Config)
```

### 5. Monitoramento
```
DynamoDB → Dashboard API → Frontend → Usuário
CloudWatch → SNS → Email/Telegram
```

## Configuração e Personalização

### Variáveis de Ambiente
```bash
# Lambda Functions
HELIUS_API_KEY_SECRET_NAME=/memecoin-sniping/helius-api-key
SOLANA_WALLET_SECRET_NAME=/memecoin-sniping/solana-wallet-private-key
TWITTER_API_SECRET_NAME=/memecoin-sniping/twitter-api-secrets
TELEGRAM_API_SECRET_NAME=/memecoin-sniping/telegram-api-secret

# DynamoDB Tables
TRADER_TABLE_NAME=MemecoinSnipingTraderTable
OPTIMIZER_TABLE_NAME=MemecoinSnipingOptimizerTable

# SQS Queues
DISCOVERER_QUEUE_URL=https://sqs.region.amazonaws.com/account/DiscovererQueue
ANALYZER_QUEUE_URL=https://sqs.region.amazonaws.com/account/AnalyzerQueue

# S3 Configuration
CONFIG_BUCKET=memecoin-sniping-config-bucket
CONFIG_KEY=agent_config.json
```

### Arquivo de Configuração (S3)
```json
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
    "max_slippage": 0.02
  },
  "optimizer": {
    "optimization_frequency": "weekly",
    "ab_test_percentage": 0.15,
    "min_trades_for_optimization": 50
  }
}
```

## Dependências e Tecnologias

### Python Packages
```txt
# Core AWS
boto3==1.26.137
botocore==1.29.137

# Web Framework (Dashboard)
flask==3.1.1
flask-cors==6.0.0

# Machine Learning
scikit-learn==1.2.2
optuna==3.2.0
numpy==1.24.3
pandas==2.0.2

# Blockchain
solana==0.30.2

# APIs
requests==2.31.0
tweepy==4.14.0

# Utilities
joblib==1.2.0
```

### AWS Services
- **Lambda**: Execução serverless
- **SQS**: Filas de mensagens
- **DynamoDB**: Banco NoSQL
- **S3**: Armazenamento de objetos
- **Secrets Manager**: Gerenciamento de secrets
- **SNS**: Notificações
- **EventBridge**: Agendamento
- **CloudWatch**: Monitoramento
- **IAM**: Controle de acesso

### APIs Externas
- **Helius API**: Monitoramento Solana
- **Twitter API v2**: Análise de sentimento
- **Telegram Bot API**: Notificações
- **Solana RPC**: Interação blockchain

## Segurança e Compliance

### Secrets Management
- Todas as chaves armazenadas no AWS Secrets Manager
- Rotação automática configurada
- Acesso via IAM roles com permissões mínimas

### Encryption
- **Em trânsito**: HTTPS/TLS 1.2+
- **Em repouso**: AES-256 (DynamoDB, S3)
- **Secrets**: AWS KMS encryption

### Audit Trail
- CloudTrail para todas as operações AWS
- Logs detalhados no CloudWatch
- Métricas customizadas para monitoramento

## Performance e Escalabilidade

### Otimizações
- **Lambda**: Provisioned concurrency para funções críticas
- **DynamoDB**: Pay-per-request para auto-scaling
- **SQS**: Long polling para reduzir latência
- **Connection pooling**: Reutilização de conexões

### Limites e Quotas
- **Lambda**: 1000 execuções concorrentes
- **DynamoDB**: 40,000 RCU/WCU por tabela
- **SQS**: Unlimited throughput
- **API Calls**: Rate limiting implementado

## Monitoramento e Alertas

### Métricas Principais
- **Lambda**: Invocations, Errors, Duration, Throttles
- **DynamoDB**: Read/Write capacity, Throttles
- **SQS**: Messages sent/received, Queue depth
- **Custom**: Trading performance, P&L, Win rate

### Alertas Configurados
- **High Error Rate**: >5% em 5 minutos
- **High Latency**: >10 segundos média
- **Queue Backlog**: >100 mensagens
- **High Drawdown**: >15%

---

Esta estrutura foi projetada para ser modular, escalável e fácil de manter, seguindo as melhores práticas de arquitetura serverless e DevOps.




REV 001

