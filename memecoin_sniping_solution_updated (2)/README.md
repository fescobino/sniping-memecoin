# 🚀 Solução de Sniping de Memecoins - Blockchain Solana

Uma solução completa, cloud-native e autônoma para sniping de memecoins na blockchain Solana, composta por quatro agentes inteligentes que trabalham em conjunto para identificar, analisar, negociar e otimizar operações de trading automaticamente, agora com um robusto pipeline de MLOps.

## 🎯 Visão Geral

Esta solução implementa um sistema de trading automatizado que monitora continuamente a blockchain Solana em busca de novos tokens (memecoins), analisa sua qualidade e potencial usando machine learning e análise de sentimento, executa trades automaticamente com gerenciamento de risco, e otimiza continuamente os parâmetros usando otimização bayesiana e A/B testing. A integração MLOps garante que os modelos de ML sejam continuamente treinados, implantados e monitorados para manter a alta performance.

### 🏗️ Arquitetura Geral

```mermaid
graph TD
    A[Dados Brutos] --> B{Agente Executor};;
    B --> C[Dados de Trade Brutos (S3)];;
    C --> D{Agente ETL Processor};;
    D --> E[Dados Processados (S3)];;
    E --> F{Agente Model Trainer};;
    F --> G[Modelo Treinado (S3)];;
    G --> H{Agente Model Deployer};;
    H --> I[Endpoint de Inferência (SageMaker)];;
    I --> J{Agente Analyzer};;
    I --> K{Agente Optimizer};;
    J --> L[Decisão de Trade];;
    K --> L;
    L --> B;
    I --> M[Monitoramento de Modelo (CloudWatch)];;
    M --> F;
    M --> N[Alertas (SNS/Telegram)];;
```

### 🤖 Agentes

#### 1. **Discoverer** - Descoberta de Novos Tokens
- **Função**: Monitora a blockchain Solana via Helius API para detectar novos tokens, com foco em migrações da Pump.Fun para PumpSwap.
- **Tecnologias**: Lambda, SQS, Helius Webhooks
- **Saída**: Envia dados de novos tokens para o Analyzer

#### 2. **Analyzer** - Análise de Qualidade
- **Função**: Analisa tokens usando ML, sentiment analysis e dados on-chain, utilizando o modelo implantado no SageMaker. Inclui lógica aprimorada para Pump.Fun/PumpSwap.
- **Tecnologias**: Lambda, Twitter API, Amazon SageMaker (inferência)
- **Saída**: Score de qualidade (0-100) e recomendação de trade

#### 3. **Trader** - Execução de Trades
- **Função**: Executa trades automaticamente com gerenciamento de risco. Inclui melhorias na gestão de slippage e retries.
- **Tecnologias**: Lambda, Solana Web3, DynamoDB
- **Modos**: Paper trading (simulação com preços reais) e Live trading

#### 4. **Optimizer** - Otimização Contínua
- **Função**: Otimiza parâmetros usando dados históricos e A/B testing, utilizando o modelo implantado no SageMaker. Agora com validação de modelo antes da promoção.
- **Tecnologias**: Lambda, Optuna, EventBridge, Amazon SageMaker (inferência)
- **Saída**: Configurações otimizadas para melhor performance

### 🚀 Componentes MLOps Adicionais

#### 5. **Executor** - Coleta de Dados para ML
- **Função**: Coleta dados detalhados de trades e eventos para o pipeline de Machine Learning.
- **Tecnologias**: Lambda, S3
- **Saída**: Dados brutos de trade armazenados no S3.

#### 6. **ETL Processor** - Processamento de Dados
- **Função**: Processa e transforma dados brutos em features prontas para o treinamento de modelos de ML. Otimizado para dados Parquet.
- **Tecnologias**: Lambda, S3, Pandas, PyArrow
- **Saída**: Features processadas armazenadas no S3.

#### 7. **Model Trainer** - Treinamento de Modelos em Lote
- **Função**: Treina múltiplos algoritmos de ML, aplica validação cruzada, otimização de hiperparâmetros e seleciona o melhor modelo. Inclui validação e promoção condicional de modelos.
- **Tecnologias**: Lambda, S3, Scikit-learn, XGBoost, Joblib
- **Saída**: Modelo treinado salvo no S3.

#### 8. **Model Deployer** - Deploy de Modelo e Endpoint de Inferência
- **Função**: Realiza o deploy automático do melhor modelo para o Amazon SageMaker, criando endpoints de inferência em tempo real. Inclui versionamento de modelos.
- **Tecnologias**: Lambda, Amazon SageMaker SDK
- **Saída**: Endpoint de inferência do SageMaker.

## 📊 Dashboard e Monitoramento

### Dashboard Web
- **Interface**: React/HTML5 responsiva com tema dark
- **Métricas**: Performance em tempo real, P&L, win rate, drawdown
- **Visualizações**: Gráficos interativos de performance cumulativa
- **Modos**: Comparação entre paper trading e live trading
- **Nova Funcionalidade**: Upload de dados históricos para treinamento via interface.

### Sistema de Alertas
- **Telegram Bot**: Notificações em tempo real de trades e alertas
- **CloudWatch**: Monitoramento de infraestrutura, métricas customizadas e métricas de modelos de ML (drift, performance).
- **SNS**: Alertas por email para eventos críticos

## 🛠️ Tecnologias Utilizadas

### Backend
- **Python 3.9+**: Linguagem principal
- **Flask**: API REST para dashboard
- **AWS Lambda**: Execução serverless dos agentes
- **boto3**: SDK da AWS

### Machine Learning & Análise
- **scikit-learn**: Modelos de ML para análise de qualidade e treinamento
- **Optuna**: Otimização bayesiana de hiperparâmetros
- **pandas/numpy**: Processamento de dados
- **XGBoost**: Algoritmo de boosting para treinamento de modelos
- **PyArrow**: Otimização de I/O para dados Parquet
- **Joblib**: Serialização de modelos Python
- **Amazon SageMaker**: Plataforma para treinamento e deploy de modelos de ML

### Blockchain & APIs
- **Solana Web3**: Interação com blockchain Solana
- **Helius API**: Monitoramento de novos tokens
- **Twitter API**: Análise de sentimento
- **Telegram API**: Sistema de notificações

### Infraestrutura AWS
- **Lambda**: Execução dos agentes
- **SQS**: Filas de mensagens entre agentes (com DLQs)
- **DynamoDB**: Armazenamento de dados de trading (com GSIs e PITR)
- **S3**: Configurações, backups, dados brutos e processados para ML, modelos treinados
- **Secrets Manager**: Gerenciamento seguro de chaves (com tags)
- **EventBridge**: Agendamento do Optimizer e Model Trainer
- **CloudWatch**: Monitoramento e alertas (incluindo métricas de MLOps)
- **SNS**: Notificações
- **Amazon SageMaker**: Para treinamento e deploy de modelos de ML

### DevOps & CI/CD
- **GitHub Actions**: Pipeline de CI/CD automatizado (lint, testes, validação de CFN, deploy)
- **CloudFormation**: Infraestrutura como código
- **Docker**: Containerização (opcional)

## 🚀 Quick Start

### Pré-requisitos
- Conta AWS com permissões adequadas
- Python 3.9+
- AWS CLI configurado
- Chaves de API (Helius, Twitter, Telegram)
- `pip install pyarrow` (necessário para manipulação de dados Parquet)

### 1. Clone e Deploy
```bash
git clone <repository-url>
cd memecoin-sniping-solution

# Deploy da infraestrutura (inclui melhorias de IaC)
./scripts/deploy_infrastructure.sh dev

# Configurar secrets (substitua YOUR_... e sua-regiao-aws)
aws secretsmanager put-secret-value \
    --secret-id /memecoin-sniping/helius-api-key \
    --secret-string \'{"apiKey":"YOUR_HELIUS_API_KEY"}\' \
    --region sua-regiao-aws

# ... (configure os outros secrets conforme DEPLOYMENT.md)

# Deploy dos agentes (inclui código otimizado)
./scripts/package_lambda.sh all
```

### 2. Configurar Monitoramento
```bash
./scripts/setup_monitoring.sh your-email@example.com dev
```

### 3. Testar Dashboard
```bash
cd dashboard
source venv/bin/activate
pip install -r requirements.txt # Instalar dependências do dashboard
python src/main.py
# Acesse: http://localhost:5000
```

### 4. Injeção de Dados Históricos (Opcional)

Para adicionar dados históricos para treinamento via dashboard:

1.  Acesse o dashboard (`http://localhost:5000` ou sua URL de deploy na AWS).
2.  Navegue até a seção de upload de dados históricos (a interface exata dependerá da implementação final).
3.  Faça o upload de um arquivo `.parquet` contendo seus dados históricos (features e `target`).
4.  Execute o script `train.py` (localmente ou via Lambda agendado) para que ele utilize os dados recém-enviados.

## 📁 Estrutura do Projeto

```
memecoin-sniping-solution/
├── src/                          # Código dos agentes
│   ├── discoverer/              # Agente Discoverer
│   ├── analyzer/                # Agente Analyzer
│   ├── trader/                  # Agente Trader
│   ├── optimizer/               # Agente Optimizer
│   ├── executor/                # Agente Executor (MLOps)
│   ├── etl_processor/           # Agente ETL Processor (MLOps)
│   ├── model_trainer/           # Agente Model Trainer (MLOps)
│   └── model_deployer/          # Agente Model Deployer (MLOps)
├── iac/                         # Infraestrutura como código
│   └── cloudformation/          # Templates CloudFormation (atualizados)
├── dashboard/                   # Dashboard web Flask (atualizado)
│   └── src/
│       ├── routes/              # APIs REST
│       └── static/              # Frontend
├── scripts/                     # Scripts de deploy e utilitários
├── .github/workflows/           # CI/CD GitHub Actions
├── etl/                         # Scripts ETL locais
├── notebooks/                   # Notebooks de exemplo (ETL, Treinamento)
├── optimizer/                   # Dados para otimização e ML
│   ├── raw/                     # Dados brutos
│   └── processed/               # Dados processados
├── models/                      # Modelos treinados localmente
├── docs/                        # Documentação adicional (MLOps, diagramas, etc.)
├── train.py                     # Script de treinamento local (atualizado)
├── requirements.txt             # Dependências do projeto
├── DEPLOYMENT.md               # Guia de deploy detalhado (atualizado)
├── USER_GUIDE.md               # Guia do usuário (atualizado)
├── COMPREHENSIVE_GUIDE.md      # Guia abrangente (atualizado)
└── README.md                   # Este arquivo (atualizado)
```

## 🔧 Configuração

### Modo Paper Trading (Padrão)
O sistema inicia em modo simulação por segurança:
```json
{
  "trader": {
    "is_dry_run": true,
    "initial_capital": 1000
  }
}
```

### Ativando Live Trading
```bash
# Atualizar configuração no S3 (consulte DEPLOYMENT.md para detalhes)
aws s3 cp config.json s3://your-config-bucket/agent_config.json
```

### Parâmetros Principais
- **Quality Threshold**: Score mínimo para executar trade (padrão: 60)
- **Position Sizing**: Percentual do capital por trade (5-15%)
- **Stop Loss**: Proteção contra perdas (10-20%)
- **Take Profit**: Objetivo de lucro (20-30%)

## 📈 Métricas e Performance

### Métricas Principais
- **Win Rate**: Percentual de trades lucrativos
- **P&L Total**: Lucro/prejuízo acumulado
- **Sharpe Ratio**: Retorno ajustado ao risco
- **Max Drawdown**: Maior perda consecutiva
- **Trade Frequency**: Número de trades por período

### Benchmarks Esperados
- **Win Rate**: 55-70% (dependendo do mercado)
- **Sharpe Ratio**: > 1.5 (objetivo)
- **Max Drawdown**: < 15% (limite de segurança)

## 🔐 Segurança

### Práticas Implementadas
- **Secrets Manager**: Todas as chaves são armazenadas de forma segura
- **IAM Roles**: Permissões mínimas necessárias
- **VPC**: Isolamento de rede (opcional)
- **Encryption**: Dados em trânsito e em repouso
- **Audit Logs**: CloudTrail para auditoria

### Recomendações
- Rotacionar chaves regularmente
- Monitorar tentativas de acesso
- Usar MFA para contas AWS
- Backup regular das configurações

## 💰 Custos Estimados

### AWS (mensal)
- **Lambda**: $5-20 (dependendo do volume)
- **DynamoDB**: $2-10 (dados de trading)
- **SQS**: $1-5 (mensagens)
- **S3**: $1-3 (configurações)
- **CloudWatch**: $2-5 (logs e métricas)
- **Amazon SageMaker**: Variável, dependendo do uso (treinamento e inferência)

**Total**: $10-60+/mês (dependendo do volume de trading e uso de ML)

### APIs Externas
- **Helius**: $0-50/mês (dependendo do plano)
- **Twitter API**: Gratuito (uso básico)
- **Telegram**: Gratuito

## 🚨 Disclaimers e Riscos

### ⚠️ IMPORTANTE
- **Trading de criptomoedas envolve riscos significativos**
- **Memecoins são especialmente voláteis e arriscados**
- **Use apenas capital que pode perder**
- **Teste extensivamente em modo paper antes do live**
- **Monitore constantemente a performance**

### Limitações
- Dependente da qualidade dos dados da Helius API
- Análise de sentimento pode ter falsos positivos
- Mercado de memecoins é altamente especulativo
- Slippage pode afetar a execução de trades

## 🤝 Contribuição

### Como Contribuir
1. Fork o repositório
2. Crie uma branch para sua feature
3. Implemente testes para novas funcionalidades
4. Submeta um Pull Request

### Áreas de Melhoria
- Novos indicadores técnicos
- Melhor análise de sentimento
- Integração com mais exchanges
- Otimizações de performance
- Novos tipos de alertas

## 📚 Documentação Adicional

- [Guia de Deploy](DEPLOYMENT.md) - Instruções detalhadas de instalação
- [Guia do Usuário](USER_GUIDE.md) - Como usar e monitorar a solução
- [Guia Abrangente](COMPREHENSIVE_GUIDE.md) - Detalhes de deploy e operação
- [Análise Técnica](analysis.md) - Análise detalhada da solução
- [API Documentation](dashboard/API.md) - Documentação das APIs
- [Guia de Uso do Modo Paper (ETL e Treinamento Local)](docs/paper_mode_guide.md) - Detalhes sobre o pipeline de ML local.
- [Diagrama do Pipeline MLOps](docs/mlops_pipeline.mmd) - Visualização da arquitetura MLOps.
- [Especificação OpenAPI do Endpoint de Inferência](docs/inference_api_spec.yaml) - Detalhes da API de inferência de modelos.

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique os logs do CloudWatch
2. Consulte a documentação da AWS
3. Revise as configurações dos secrets
4. Abra uma issue no GitHub

## 📄 Licença

Este projeto é fornecido "como está" para fins educacionais e de demonstração. Use por sua própria conta e risco.

---

**Desenvolvido por Manus AI** 🤖

*Última atualização: Julho 2025*

REV 002


