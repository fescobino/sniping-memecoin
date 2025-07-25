#!/usr/bin/env python3
"""
Script de teste para o Agente Analyzer.
Este script simula o comportamento do Analyzer sem depender de AWS ou APIs externas.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import types

# Create a stub boto3 module so patch works without the real dependency
sys.modules['boto3'] = types.SimpleNamespace(client=Mock(), resource=Mock())
solana_api = types.SimpleNamespace(Client=Mock())
solana_rpc = types.SimpleNamespace(api=solana_api)
sys.modules['solana'] = types.SimpleNamespace(rpc=solana_rpc)
sys.modules['solana.rpc'] = solana_rpc
sys.modules['solana.rpc.api'] = solana_api
sys.modules['tweepy'] = types.SimpleNamespace(API=Mock(), OAuthHandler=Mock())
sys.modules['requests'] = Mock()
sys.modules['aiohttp'] = Mock()
sys.modules['botocore'] = types.SimpleNamespace(exceptions=types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception))
sys.modules['botocore.exceptions'] = types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception)
sys.modules['numpy'] = Mock()

# Adiciona o diretório atual ao path para importar o módulo analyzer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock das dependências para teste local
with patch('boto3.client'), \
     patch('solana.rpc.api.Client'), \
     patch('tweepy.API'), \
     patch('tweepy.OAuthHandler'):
    from analyzer import process_token_analysis, calculate_quality_score, lambda_handler

def test_calculate_quality_score():
    """Testa o cálculo do score de qualidade."""
    print("Testando calculate_quality_score...")
    
    # Dados de teste - token de boa qualidade
    good_on_chain = {
        'account_exists': True,
        'is_honeypot': False,
        'liquidity_locked': True,
        'deployer_percentage': 5.0
    }
    
    good_social = {
        'sentiment_score': 0.8,
        'tweet_count': 25,
        'social_activity': 'high'
    }
    
    score = calculate_quality_score(good_on_chain, good_social)
    
    assert score > 60, f"Score de token bom deveria ser > 60, recebido: {score}"
    print(f"✓ Token bom recebeu score: {score}")
    
    # Dados de teste - token de má qualidade
    bad_on_chain = {
        'account_exists': True,
        'is_honeypot': True,
        'liquidity_locked': False,
        'deployer_percentage': 80.0
    }
    
    bad_social = {
        'sentiment_score': -0.5,
        'tweet_count': 2,
        'social_activity': 'low'
    }
    
    score = calculate_quality_score(bad_on_chain, bad_social)
    
    assert score < 60, f"Score de token ruim deveria ser < 60, recebido: {score}"
    print(f"✓ Token ruim recebeu score: {score}")

def test_process_token_analysis():
    """Testa o processamento de análise de token."""
    print("Testando process_token_analysis...")
    
    # Mock das funções de análise
    with patch('analyzer.analyze_on_chain_data') as mock_on_chain, \
         patch('analyzer.analyze_social_sentiment') as mock_social:
        
        # Configura os mocks
        mock_on_chain.return_value = {
            'account_exists': True,
            'is_honeypot': False,
            'liquidity_locked': True,
            'deployer_percentage': 10.0
        }
        
        mock_social.return_value = {
            'sentiment_score': 0.6,
            'tweet_count': 15,
            'social_activity': 'medium'
        }
        
        # Dados de teste
        token_data = {
            'tokenAddress': 'So11111111111111111111111111111111111111112',
            'poolAddress': 'pool123456789',
            'liquidityAmount': 1000000
        }
        
        result = process_token_analysis(token_data)
        
        assert result is not None, "Resultado não deveria ser None"
        assert result['tokenAddress'] == token_data['tokenAddress'], "Token address não confere"
        assert 'qualityScore' in result, "Quality score deveria estar presente"
        assert 'approved' in result, "Campo approved deveria estar presente"
        
        print(f"✓ Análise processada com score: {result['qualityScore']}")

def test_lambda_handler():
    """Testa o handler principal do Lambda."""
    print("Testando lambda_handler...")
    
    # Mock das funções
    with patch('analyzer.process_token_analysis') as mock_process, \
         patch('analyzer.send_to_trader_queue') as mock_send:
        
        # Configura os mocks
        mock_process.return_value = {
            'tokenAddress': 'So11111111111111111111111111111111111111112',
            'qualityScore': 75,
            'approved': True
        }
        
        # Evento de teste (SQS)
        test_event = {
            'Records': [
                {
                    'eventSource': 'aws:sqs',
                    'body': json.dumps({
                        'tokenAddress': 'So11111111111111111111111111111111111111112',
                        'poolAddress': 'pool123456789',
                        'liquidityAmount': 1000000
                    })
                }
            ]
        }
        
        result = lambda_handler(test_event, None)
        
        assert result['statusCode'] == 200, f"Status code esperado: 200, recebido: {result['statusCode']}"
        
        # Verifica se as funções foram chamadas
        mock_process.assert_called_once()
        mock_send.assert_called_once()
        
        print("✓ lambda_handler passou no teste")

def test_invalid_token():
    """Testa o processamento de tokens inválidos."""
    print("Testando tokens inválidos...")
    
    # Token sem endereço
    invalid_token = {
        'poolAddress': 'pool123456789',
        'liquidityAmount': 1000000
    }
    
    result = process_token_analysis(invalid_token)
    
    assert result is None, "Token inválido deveria retornar None"
    
    print("✓ Teste de tokens inválidos passou")

if __name__ == "__main__":
    print("Executando testes do Agente Analyzer...\n")
    
    try:
        test_calculate_quality_score()
        test_process_token_analysis()
        test_lambda_handler()
        test_invalid_token()
        
        print("\n✅ Todos os testes passaram!")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





