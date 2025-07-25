# 📖 Guia do Usuário - Solução de Sniping de Memecoins

## Bem-vindo! 👋

Este guia irá ajudá-lo a configurar, usar e monitorar sua solução de sniping de memecoins na blockchain Solana, com um foco aprimorado na detecção de tokens migrados da Pump.Fun para a **PumpSwap**. Mesmo sem experiência técnica avançada, você conseguirá colocar o sistema em funcionamento seguindo este passo a passo.

## 🎯 O que Esta Solução Faz

Imagine ter um assistente robótico que:
- 🔍 **Monitora** constantemente a blockchain Solana procurando novos tokens (memecoins), com foco em migrações da Pump.Fun para PumpSwap.
- 🧠 **Analisa** automaticamente a qualidade e potencial de cada token, usando métricas específicas para tokens migrados.
- 💰 **Executa** trades automaticamente quando encontra oportunidades
- 📈 **Otimiza** continuamente sua estratégia para melhor performance
- 📱 **Notifica** você sobre todas as atividades via Telegram

Isso é exatamente o que nossa solução faz, 24/7, sem intervenção manual!

## 🚀 Primeiros Passos

### Pré-requisitos

Antes de começar, você precisará de:

1. **Conta AWS** (Amazon Web Services)
   - Cartão de crédito para verificação
   - Acesso administrativo

2. **Chaves de API** (vamos ajudar você a obter):
   - Helius API (para monitorar Solana)
   - Twitter API (para análise de sentimento)
   - Telegram Bot (para notificações)

3. **Carteira Solana** (para trading):
   - Phantom, Solflare ou similar
   - Chave privada para automação

### ⚠️ Importante: Segurança Primeiro

- **NUNCA** compartilhe suas chaves privadas
- **SEMPRE** teste em modo simulação primeiro
- **USE** apenas capital que pode perder
- **MONITORE** constantemente a performance

## 📋 Configuração Passo a Passo

### Etapa 1: Configurar Conta AWS

1. **Criar Conta AWS**
   - Acesse [aws.amazon.com](https://aws.amazon.com)
   - Clique em "Criar conta AWS"
   - Siga o processo de verificação

2. **Configurar AWS CLI**
   ```bash
   # Instalar AWS CLI
   pip install awscli
   
   # Configurar credenciais
   aws configure
   ```
   
   Você precisará de:
   - Access Key ID
   - Secret Access Key
   - Região (recomendado: us-east-1)

### Etapa 2: Obter Chaves de API

#### Helius API (Essencial)
1. Acesse [helius.xyz](https://helius.xyz)
2. Crie uma conta gratuita
3. Gere uma API key
4. **Guarde** a chave com segurança

#### Twitter API (Opcional, mas recomendado)
1. Acesse [developer.twitter.com](https://developer.twitter.com)
2. Solicite acesso de desenvolvedor
3. Crie um app e obtenha:
   - Consumer Key
   - Consumer Secret
   - Access Token
   - Access Token Secret

#### Telegram Bot (Para notificações)
1. Abra o Telegram
2. Procure por @BotFather
3. Digite `/newbot` e siga as instruções
4. **Guarde** o token do bot

### Etapa 3: Deploy da Solução

1. **Download do Código**
   ```bash
   git clone <repository-url>
   cd memecoin-sniping-solution
   ```

2. **Deploy Automático**
   ```bash
   # Tornar scripts executáveis
   chmod +x scripts/*.sh
   
   # Deploy da infraestrutura
   ./scripts/deploy_infrastructure.sh dev
   ```

3. **Configurar Secrets**
   ```bash
   # Helius API
   aws secretsmanager put-secret-value \
     --secret-id /memecoin-sniping/helius-api-key \
     --secret-string \'{"apiKey":"SUA_CHAVE_HELIUS"}\' \
     --region sua-regiao-aws
   
   # Carteira Solana
   aws secretsmanager put-secret-value \
     --secret-id /memecoin-sniping/solana-wallet-private-key \
     --secret-string \'{"privateKey":"SUA_CHAVE_PRIVADA"}\' \
     --region sua-regiao-aws
   
   # Twitter (opcional)
   aws secretsmanager put-secret-value \
     --secret-id /memecoin-sniping/twitter-api-secrets \
     --secret-string \'{"consumerKey":"...","consumerSecret":"...","accessToken":"...","accessTokenSecret":"..."}\' \
     --region sua-regiao-aws
   
   # Telegram
   aws secretsmanager put-secret-value \
     --secret-id /memecoin-sniping/telegram-api-secret \
     --secret-string \'{"botToken":"SEU_TOKEN_TELEGRAM"}\' \
     --region sua-regiao-aws
   ```

4. **Configurar Monitoramento**
   ```bash
   ./scripts/setup_monitoring.sh seu-email@exemplo.com dev
   ```

## 🎛️ Configuração e Personalização

### Configurações Principais

O sistema usa um arquivo de configuração JSON que você pode personalizar:

```json
{
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
  }
}
```

### Parâmetros Importantes

#### Quality Score Threshold (60)
- **O que é**: Score mínimo para executar um trade
- **Valores**: 50-90
- **Recomendação**: 
  - Iniciantes: 70+ (mais conservador)
  - Experientes: 60+ (mais agressivo)

#### Position Sizing
- **high_score_position (0.15)**: 15% do capital para tokens de alta qualidade
- **medium_score_position (0.10)**: 10% para qualidade média
- **Recomendação**: Nunca mais que 20% por trade

#### Stop Loss / Take Profit
- **Stop Loss**: Proteção contra perdas (10-20%)
- **Take Profit**: Objetivo de lucro (20-30%)
- **Recomendação**: Sempre manter stop loss ativo

### Modos de Operação

#### 🧪 Paper Trading (Padrão)
- **O que é**: Simulação sem dinheiro real
- **Vantagens**: Sem risco, teste de estratégias
- **Uso**: Sempre comece aqui!

#### 💰 Live Trading
- **O que é**: Trading com dinheiro real
- **Ativação**: Apenas após validar no paper trading
- **Cuidado**: Use apenas capital que pode perder

## 📱 Usando o Dashboard

### Acessando o Dashboard

1. **Deploy Local** (para testes):
   ```bash
   cd dashboard
   source venv/bin/activate
   python src/main.py
   ```
   Acesse: http://localhost:5000

2. **Deploy na AWS** (produção):
   O dashboard será disponibilizado em uma URL pública após o deploy

### Funcionalidades do Dashboard

#### 📊 Métricas Principais
- **Total de Trades**: Número total de operações
- **Win Rate**: Percentual de trades lucrativos
- **P&L Total**: Lucro/prejuízo acumulado
- **P&L Médio**: Resultado médio por trade
- **Max Drawdown**: Maior perda consecutiva

#### 📈 Gráfico de Performance
- Mostra evolução do P&L ao longo do tempo
- Permite comparar paper trading vs live trading
- Atualização em tempo real

#### 📋 Lista de Trades
- Histórico detalhado de todas as operações
- Status: aberto, fechado
- Informações: token, preços, P&L, score

#### ⬆️ Upload de Dados Históricos para Treinamento

O sistema permite que você forneça dados históricos adicionais para o treinamento do modelo, além dos dados coletados automaticamente. Isso é útil para iniciar o treinamento com um conjunto de dados maior ou para complementar os dados existentes.

1.  **Formato do Arquivo**: Os dados históricos devem estar em formato Parquet (`.parquet`). Certifique-se de que o arquivo contenha as mesmas colunas de features esperadas pelo modelo e uma coluna `target` (rótulo).
2.  **Acessar o Dashboard**: Navegue até a URL do seu dashboard (local ou na AWS).
3.  **Navegar para a Seção de Upload**: Procure por uma seção ou botão de "Upload de Dados Históricos" ou similar. (A interface exata dependerá da implementação final do dashboard).
4.  **Fazer o Upload**: Selecione o arquivo `.parquet` com seus dados históricos e faça o upload. O dashboard enviará este arquivo para o local esperado pelo script `train.py` (`optimizer/processed/historical_data.parquet`).
5.  **Executar o Treinamento**: Após o upload, você pode acionar o treinamento do modelo. Se o `train.py` for executado via um Lambda agendado, ele usará os dados mais recentes disponíveis (incluindo os que você acabou de enviar). Se você estiver executando localmente, basta executar o script `train.py`.

#### 🔄 Modos de Visualização
- **Todos os Trades**: Visão completa
- **Live Trading**: Apenas operações reais
- **Paper Trading**: Apenas simulações

## 🔔 Sistema de Notificações

### Configurando Telegram

1. **Adicionar o Bot**
   - Procure seu bot no Telegram
   - Digite `/start` para ativar

2. **Comandos Disponíveis**
   - `/status` - Status do sistema
   - `/metrics` - Métricas rápidas
   - `/help` - Lista de comandos

### Tipos de Alertas

#### 🚀 Novo Trade
```
🚀 Novo Trade Executado

🪙 Token: So111111...
💰 Valor: $100.00
📊 Score: 75/100
💵 Preço: $0.000123
🎯 Take Profit: $0.000160
🛑 Stop Loss: $0.000111
🔄 Modo: Paper

Trade ID: trade_1234567890_So111111
```

#### 🟢 Trade Fechado (Lucro)
```
🟢 Trade Fechado

🪙 Token: So111111...
💰 P&L: $25.50 (25.5%)
📈 Entrada: $0.000123
📉 Saída: $0.000154
🎯 Motivo: Take Profit
🔄 Modo: Paper

Trade ID: trade_1234567890_So111111
```

#### ⚠️ Alertas de Sistema
```
⚠️ Alerta do Sistema

Drawdown atual: 12.5%
💰 P&L total: $-125.00
📊 Win rate: 65.0%

Revisar estratégia recomendado
```

## 📈 Monitoramento e Otimização

### Métricas para Acompanhar

#### 🎯 Performance
- **Win Rate**: Objetivo 55-70%
- **Sharpe Ratio**: Objetivo >1.5
- **Max Drawdown**: Limite 15%

#### 📊 Operacional
- **Frequência de Trades**: 5-20 por dia
- **Tempo Médio de Trade**: 2-8 horas
- **Slippage Médio**: <2%

### Sinais de Alerta

#### 🔴 Problemas Críticos
- Drawdown >15%
- Win rate <40%
- Muitos erros no sistema

#### 🟡 Atenção Necessária
- Drawdown >10%
- Win rate <50%
- Poucos trades executados

#### 🟢 Performance Saudável
- Drawdown <10%
- Win rate >55%
- Sistema funcionando normalmente

### Otimização Automática

O sistema possui um agente **Optimizer** que:
- Analisa performance histórica semanalmente
- Testa novos parâmetros automaticamente
- Implementa melhorias via A/B testing
- Notifica sobre mudanças importantes

## 🛠️ Manutenção e Troubleshooting

### Verificações Diárias

1. **Dashboard**: Verificar métricas e trades
2. **Telegram**: Confirmar recebimento de alertas
3. **AWS Console**: Verificar logs de erro
4. **Saldo**: Confirmar saldo da carteira

### Problemas Comuns

#### ❌ "Nenhum trade sendo executado"
**Possíveis causas**:
- Threshold muito alto
- Problemas com APIs
- Mercado sem oportunidades

**Soluções**:
1. Verificar configuração do threshold
2. Testar APIs manualmente
3. Verificar logs do sistema

#### ❌ "Muitos trades perdedores"
**Possíveis causas**:
- Mercado em baixa
- Parâmetros inadequados
- Problemas de timing

**Soluções**:
1. Aumentar threshold temporariamente
2. Revisar stop loss/take profit
3. Aguardar otimização automática

#### ❌ "Sistema não responde"
**Possíveis causas**:
- Problemas na AWS
- Limites de API atingidos
- Configuração incorreta

**Soluções**:
1. Verificar status da AWS
2. Verificar limites das APIs
3. Reiniciar sistema se necessário

### Logs e Debugging

#### CloudWatch Logs
```bash
# Ver logs do Discoverer
aws logs tail /aws/lambda/MemecoinSnipingDiscoverer --follow

# Ver logs do Trader
aws logs tail /aws/lambda/MemecoinSnipingTrader --follow
```

#### Dashboard de Monitoramento
- Acesse o CloudWatch Dashboard criado automaticamente
- Monitore métricas de sistema e performance
- Configure alertas personalizados

## 💡 Dicas e Melhores Práticas

### Para Iniciantes

1. **Comece Pequeno**
   - Use paper trading por pelo menos 1 semana
   - Comece com capital pequeno no live trading
   - Aumente gradualmente conforme ganha confiança

2. **Monitore Ativamente**
   - Verifique o dashboard diariamente
   - Configure alertas no Telegram
   - Mantenha logs de suas observações

3. **Seja Paciente**
   - Memecoins são voláteis
   - Nem todo dia terá oportunidades
   - Foque na consistência, não em grandes ganhos

### Para Usuários Avançados

1. **Customização**
   - Ajuste parâmetros baseado em backtesting
   - Implemente filtros adicionais
   - Teste diferentes estratégias

2. **Análise Avançada**
   - Exporte dados para análise externa
   - Implemente métricas customizadas
   - Use ferramentas de análise técnica

3. **Otimização**
   - Monitore correlações de mercado
   - Ajuste position sizing dinamicamente
   - Implemente filtros de volatilidade

### Gestão de Risco

#### 🛡️ Regras de Ouro
1. **Nunca** invista mais que pode perder
2. **Sempre** use stop loss
3. **Diversifique** não concentre em um token
4. **Monitore** drawdown constantemente
5. **Pare** se drawdown >15%

#### 📊 Position Sizing
- **Conservador**: 5-10% por trade
- **Moderado**: 10-15% por trade
- **Agressivo**: 15-20% por trade (máximo!)

#### ⏰ Timing
- **Mercado Bull**: Mais agressivo
- **Mercado Bear**: Mais conservador
- **Alta Volatilidade**: Reduzir position size

## 🆘 Suporte e Comunidade

### Recursos de Ajuda

1. **Documentação**
   - README.md - Visão geral
   - TECHNICAL_DOCUMENTATION.md - Detalhes técnicos
   - DEPLOYMENT.md - Guia de instalação
   - ULTIMATE_GUIDE.md - Guia principal com foco na estratégia de tokens migrados.
   - COMPREHENSIVE_GUIDE.md - Guia abrangente com detalhes de deploy e operação.

2. **Logs do Sistema**
   - CloudWatch Logs
   - Dashboard de monitoramento
   - Alertas por email

3. **Comunidade**
   - GitHub Issues para bugs
   - Discussions para dúvidas
   - Discord/Telegram para chat

### Contato

Para suporte técnico:
- 📧 Email: [criar canal de suporte]
- 💬 Discord: [criar servidor]
- 📱 Telegram: [criar grupo]

## 🔄 Atualizações e Melhorias

### Roadmap

#### Próximas Funcionalidades
- [ ] Integração com mais exchanges
- [ ] Análise técnica avançada
- [ ] Mobile app
- [ ] Backtesting histórico
- [ ] Copy trading

#### Melhorias Contínuas
- Otimização de algoritmos
- Novos indicadores
- Interface melhorada
- Performance aprimorada

### Como Contribuir

1. **Feedback**: Relate bugs e sugestões
2. **Testes**: Ajude testando novas funcionalidades
3. **Código**: Contribua com melhorias
4. **Documentação**: Ajude a melhorar guias

---

## 🎉 Parabéns!

You now have a complete memecoin sniping solution up and running! Remember:

- ✅ **Start** with paper trading
- ✅ **Monitor** constantly
- ✅ **Be** patient and disciplined
- ✅ **Learn** from the results
- ✅ **Have fun** (but responsibly!)

**Good luck and happy trading!** 🚀💰

---

*Última atualização: Julho de 2025*
*Versão: 1.0*


