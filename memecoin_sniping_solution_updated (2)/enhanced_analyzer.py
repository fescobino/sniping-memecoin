import json
import logging
import os
import boto3
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta
from botocore.exceptions import ClientError
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')
secrets_manager = boto3.client('secretsmanager')

# Variáveis de ambiente
TRADER_QUEUE_URL = os.environ.get('TRADER_QUEUE_URL')
ANALYSIS_TABLE = os.environ.get('ANALYSIS_TABLE', 'TokenAnalysisTable')

@dataclass
class MigrationAnalysis:
    """Estrutura para análise específica de tokens migrados."""
    token_address: str
    migration_destination: str
    migration_quality_score: float
    liquidity_stability_score: float
    post_migration_volume_score: float
    smart_money_following_score: float
    migration_timing_score: float
    overall_migration_score: float
    risk_factors: List[str]
    opportunity_factors: List[str]

class EnhancedAnalyzer:
    def __init__(self):
        self.analysis_table = dynamodb.Table(ANALYSIS_TABLE)
        self.session = aiohttp.ClientSession()
        
        # Pesos específicos para análise de tokens migrados
        self.migration_weights = {
            'liquidity_stability': 0.25,
            'post_migration_volume': 0.20,
            'smart_money_following': 0.20,
            'migration_timing': 0.15,
            'migration_destination_quality': 0.20
        }
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_secret(self, secret_name: str) -> Dict:
        """Recupera um segredo do AWS Secrets Manager."""
        try:
            response = secrets_manager.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except ClientError as e:
            logger.error(f"Erro ao recuperar segredo {secret_name}: {e}")
            raise

    async def analyze_liquidity_stability(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa a estabilidade da liquidez pós-migração.
        Tokens migrados devem manter liquidez estável para serem confiáveis.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            token_address = token_data['token_address']
            migration_destination = token_data['migration_destination']
            
            # Obter dados de liquidez histórica pós-migração
            liquidity_data = await self.get_post_migration_liquidity(token_address, migration_destination)
            
            if not liquidity_data:
                risk_factors.append("Dados de liquidez insuficientes")
                return 0.0, risk_factors
            
            # Calcular variação da liquidez
            liquidity_values = [point['liquidity_usd'] for point in liquidity_data]
            
            if len(liquidity_values) < 2:
                risk_factors.append("Histórico de liquidez muito curto")
                return 0.3, risk_factors
            
            # Calcular estabilidade (menor variação = maior estabilidade)
            liquidity_std = np.std(liquidity_values)
            liquidity_mean = np.mean(liquidity_values)
            
            if liquidity_mean == 0:
                risk_factors.append("Liquidez média zero")
                return 0.0, risk_factors
            
            coefficient_of_variation = liquidity_std / liquidity_mean
            
            # Score baseado na estabilidade (menor CV = maior score)
            if coefficient_of_variation < 0.1:
                stability_score = 1.0
                opportunity_factors.append("Liquidez muito estável")
            elif coefficient_of_variation < 0.2:
                stability_score = 0.8
                opportunity_factors.append("Liquidez estável")
            elif coefficient_of_variation < 0.4:
                stability_score = 0.6
            elif coefficient_of_variation < 0.6:
                stability_score = 0.4
                risk_factors.append("Liquidez moderadamente volátil")
            else:
                stability_score = 0.2
                risk_factors.append("Liquidez muito volátil")
            
            # Verificar tendência de crescimento
            if len(liquidity_values) >= 5:
                recent_avg = np.mean(liquidity_values[-3:])
                earlier_avg = np.mean(liquidity_values[:3])
                
                if recent_avg > earlier_avg * 1.1:
                    stability_score *= 1.2  # Bonus para crescimento
                    opportunity_factors.append("Liquidez em crescimento")
                elif recent_avg < earlier_avg * 0.9:
                    stability_score *= 0.8  # Penalidade para declínio
                    risk_factors.append("Liquidez em declínio")
            
            return min(stability_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar estabilidade da liquidez: {e}")
            risk_factors.append("Erro na análise de liquidez")
            return 0.0, risk_factors

    async def analyze_post_migration_volume(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa o volume de trading pós-migração.
        Volume consistente indica interesse sustentado.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            token_address = token_data['token_address']
            migration_destination = token_data['migration_destination']
            
            # Obter dados de volume pós-migração
            volume_data = await self.get_post_migration_volume(token_address, migration_destination)
            
            if not volume_data:
                risk_factors.append("Dados de volume insuficientes")
                return 0.0, risk_factors
            
            # Analisar padrões de volume
            volumes = [point['volume_usd'] for point in volume_data]
            
            if len(volumes) < 3:
                risk_factors.append("Histórico de volume muito curto")
                return 0.3, risk_factors
            
            # Calcular métricas de volume
            avg_volume = np.mean(volumes)
            volume_trend = self.calculate_trend(volumes)
            volume_consistency = 1 - (np.std(volumes) / (avg_volume + 1))
            
            # Score baseado em volume médio (normalizado)
            if avg_volume > 100000:  # $100k+
                volume_score = 1.0
                opportunity_factors.append("Volume muito alto")
            elif avg_volume > 50000:  # $50k+
                volume_score = 0.8
                opportunity_factors.append("Volume alto")
            elif avg_volume > 10000:  # $10k+
                volume_score = 0.6
            elif avg_volume > 1000:  # $1k+
                volume_score = 0.4
            else:
                volume_score = 0.2
                risk_factors.append("Volume muito baixo")
            
            # Ajustar score baseado na tendência
            if volume_trend > 0.1:
                volume_score *= 1.3
                opportunity_factors.append("Volume em crescimento")
            elif volume_trend < -0.1:
                volume_score *= 0.7
                risk_factors.append("Volume em declínio")
            
            # Ajustar score baseado na consistência
            volume_score *= volume_consistency
            
            return min(volume_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar volume pós-migração: {e}")
            risk_factors.append("Erro na análise de volume")
            return 0.0, risk_factors

    async def analyze_smart_money_following(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa se 'smart money' (carteiras conhecidas por bons trades) está seguindo o token.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            token_address = token_data['token_address']
            
            # Obter lista de carteiras smart money
            smart_wallets = await self.get_smart_money_wallets()
            
            # Verificar atividade dessas carteiras no token
            smart_money_activity = await self.check_smart_money_activity(token_address, smart_wallets)
            
            if not smart_money_activity:
                risk_factors.append("Nenhuma atividade de smart money detectada")
                return 0.2, risk_factors
            
            # Calcular score baseado na atividade
            total_smart_wallets = len(smart_wallets)
            active_smart_wallets = len(smart_money_activity)
            smart_money_ratio = active_smart_wallets / total_smart_wallets
            
            # Analisar tipo de atividade (compra vs venda)
            buy_activity = sum(1 for activity in smart_money_activity if activity['type'] == 'buy')
            sell_activity = active_smart_wallets - buy_activity
            
            if buy_activity > sell_activity:
                activity_score = 1.0
                opportunity_factors.append(f"{buy_activity} smart wallets comprando")
            elif buy_activity == sell_activity:
                activity_score = 0.6
            else:
                activity_score = 0.3
                risk_factors.append(f"{sell_activity} smart wallets vendendo")
            
            # Score final baseado na proporção e tipo de atividade
            final_score = smart_money_ratio * activity_score
            
            if final_score > 0.7:
                opportunity_factors.append("Forte interesse de smart money")
            elif final_score < 0.3:
                risk_factors.append("Baixo interesse de smart money")
            
            return final_score, risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar smart money: {e}")
            risk_factors.append("Erro na análise de smart money")
            return 0.0, risk_factors

    async def analyze_migration_timing(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa o timing da migração em relação ao mercado geral.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            migration_timestamp = datetime.fromisoformat(
                token_data.get('migration_timestamp', '').replace('Z', '+00:00')
            )
            
            # Verificar condições de mercado no momento da migração
            market_conditions = await self.get_market_conditions_at_time(migration_timestamp)
            
            # Analisar timing em relação ao mercado
            if market_conditions['sol_price_trend'] > 0.05:  # SOL subindo >5%
                timing_score = 1.0
                opportunity_factors.append("Migração durante alta do SOL")
            elif market_conditions['sol_price_trend'] > 0:
                timing_score = 0.8
                opportunity_factors.append("Migração durante estabilidade do SOL")
            elif market_conditions['sol_price_trend'] > -0.05:
                timing_score = 0.6
            else:
                timing_score = 0.4
                risk_factors.append("Migração durante queda do SOL")
            
            # Verificar volume geral de memecoins
            if market_conditions['memecoin_volume_trend'] > 0.1:
                timing_score *= 1.2
                opportunity_factors.append("Alto volume de memecoins")
            elif market_conditions['memecoin_volume_trend'] < -0.1:
                timing_score *= 0.8
                risk_factors.append("Baixo volume de memecoins")
            
            # Verificar horário da migração (UTC)
            migration_hour = migration_timestamp.hour
            
            # Horários de maior atividade (aproximadamente)
            if 13 <= migration_hour <= 21:  # Horário US/EU ativo
                timing_score *= 1.1
                opportunity_factors.append("Migração em horário de alta atividade")
            elif 2 <= migration_hour <= 6:  # Horário de baixa atividade
                timing_score *= 0.9
                risk_factors.append("Migração em horário de baixa atividade")
            
            return min(timing_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar timing da migração: {e}")
            risk_factors.append("Erro na análise de timing")
            return 0.5, risk_factors

    async def analyze_migration_destination_quality(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa a qualidade do destino da migração (PumpSwap vs Raydium).
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            migration_destination = token_data['migration_destination']
            
            if migration_destination == 'PumpSwap':
                # PumpSwap: mais novo, menos taxas, mas menos liquidez geral
                destination_score = 0.8
                opportunity_factors.append("Migração para PumpSwap (sem taxas)")
                
                # Verificar se é um dos primeiros tokens no PumpSwap
                pumpswap_token_count = await self.get_pumpswap_token_count()
                if pumpswap_token_count < 1000:  # Primeiros tokens
                    destination_score *= 1.2
                    opportunity_factors.append("Entre os primeiros tokens no PumpSwap")
                
            elif migration_destination == 'Raydium':
                # Raydium: mais estabelecido, maior liquidez, mas com taxas
                destination_score = 0.9
                opportunity_factors.append("Migração para Raydium (estabelecido)")
                
                # Verificar liquidez geral do Raydium
                raydium_tvl = await self.get_raydium_tvl()
                if raydium_tvl > 1000000000:  # $1B+ TVL
                    destination_score *= 1.1
                    opportunity_factors.append("Raydium com alta liquidez")
                
            else:
                destination_score = 0.5
                risk_factors.append("Destino de migração desconhecido")
            
            return destination_score, risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar destino da migração: {e}")
            risk_factors.append("Erro na análise do destino")
            return 0.5, risk_factors

    async def perform_migration_analysis(self, token_data: Dict) -> MigrationAnalysis:
        """
        Realiza análise completa específica para tokens migrados.
        """
        try:
            # Executar todas as análises em paralelo
            results = await asyncio.gather(
                self.analyze_liquidity_stability(token_data),
                self.analyze_post_migration_volume(token_data),
                self.analyze_smart_money_following(token_data),
                self.analyze_migration_timing(token_data),
                self.analyze_migration_destination_quality(token_data),
                return_exceptions=True
            )
            
            # Extrair scores e fatores
            liquidity_score, liquidity_factors = results[0] if not isinstance(results[0], Exception) else (0.0, ["Erro na análise de liquidez"])
            volume_score, volume_factors = results[1] if not isinstance(results[1], Exception) else (0.0, ["Erro na análise de volume"])
            smart_money_score, smart_money_factors = results[2] if not isinstance(results[2], Exception) else (0.0, ["Erro na análise de smart money"])
            timing_score, timing_factors = results[3] if not isinstance(results[3], Exception) else (0.0, ["Erro na análise de timing"])
            destination_score, destination_factors = results[4] if not isinstance(results[4], Exception) else (0.0, ["Erro na análise de destino"])
            
            # Calcular score geral ponderado
            overall_score = (
                liquidity_score * self.migration_weights['liquidity_stability'] +
                volume_score * self.migration_weights['post_migration_volume'] +
                smart_money_score * self.migration_weights['smart_money_following'] +
                timing_score * self.migration_weights['migration_timing'] +
                destination_score * self.migration_weights['migration_destination_quality']
            )
            
            # Compilar fatores de risco e oportunidade
            all_factors = (liquidity_factors + volume_factors + smart_money_factors + 
                          timing_factors + destination_factors)
            
            risk_factors = [f for f in all_factors if any(word in f.lower() for word in ['risco', 'erro', 'baixo', 'declínio', 'volátil', 'insuficiente'])]
            opportunity_factors = [f for f in all_factors if f not in risk_factors]
            
            return MigrationAnalysis(
                token_address=token_data['token_address'],
                migration_destination=token_data['migration_destination'],
                migration_quality_score=overall_score,
                liquidity_stability_score=liquidity_score,
                post_migration_volume_score=volume_score,
                smart_money_following_score=smart_money_score,
                migration_timing_score=timing_score,
                overall_migration_score=overall_score,
                risk_factors=risk_factors,
                opportunity_factors=opportunity_factors
            )
            
        except Exception as e:
            logger.error(f"Erro na análise de migração: {e}")
            return MigrationAnalysis(
                token_address=token_data['token_address'],
                migration_destination=token_data.get('migration_destination', 'Unknown'),
                migration_quality_score=0.0,
                liquidity_stability_score=0.0,
                post_migration_volume_score=0.0,
                smart_money_following_score=0.0,
                migration_timing_score=0.0,
                overall_migration_score=0.0,
                risk_factors=["Erro na análise completa"],
                opportunity_factors=[]
            )

    def calculate_trend(self, values: List[float]) -> float:
        """Calcula a tendência de uma série de valores."""
        if len(values) < 2:
            return 0.0
        
        x = np.arange(len(values))
        slope = np.polyfit(x, values, 1)[0]
        return slope / (np.mean(values) + 1)  # Normalizado

    async def get_post_migration_liquidity(self, token_address: str, destination: str) -> List[Dict]:
        """Obtém dados de liquidez pós-migração."""
        # Implementação específica para cada destino
        # Por simplicidade, retornamos dados simulados
        return [
            {'timestamp': datetime.now() - timedelta(hours=i), 'liquidity_usd': 50000 + i * 1000}
            for i in range(10)
        ]

    async def get_post_migration_volume(self, token_address: str, destination: str) -> List[Dict]:
        """Obtém dados de volume pós-migração."""
        # Implementação específica para cada destino
        return [
            {'timestamp': datetime.now() - timedelta(hours=i), 'volume_usd': 10000 + i * 500}
            for i in range(10)
        ]

    async def get_smart_money_wallets(self) -> List[str]:
        """Obtém lista de carteiras conhecidas como 'smart money'."""
        # Lista de carteiras conhecidas por bons trades
        return [
            "wallet1...", "wallet2...", "wallet3..."  # Endereços reais seriam usados
        ]

    async def check_smart_money_activity(self, token_address: str, wallets: List[str]) -> List[Dict]:
        """Verifica atividade de smart money no token."""
        # Implementação para verificar transações das carteiras
        return [
            {'wallet': 'wallet1...', 'type': 'buy', 'amount': 1000},
            {'wallet': 'wallet2...', 'type': 'buy', 'amount': 2000}
        ]

    async def get_market_conditions_at_time(self, timestamp: datetime) -> Dict:
        """Obtém condições de mercado em um momento específico."""
        return {
            'sol_price_trend': 0.03,  # 3% de alta
            'memecoin_volume_trend': 0.15  # 15% de aumento no volume
        }

    async def get_pumpswap_token_count(self) -> int:
        """Obtém número total de tokens no PumpSwap."""
        return 500  # Valor simulado

    async def get_raydium_tvl(self) -> float:
        """Obtém TVL total do Raydium."""
        return 1500000000  # $1.5B simulado

    def save_analysis(self, analysis: MigrationAnalysis) -> None:
        """Salva a análise no DynamoDB."""
        try:
            item = {
                'token_address': analysis.token_address,
                'analysis_timestamp': datetime.now().isoformat(),
                'migration_destination': analysis.migration_destination,
                'overall_migration_score': analysis.overall_migration_score,
                'liquidity_stability_score': analysis.liquidity_stability_score,
                'post_migration_volume_score': analysis.post_migration_volume_score,
                'smart_money_following_score': analysis.smart_money_following_score,
                'migration_timing_score': analysis.migration_timing_score,
                'risk_factors': analysis.risk_factors,
                'opportunity_factors': analysis.opportunity_factors,
                'analysis_type': 'migration_analysis'
            }
            
            self.analysis_table.put_item(Item=item)
            logger.info(f"Análise salva para token {analysis.token_address}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar análise: {e}")

    def send_to_trader(self, analysis: MigrationAnalysis) -> None:
        """Envia análise para o agente Trader se o score for suficiente."""
        try:
            # Threshold específico para tokens migrados (pode ser mais baixo que tokens normais)
            migration_threshold = 0.6
            
            if analysis.overall_migration_score >= migration_threshold:
                message = {
                    'token_address': analysis.token_address,
                    'migration_destination': analysis.migration_destination,
                    'overall_score': analysis.overall_migration_score,
                    'analysis_type': 'migration_analysis',
                    'risk_factors': analysis.risk_factors,
                    'opportunity_factors': analysis.opportunity_factors,
                    'recommendation': 'BUY' if analysis.overall_migration_score > 0.8 else 'CONSIDER',
                    'timestamp': datetime.now().isoformat()
                }
                
                sqs.send_message(
                    QueueUrl=TRADER_QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
                
                logger.info(f"Token migrado {analysis.token_address} enviado para trader com score {analysis.overall_migration_score:.2f}")
            else:
                logger.info(f"Token migrado {analysis.token_address} rejeitado - score {analysis.overall_migration_score:.2f} abaixo do threshold {migration_threshold}")
                
        except Exception as e:
            logger.error(f"Erro ao enviar para trader: {e}")


async def lambda_handler(event, context):
    """Função principal do Lambda para o Enhanced Analyzer."""
    try:
        logger.info("Enhanced Analyzer iniciado - analisando tokens migrados")
        
        async with EnhancedAnalyzer() as analyzer:
            # Processar mensagens da fila SQS
            for record in event.get('Records', []):
                try:
                    # Parse da mensagem
                    message_body = json.loads(record['body'])
                    
                    # Verificar se é um token migrado
                    if message_body.get('token_type') == 'migrated_token':
                        logger.info(f"Analisando token migrado: {message_body['token_address']}")
                        
                        # Realizar análise específica para migração
                        analysis = await analyzer.perform_migration_analysis(message_body)
                        
                        # Salvar análise
                        analyzer.save_analysis(analysis)
                        
                        # Enviar para trader se qualificado
                        analyzer.send_to_trader(analysis)
                        
                        logger.info(f"Análise concluída para {analysis.token_address} - Score: {analysis.overall_migration_score:.2f}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {e}")
                    continue
        
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Enhanced Analyzer executado com sucesso'})
        }
    
    except Exception as e:
        logger.error(f"Erro no Enhanced Analyzer: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }


# Para teste local
if __name__ == "__main__":
    import asyncio
    
    async def test_analyzer():
        test_token_data = {
            'token_address': 'test_token_123',
            'migration_destination': 'PumpSwap',
            'graduation_timestamp': datetime.now().isoformat(),
            'migration_timestamp': datetime.now().isoformat(),
            'market_cap_at_graduation': 75000,
            'liquidity_at_graduation': 25000
        }
        
        async with EnhancedAnalyzer() as analyzer:
            analysis = await analyzer.perform_migration_analysis(test_token_data)
            print(f"Análise concluída:")
            print(f"Score geral: {analysis.overall_migration_score:.2f}")
            print(f"Fatores de risco: {analysis.risk_factors}")
            print(f"Fatores de oportunidade: {analysis.opportunity_factors}")
    
    asyncio.run(test_analyzer())

