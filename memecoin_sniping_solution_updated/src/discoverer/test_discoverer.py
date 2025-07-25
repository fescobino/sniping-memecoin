#!/usr/bin/env python3
"""
Script de teste para o Agente Discoverer.
Este script simula o comportamento do Discoverer sem depender de AWS.
"""

import json
import os
import sys
from unittest.mock import Mock, patch
import types

# Create a stub boto3 module so patch works without the real dependency
sys.modules['boto3'] = types.SimpleNamespace(client=Mock())
solana_api = types.SimpleNamespace(Client=Mock())
solana_rpc = types.SimpleNamespace(api=solana_api)
sys.modules['solana'] = types.SimpleNamespace(rpc=solana_rpc)
sys.modules['solana.rpc'] = solana_rpc
sys.modules['solana.rpc.api'] = solana_api
sys.modules['requests'] = Mock()
sys.modules['aiohttp'] = Mock()
sys.modules['botocore'] = types.SimpleNamespace(exceptions=types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception))
sys.modules['botocore.exceptions'] = types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception)
sys.modules['numpy'] = Mock()

# Adiciona o diretório atual ao path para importar o módulo discoverer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock das dependências AWS para teste local
with patch('boto3.client'):
    from discoverer import process_token_event, lambda_handler

def test_process_token_event():
    """Testa o processamento de eventos de token."""
    print("Testando process_token_event...")
    
    # Evento de teste
    test_event = {
        'tokenAddress': 'So11111111111111111111111111111111111111112',
        'poolAddress': 'pool123456789',
        'liquidityAmount': 1000000,
        'timestamp': '2023-01-01T00:00:00Z',
        'signature': 'sig123456789',
        'type': 'TOKEN_MINT'
    }
    
    result = process_token_event(test_event)
    
    assert result is not None, "O resultado não deveria ser None"
    assert result['tokenAddress'] == test_event['tokenAddress'], "Token address não confere"
    assert result['eventType'] == test_event['type'], "Event type não confere"
    
    print("✓ process_token_event passou no teste")

def test_lambda_handler():
    """Testa o handler principal do Lambda."""
    print("Testando lambda_handler...")
    
    # Mock das funções AWS
    with patch('discoverer.get_secret') as mock_get_secret, \
         patch('discoverer.sqs') as mock_sqs, \
         patch('discoverer.send_to_sqs') as mock_send_to_sqs:
        
        # Configura os mocks
        mock_get_secret.return_value = {'apiKey': 'test_api_key'}
        mock_send_to_sqs.return_value = {'MessageId': 'test_message_id'}
        
        # Evento de teste (webhook)
        test_event = {
            'body': json.dumps([
                {
                    'tokenAddress': 'So11111111111111111111111111111111111111112',
                    'poolAddress': 'pool123456789',
                    'liquidityAmount': 1000000,
                    'timestamp': '2023-01-01T00:00:00Z',
                    'signature': 'sig123456789',
                    'type': 'TOKEN_MINT'
                }
            ])
        }
        
        result = lambda_handler(test_event, None)
        
        assert result['statusCode'] == 200, f"Status code esperado: 200, recebido: {result['statusCode']}"
        
        # Verifica se send_to_sqs foi chamado
        mock_send_to_sqs.assert_called_once()
        
        print("✓ lambda_handler passou no teste")

def test_invalid_token_event():
    """Testa o processamento de eventos inválidos."""
    print("Testando eventos inválidos...")
    
    # Evento sem tokenAddress
    invalid_event = {
        'poolAddress': 'pool123456789',
        'liquidityAmount': 1000000,
        'timestamp': '2023-01-01T00:00:00Z',
        'signature': 'sig123456789',
        'type': 'TOKEN_MINT'
    }
    
    result = process_token_event(invalid_event)
    
    assert result is None, "Evento inválido deveria retornar None"
    
    print("✓ Teste de eventos inválidos passou")

if __name__ == "__main__":
    print("Executando testes do Agente Discoverer...\n")
    
    try:
        test_process_token_event()
        test_lambda_handler()
        test_invalid_token_event()
        
        print("\n✅ Todos os testes passaram!")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        sys.exit(1)





