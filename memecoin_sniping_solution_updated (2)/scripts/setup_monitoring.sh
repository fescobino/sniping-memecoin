#!/bin/bash

# Script para configurar monitoramento e alertas
# Uso: ./scripts/setup_monitoring.sh [email] [environment]

set -e

ALERT_EMAIL=${1:-"admin@example.com"}
ENVIRONMENT=${2:-"dev"}
AWS_REGION=${AWS_REGION:-"us-east-1"}

echo "📊 Configurando monitoramento..."
echo "📧 Email para alertas: $ALERT_EMAIL"
echo "🌍 Environment: $ENVIRONMENT"

# Deploy do stack de monitoramento
aws cloudformation deploy \
    --template-file iac/cloudformation/monitoring.yaml \
    --stack-name "MemecoinSniping-Monitoring-$ENVIRONMENT" \
    --capabilities CAPABILITY_IAM \
    --region "$AWS_REGION" \
    --parameter-overrides AlertEmail="$ALERT_EMAIL"

echo "✅ Monitoramento configurado com sucesso!"

# Obter URL do dashboard
DASHBOARD_URL=$(aws cloudformation describe-stacks \
    --stack-name "MemecoinSniping-Monitoring-$ENVIRONMENT" \
    --query 'Stacks[0].Outputs[?OutputKey==`DashboardURL`].OutputValue' \
    --output text \
    --region "$AWS_REGION")

echo ""
echo "📊 Dashboard URL: $DASHBOARD_URL"
echo ""
echo "🔔 Alertas configurados para:"
echo "   - Erros nos Lambda functions"
echo "   - Drawdown > 15%"
echo "   - Filas SQS com muitas mensagens"
echo ""
echo "📧 Confirme a inscrição no email: $ALERT_EMAIL"

