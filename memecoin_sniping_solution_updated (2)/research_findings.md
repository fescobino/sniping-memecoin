# Achados da Pesquisa: Pump.Fun, PumpSwap e Raydium

## Resumo Executivo

A pesquisa revelou mudanças significativas no ecossistema de memecoins da Solana que impactam diretamente a estratégia de sniping proposta. O lançamento do PumpSwap em março de 2025 alterou fundamentalmente o fluxo de migração de tokens da Pump.Fun, criando novas oportunidades e desafios para a captura de tokens "migrados".

## Principais Descobertas

### 1. Mudança no Paradigma de Migração

**Situação Anterior (até março 2025):**
- Tokens da Pump.Fun migravam automaticamente para Raydium após atingir $69,000 de market cap
- Taxa de migração: 6 SOL
- Processo automático e previsível

**Situação Atual (pós-março 2025):**
- Pump.Fun lançou PumpSwap, seu próprio DEX
- Tokens agora migram para PumpSwap por padrão
- Taxa de migração: 0 SOL (gratuita)
- Raydium ainda recebe alguns tokens, mas não é mais o destino principal

### 2. APIs Disponíveis

**Pump.Fun:**
- Moralis API: Suporte completo para tokens graduados
- Bitquery API: Dados em tempo real de bonding curve e graduação
- Helius API: Webhooks para eventos de token

**PumpSwap:**
- Bitquery API: Dados de liquidez e trades em tempo real
- Shyft API: Pools AMM e dados de liquidez
- SDKs Python disponíveis (pumpswap-sdk, PumpSwapAMM)

**Raydium:**
- API oficial: Trade API e dados de liquidez
- Bitquery API: Pools e trades
- SDK oficial disponível

### 3. Implicações para a Estratégia

A mudança para PumpSwap significa que:
1. A maioria dos tokens "migrados" agora vai para PumpSwap, não Raydium
2. Tokens no PumpSwap podem ter características diferentes dos que vão para Raydium
3. É necessário monitorar ambos os destinos para capturar todas as oportunidades
4. A ausência de taxa de migração pode aumentar o volume de tokens migrados

## Próximos Passos

Com base nestes achados, a estratégia deve ser adaptada para:
1. Priorizar PumpSwap como destino principal de migração
2. Manter monitoramento de Raydium para tokens que ainda migram para lá
3. Implementar lógica para distinguir entre os dois tipos de migração
4. Aproveitar as APIs específicas de cada plataforma para otimizar a detecção




REV 001

