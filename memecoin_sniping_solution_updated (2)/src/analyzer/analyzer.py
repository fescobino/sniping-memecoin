import json
import logging
import os
import boto3
import requests
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from botocore.exceptions import ClientError, NoCredentialsError
from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass

# Configuração de logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clientes AWS
# Mock de secrets para teste local (NÃO USE EM PRODUÇÃO)
class MockSecretsManager:
    def get_secret_value(self, SecretId):
        if SecretId == "/memecoin-sniping/moralis-api-key":
            return {"SecretString": json.dumps({"apiKey": "YOUR_MORALIS_API_KEY"})}
        elif SecretId == "/memecoin-sniping/bitquery-api-key":
            return {"SecretString": json.dumps({"apiKey": "YOUR_BITQUERY_API_KEY"})}
        elif SecretId == "/memecoin-sniping/shyft-api-key":
            return {"SecretString": json.dumps({"apiKey": "YOUR_SHYFT_API_KEY"})}
        raise ClientError({"Error": {"Code": "ResourceNotFoundException"}}, "GetSecretValue")

# Mock de DynamoDB para teste local (NÃO USE EM PRODUÇÃO)
class MockDynamoDBTable:
    def __init__(self, name):
        self.name = name
        self.items = {}
    
    def get_item(self, Key):
        return {"Item": self.items.get(Key["token_address"])}
        
    def put_item(self, Item):
        self.items[Item["token_address"]] = Item
        
# Mock de SQS para teste local (NÃO USE EM PRODUÇÃO)
class MockSQSClient:
    def send_message(self, QueueUrl, MessageBody):
        print(f"Mock SQS: Mensagem enviada para {QueueUrl}: {MessageBody}")
        return {"MessageId": "mock-message-id"}

# Substitui os clientes AWS pelos mocks para teste local
boto3_client_original = boto3.client
boto3_resource_original = boto3.resource

def mock_boto3_client(service_name):
    if service_name == "secretsmanager":
        return MockSecretsManager()
    elif service_name == "sqs":
        return MockSQSClient()
    return boto3_client_original(service_name)

def mock_boto3_resource(service_name):
    if service_name == "dynamodb":
        return type("MockDynamoDB", (object,), {"Table": MockDynamoDBTable})()
    return boto3_resource_original(service_name)

boto3.client = mock_boto3_client
boto3.resource = mock_boto3_resource

sqs = boto3.client("sqs")
dynamodb = boto3.resource("dynamodb")
secrets_manager = boto3.client("secretsmanager")

# Variáveis de ambiente
TRADER_QUEUE_URL = os.environ.get("TRADER_QUEUE_URL")
ANALYSIS_TABLE = os.environ.get("ANALYSIS_TABLE", "PumpSwapAnalysisTable")

@dataclass
class PumpSwapAnalysis:
    """Estrutura para análise específica de tokens migrados para PumpSwap."""
    token_address: str
    token_symbol: str
    token_name: str
    pumpswap_quality_score: float
    early_adoption_score: float
    liquidity_growth_score: float
    volume_momentum_score: float
    price_stability_score: float
    community_interest_score: float
    overall_pumpswap_score: float
    risk_factors: List[str]
    opportunity_factors: List[str]
    recommended_action: str
    confidence_level: str

class PumpSwapFocusedAnalyzer:
    def __init__(self):
        self.analysis_table = dynamodb.Table(ANALYSIS_TABLE)
        self.session = aiohttp.ClientSession()
        
        # Pesos específicos para análise PumpSwap
        self.pumpswap_weights = {
            "early_adoption": 0.25,      # Ser cedo no PumpSwap é vantajoso
            "liquidity_growth": 0.20,    # Crescimento de liquidez
            "volume_momentum": 0.20,     # Momentum de volume
            "price_stability": 0.15,     # Estabilidade de preço
            "community_interest": 0.20   # Interesse da comunidade
        }
        
        # Thresholds específicos para PumpSwap
        self.thresholds = {
            "min_liquidity_usd": 500,
            "min_volume_24h_usd": 1000,
            "max_price_volatility": 0.5,  # 50% volatilidade máxima
            "min_trade_count": 5,
            "early_adopter_threshold_hours": 6  # Primeiras 6 horas
        }
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.session.close()

    def get_secret(self, secret_name: str) -> Dict:
        """Recupera um segredo do AWS Secrets Manager."""
        try:
            response = secrets_manager.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except (ClientError, NoCredentialsError) as e:
            logger.error(f"Erro ao recuperar segredo {secret_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao recuperar segredo {secret_name}: {e}")
            raise

    async def analyze_early_adoption_advantage(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa a vantagem de early adoption no PumpSwap.
        Tokens que migram cedo para PumpSwap podem ter vantagens.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            # Garantir que migration_timestamp seja timezone-aware
            migration_timestamp_str = token_data["migration_timestamp"]
            if migration_timestamp_str.endswith("Z"):
                migration_timestamp_str = migration_timestamp_str.replace("Z", "+00:00")
            migration_timestamp = datetime.fromisoformat(migration_timestamp_str)
            
            # Garantir que datetime.now() seja timezone-aware (UTC)
            current_time = datetime.now(timezone.utc)
            
            time_since_migration = current_time - migration_timestamp
            
            # Score baseado em quão cedo estamos detectando
            hours_since_migration = time_since_migration.total_seconds() / 3600
            
            if hours_since_migration <= 1:
                early_score = 1.0
                opportunity_factors.append("Detectado na primeira hora pós-migração")
            elif hours_since_migration <= 3:
                early_score = 0.9
                opportunity_factors.append("Detectado nas primeiras 3 horas")
            elif hours_since_migration <= 6:
                early_score = 0.7
                opportunity_factors.append("Detectado nas primeiras 6 horas")
            elif hours_since_migration <= 12:
                early_score = 0.5
            elif hours_since_migration <= 24:
                early_score = 0.3
                risk_factors.append("Detectado após 24 horas da migração")
            else:
                early_score = 0.1
                risk_factors.append("Detectado muito tarde pós-migração")
            
            # Bonus para tokens com poucos concorrentes no PumpSwap
            pumpswap_token_count = await self.get_current_pumpswap_token_count()
            
            if pumpswap_token_count < 100:
                early_score *= 1.3
                opportunity_factors.append("PumpSwap ainda com poucos tokens")
            elif pumpswap_token_count < 500:
                early_score *= 1.1
                opportunity_factors.append("PumpSwap em fase inicial")
            
            # Verificar se é um dos primeiros tokens do dia
            daily_migration_count = await self.get_daily_migration_count()
            
            if daily_migration_count <= 5:
                early_score *= 1.2
                opportunity_factors.append("Entre os primeiros tokens do dia")
            elif daily_migration_count <= 10:
                early_score *= 1.1
                opportunity_factors.append("Entre os primeiros 10 tokens do dia")
            
            return min(early_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar early adoption: {e}")
            risk_factors.append("Erro na análise de early adoption")
            return 0.0, risk_factors

    async def analyze_liquidity_growth_potential(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa o potencial de crescimento de liquidez no PumpSwap.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            pool_data = token_data.get("pool_data", {})
            
            if not pool_data:
                risk_factors.append("Dados de pool não disponíveis")
                return 0.3, risk_factors
            
            current_liquidity = pool_data.get("liquidity_usd", 0)
            volume_24h = pool_data.get("volume_24h_usd", 0)
            
            # Score baseado na liquidez atual
            if current_liquidity >= 10000:
                liquidity_score = 1.0
                opportunity_factors.append(f"Alta liquidez: ${current_liquidity:,.0f}")
            elif current_liquidity >= 5000:
                liquidity_score = 0.8
                opportunity_factors.append(f"Boa liquidez: ${current_liquidity:,.0f}")
            elif current_liquidity >= 1000:
                liquidity_score = 0.6
                opportunity_factors.append(f"Liquidez moderada: ${current_liquidity:,.0f}")
            elif current_liquidity >= 500:
                liquidity_score = 0.4
            else:
                liquidity_score = 0.2
                risk_factors.append(f"Baixa liquidez: ${current_liquidity:,.0f}")
            
            # Analisar ratio volume/liquidez (turnover)
            if current_liquidity > 0:
                turnover_ratio = volume_24h / current_liquidity
                
                if turnover_ratio > 2.0:  # Volume > 2x liquidez
                    liquidity_score *= 1.3
                    opportunity_factors.append("Alto turnover de liquidez")
                elif turnover_ratio > 1.0:
                    liquidity_score *= 1.1
                    opportunity_factors.append("Bom turnover de liquidez")
                elif turnover_ratio < 0.1:
                    liquidity_score *= 0.7
                    risk_factors.append("Baixo turnover de liquidez")
            
            # Verificar crescimento histórico de liquidez
            liquidity_growth = await self.get_liquidity_growth_trend(token_data["token_address"])
            
            if liquidity_growth > 0.2:  # 20% crescimento
                liquidity_score *= 1.2
                opportunity_factors.append("Liquidez em forte crescimento")
            elif liquidity_growth > 0.1:
                liquidity_score *= 1.1
                opportunity_factors.append("Liquidez em crescimento")
            elif liquidity_growth < -0.1:
                liquidity_score *= 0.8
                risk_factors.append("Liquidez em declínio")
            
            return min(liquidity_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar crescimento de liquidez: {e}")
            risk_factors.append("Erro na análise de liquidez")
            return 0.0, risk_factors

    async def analyze_volume_momentum(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa o momentum de volume no PumpSwap.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            total_volume = token_data.get("total_volume_usd", 0)
            trade_count = token_data.get("trade_count", 0)
            pool_data = token_data.get("pool_data", {})
            volume_24h = pool_data.get("volume_24h_usd", 0)
            
            # Score baseado no volume total desde migração
            if total_volume >= 50000:
                volume_score = 1.0
                opportunity_factors.append(f"Alto volume total: ${total_volume:,.0f}")
            elif total_volume >= 20000:
                volume_score = 0.8
                opportunity_factors.append(f"Bom volume total: ${total_volume:,.0f}")
            elif total_volume >= 5000:
                volume_score = 0.6
            elif total_volume >= 1000:
                volume_score = 0.4
            else:
                volume_score = 0.2
                risk_factors.append(f"Baixo volume total: ${total_volume:,.0f}")
            
            # Analisar ratio volume/liquidez (turnover)
            if trade_count > 0:
                avg_trade_size = total_volume / trade_count
                
                if avg_trade_size >= 1000:
                    volume_score *= 1.2
                    opportunity_factors.append("Trades de alto valor")
                elif avg_trade_size >= 500:
                    volume_score *= 1.1
                    opportunity_factors.append("Trades de valor moderado")
                elif avg_trade_size < 100:
                    volume_score *= 0.8
                    risk_factors.append("Trades de baixo valor")
            
            # Verificar aceleração de volume
            volume_acceleration = await self.get_volume_acceleration(token_data["token_address"])
            
            if volume_acceleration > 0.5:  # 50% aceleração
                volume_score *= 1.3
                opportunity_factors.append("Volume em forte aceleração")
            elif volume_acceleration > 0.2:
                volume_score *= 1.1
                opportunity_factors.append("Volume em aceleração")
            elif volume_acceleration < -0.2:
                volume_score *= 0.7
                risk_factors.append("Volume desacelerando")
            
            # Verificar consistência de trades
            if trade_count >= 20:
                opportunity_factors.append("Alta atividade de trading")
                volume_score *= 1.1
            elif trade_count >= 10:
                opportunity_factors.append("Boa atividade de trading")
            elif trade_count < 5:
                risk_factors.append("Baixa atividade de trading")
                volume_score *= 0.8
            
            return min(volume_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar momentum de volume: {e}")
            risk_factors.append("Erro na análise de volume")
            return 0.0, risk_factors

    async def analyze_price_stability(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa a estabilidade de preço no PumpSwap.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            pool_data = token_data.get("pool_data", {})
            
            if not pool_data:
                risk_factors.append("Dados de preço não disponíveis")
                return 0.3, risk_factors
            
            current_price = pool_data.get("price_usd", 0)
            price_change_24h = pool_data.get("price_change_24h", 0)
            
            if current_price <= 0:
                risk_factors.append("Preço inválido")
                return 0.1, risk_factors
            
            # Score baseado na variação de preço 24h
            abs_price_change = abs(price_change_24h)
            
            if abs_price_change <= 0.1:  # ±10%
                stability_score = 1.0
                opportunity_factors.append("Preço muito estável")
            elif abs_price_change <= 0.2:  # ±20%
                stability_score = 0.8
                opportunity_factors.append(f"Preço estável")
            elif abs_price_change <= 0.3:  # ±30%
                stability_score = 0.6
            elif abs_price_change <= 0.5:  # ±50%
                stability_score = 0.4
                risk_factors.append("Preço moderadamente volátil")
            else:
                stability_score = 0.2
                risk_factors.append("Preço muito volátil")
            
            # Bonus para tendência de alta controlada
            if 0 < price_change_24h <= 0.3:  # Alta de até 30%
                stability_score *= 1.2
                opportunity_factors.append(f"Tendência de alta controlada: +{price_change_24h*100:.1f}%")
            elif price_change_24h > 0.5:  # Alta muito forte
                stability_score *= 0.8
                risk_factors.append("Alta muito agressiva pode indicar pump")
            elif price_change_24h < -0.3:  # Queda forte
                stability_score *= 0.7
                risk_factors.append("Queda significativa de preço")
            
            # Analisar volatilidade histórica
            price_volatility = await self.get_price_volatility(token_data["token_address"])
            
            if price_volatility < 0.2:  # Baixa volatilidade
                stability_score *= 1.1
                opportunity_factors.append("Baixa volatilidade histórica")
            elif price_volatility > 0.6:  # Alta volatilidade
                stability_score *= 0.8
                risk_factors.append("Alta volatilidade histórica")
            
            return min(stability_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar estabilidade de preço: {e}")
            risk_factors.append("Erro na análise de preço")
            return 0.0, risk_factors

    async def analyze_community_interest(self, token_data: Dict) -> Tuple[float, List[str]]:
        """
        Analisa o interesse da comunidade no token PumpSwap.
        """
        risk_factors = []
        opportunity_factors = []
        
        try:
            token_symbol = token_data.get("token_symbol", "")
            token_name = token_data.get("token_name", "")
            
            # Analisar atividade social (simulado - implementação real usaria APIs sociais)
            social_metrics = await self.get_social_metrics(token_symbol, token_name)
            
            # Score baseado em métricas sociais
            twitter_mentions = social_metrics.get("twitter_mentions", 0)
            telegram_activity = social_metrics.get("telegram_activity", 0)
            discord_activity = social_metrics.get("discord_activity", 0)
            
            # Calcular score de interesse
            if twitter_mentions >= 100:
                interest_score = 1.0
                opportunity_factors.append(f"Alto interesse no Twitter: {twitter_mentions} menções")
            elif twitter_mentions >= 50:
                interest_score = 0.8
                opportunity_factors.append(f"Bom interesse no Twitter: {twitter_mentions} menções")
            elif twitter_mentions >= 10:
                interest_score = 0.6
            elif twitter_mentions >= 5:
                interest_score = 0.4
            else:
                interest_score = 0.2
                risk_factors.append("Baixo interesse social")
            
            # Bonus para atividade em múltiplas plataformas
            active_platforms = sum([
                1 if twitter_mentions > 0 else 0,
                1 if telegram_activity > 0 else 0,
                1 if discord_activity > 0 else 0
            ])
            
            if active_platforms >= 3:
                interest_score *= 1.3
                opportunity_factors.append("Ativo em múltiplas plataformas sociais")
            elif active_platforms >= 2:
                interest_score *= 1.1
                opportunity_factors.append("Ativo em várias plataformas")
            
            # Analisar qualidade do nome/símbolo
            if len(token_symbol) <= 6 and token_symbol.isalpha():
                interest_score *= 1.1
                opportunity_factors.append("Símbolo limpo e memorável")
            
            if len(token_name) <= 20 and not any(char.isdigit() for char in token_name):
                interest_score *= 1.05
                opportunity_factors.append("Nome profissional")
            
            # Verificar se não é um meme muito genérico
            generic_terms = ["coin", "token", "meme", "doge", "shib", "pepe"]
            if any(term in token_name.lower() for term in generic_terms):
                interest_score *= 0.9
                risk_factors.append("Nome genérico pode indicar falta de originalidade")
            
            return min(interest_score, 1.0), risk_factors + opportunity_factors
            
        except Exception as e:
            logger.error(f"Erro ao analisar interesse da comunidade: {e}")
            risk_factors.append("Erro na análise de comunidade")
            return 0.0, risk_factors

    async def perform_pumpswap_analysis(self, token_data: Dict) -> PumpSwapAnalysis:
        """
        Realiza análise completa específica para tokens PumpSwap.
        """
        try:
            logger.info(f"Iniciando análise PumpSwap para {token_data['token_address']}")
            
            # Executar todas as análises em paralelo
            results = await asyncio.gather(
                self.analyze_early_adoption_advantage(token_data),
                self.analyze_liquidity_growth_potential(token_data),
                self.analyze_volume_momentum(token_data),
                self.analyze_price_stability(token_data),
                self.analyze_community_interest(token_data),
                return_exceptions=True
            )
            
            # Extrair scores e fatores
            early_score, early_factors = results[0] if not isinstance(results[0], Exception) else (0.0, ["Erro na análise early adoption"])
            liquidity_score, liquidity_factors = results[1] if not isinstance(results[1], Exception) else (0.0, ["Erro na análise de liquidez"])
            volume_score, volume_factors = results[2] if not isinstance(results[2], Exception) else (0.0, ["Erro na análise de volume"])
            stability_score, stability_factors = results[3] if not isinstance(results[3], Exception) else (0.0, ["Erro na análise de estabilidade"])
            community_score, community_factors = results[4] if not isinstance(results[4], Exception) else (0.0, ["Erro na análise de comunidade"])
            
            # Calcular score geral ponderado
            overall_score = (
                early_score * self.pumpswap_weights["early_adoption"] +
                liquidity_score * self.pumpswap_weights["liquidity_growth"] +
                volume_score * self.pumpswap_weights["volume_momentum"] +
                stability_score * self.pumpswap_weights["price_stability"] +
                community_score * self.pumpswap_weights["community_interest"]
            )
            
            # Compilar fatores
            all_factors = (early_factors + liquidity_factors + volume_factors + 
                          stability_factors + community_factors)
            
            risk_factors = [f for f in all_factors if any(word in f.lower() for word in 
                           ["risco", "erro", "baixo", "declínio", "volátil", "insuficiente", "genérico"])]
            opportunity_factors = [f for f in all_factors if f not in risk_factors]
            
            # Determinar recomendação
            if overall_score >= 0.8:
                recommended_action = "STRONG_BUY"
                confidence_level = "HIGH"
            elif overall_score >= 0.65:
                recommended_action = "BUY"
                confidence_level = "MEDIUM"
            elif overall_score >= 0.5:
                recommended_action = "CONSIDER"
                confidence_level = "LOW"
            else:
                recommended_action = "AVOID"
                confidence_level = "HIGH"
            
            return PumpSwapAnalysis(
                token_address=token_data["token_address"],
                token_symbol=token_data.get("token_symbol", ""),
                token_name=token_data.get("token_name", ""),
                pumpswap_quality_score=overall_score,
                early_adoption_score=early_score,
                liquidity_growth_score=liquidity_score,
                volume_momentum_score=volume_score,
                price_stability_score=stability_score,
                community_interest_score=community_score,
                overall_pumpswap_score=overall_score,
                risk_factors=risk_factors,
                opportunity_factors=opportunity_factors,
                recommended_action=recommended_action,
                confidence_level=confidence_level
            )
            
        except Exception as e:
            logger.error(f"Erro na análise PumpSwap: {e}")
            return PumpSwapAnalysis(
                token_address=token_data["token_address"],
                token_symbol=token_data.get("token_symbol", ""),
                token_name=token_data.get("token_name", ""),
                pumpswap_quality_score=0.0,
                early_adoption_score=0.0,
                liquidity_growth_score=0.0,
                volume_momentum_score=0.0,
                price_stability_score=0.0,
                community_interest_score=0.0,
                overall_pumpswap_score=0.0,
                risk_factors=["Erro na análise completa"],
                opportunity_factors=[],
                recommended_action="AVOID",
                confidence_level="HIGH"
            )

    # Métodos auxiliares (implementações simplificadas)
    async def get_current_pumpswap_token_count(self) -> int:
        """Obtém número atual de tokens no PumpSwap."""
        return 250  # Valor simulado

    async def get_daily_migration_count(self) -> int:
        """Obtém número de migrações do dia."""
        return 8  # Valor simulado

    async def get_liquidity_growth_trend(self, token_address: str) -> float:
        """Obtém tendência de crescimento de liquidez."""
        return 0.15  # 15% crescimento simulado

    async def get_volume_acceleration(self, token_address: str) -> float:
        """Obtém aceleração de volume."""
        return 0.3  # 30% aceleração simulada

    async def get_price_volatility(self, token_address: str) -> float:
        """Obtém volatilidade histórica de preço."""
        return 0.25  # 25% volatilidade simulada

    async def get_social_metrics(self, symbol: str, name: str) -> Dict:
        """Obtém métricas sociais do token."""
        return {
            "twitter_mentions": 25,
            "telegram_activity": 15,
            "discord_activity": 10
        }

    def save_analysis(self, analysis: PumpSwapAnalysis) -> None:
        """Salva a análise no DynamoDB."""
        try:
            item = {
                "token_address": analysis.token_address,
                "analysis_timestamp": datetime.now().isoformat(),
                "token_symbol": analysis.token_symbol,
                "token_name": analysis.token_name,
                "overall_pumpswap_score": analysis.overall_pumpswap_score,
                "early_adoption_score": analysis.early_adoption_score,
                "liquidity_growth_score": analysis.liquidity_growth_score,
                "volume_momentum_score": analysis.volume_momentum_score,
                "price_stability_score": analysis.price_stability_score,
                "community_interest_score": analysis.community_interest_score,
                "risk_factors": analysis.risk_factors,
                "opportunity_factors": analysis.opportunity_factors,
                "recommended_action": analysis.recommended_action,
                "confidence_level": analysis.confidence_level,
                "analysis_type": "pumpswap_analysis"
            }
            
            self.analysis_table.put_item(Item=item)
            logger.info(f"Análise PumpSwap salva para {analysis.token_address}")
            
        except ClientError as e:
            logger.error(f"Erro de cliente DynamoDB ao salvar análise: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao salvar análise: {e}")

    def send_to_trader(self, analysis: PumpSwapAnalysis) -> None:
        """Envia análise para o agente Trader se qualificado."""
        try:
            # Threshold mais baixo para PumpSwap devido ao potencial early adoption
            pumpswap_threshold = 0.5
            
            if analysis.overall_pumpswap_score >= pumpswap_threshold:
                message = {
                    "token_address": analysis.token_address,
                    "token_symbol": analysis.token_symbol,
                    "token_name": analysis.token_name,
                    "migration_destination": "PumpSwap",
                    "overall_score": analysis.overall_pumpswap_score,
                    "recommended_action": analysis.recommended_action,
                    "confidence_level": analysis.confidence_level,
                    "analysis_type": "pumpswap_analysis",
                    "risk_factors": analysis.risk_factors,
                    "opportunity_factors": analysis.opportunity_factors,
                    "early_adoption_score": analysis.early_adoption_score,
                    "timestamp": datetime.now().isoformat()
                }
                
                sqs.send_message(
                    QueueUrl=TRADER_QUEUE_URL,
                    MessageBody=json.dumps(message)
                )
                
                logger.info(f"Token PumpSwap {analysis.token_address} enviado para trader - Score: {analysis.overall_pumpswap_score:.2f}, Ação: {analysis.recommended_action}")
            else:
                logger.info(f"Token PumpSwap {analysis.token_address} rejeitado - Score {analysis.overall_pumpswap_score:.2f} abaixo do threshold {pumpswap_threshold}")
                
        except ClientError as e:
            logger.error(f"Erro de cliente SQS ao enviar mensagem para trader: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao enviar para trader: {e}")


async def lambda_handler(event, context):
    """Função principal do Lambda para análise PumpSwap."""
    try:
        logger.info("PumpSwap Focused Analyzer iniciado")
        
        # Verifica se TRADER_QUEUE_URL e ANALYSIS_TABLE estão definidos
        if not TRADER_QUEUE_URL:
            logger.error("Variável de ambiente TRADER_QUEUE_URL não definida.")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "TRADER_QUEUE_URL não configurado."})
            }
        if not ANALYSIS_TABLE:
            logger.error("Variável de ambiente ANALYSIS_TABLE não definida.")
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "ANALYSIS_TABLE não configurado."})
            }

        async with PumpSwapFocusedAnalyzer() as analyzer:
            processed_count = 0
            
            # Processar mensagens da fila SQS
            for record in event.get("Records", []):
                try:
                    message_body = json.loads(record["body"])
                    
                    # Verificar se é um token PumpSwap
                    if message_body.get("token_type") == "pumpswap_migrated_token":
                        logger.info(f"Analisando token PumpSwap: {message_body['token_address']}")
                        
                        # Realizar análise específica para PumpSwap
                        analysis = await analyzer.perform_pumpswap_analysis(message_body)
                        
                        # Salvar análise
                        analyzer.save_analysis(analysis)
                        
                        # Enviar para trader se qualificado
                        analyzer.send_to_trader(analysis)
                        
                        processed_count += 1
                        logger.info(f"Análise PumpSwap concluída para {analysis.token_address} - Score: {analysis.overall_pumpswap_score:.2f}, Ação: {analysis.recommended_action}")
                    
                except Exception as e:
                    logger.error(f"Erro ao processar mensagem: {e}")
                    continue
        
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "PumpSwap Focused Analyzer executado com sucesso",
                "tokens_processed": processed_count
            })
        }
    
    except Exception as e:
        logger.error(f"Erro no PumpSwap Focused Analyzer: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


# Para teste local
if __name__ == "__main__":
    import asyncio
    
    # Configurações de ambiente para teste local
    os.environ["TRADER_QUEUE_URL"] = "YOUR_LOCAL_TRADER_QUEUE_URL" # Substitua pela URL da sua fila SQS local ou mock
    os.environ["ANALYSIS_TABLE"] = "PumpSwapAnalysisTable" # Substitua pelo nome da sua tabela DynamoDB local ou mock
    
    async def test_analyzer():
        test_token_data = {
            "token_address": "test_pumpswap_token_123",
            "token_symbol": "TEST",
            "token_name": "Test Token",
            "migration_timestamp": datetime.now(timezone.utc).isoformat(), # Garante que o timestamp de migração seja timezone-aware
            "total_volume_usd": 15000,
            "trade_count": 25,
            "pool_data": {
                "liquidity_usd": 8000,
                "volume_24h_usd": 12000,
                "price_usd": 0.001,
                "price_change_24h": 0.15
            }
        }
        
        async with PumpSwapFocusedAnalyzer() as analyzer:
            analysis = await analyzer.perform_pumpswap_analysis(test_token_data)
            print(f"Análise PumpSwap concluída:")
            print(f"Score geral: {analysis.overall_pumpswap_score:.2f}")
            print(f"Recomendação: {analysis.recommended_action}")
            print(f"Confiança: {analysis.confidence_level}")
            print(f"Fatores de oportunidade: {analysis.opportunity_factors}")
            print(f"Fatores de risco: {analysis.risk_factors}")
    
    asyncio.run(test_analyzer())













