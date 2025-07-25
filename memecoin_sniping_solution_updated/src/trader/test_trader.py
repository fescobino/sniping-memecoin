#!/usr/bin/env python3
"""
Script de teste para o Agente Trader.
Este script simula o comportamento do Trader sem depender de AWS ou blockchain real.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal

# Adiciona o diretório atual ao path para importar o módulo trader
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock das dependências para teste local
with patch('boto3.client'), \
     patch('boto3.resource'), \
     patch('solana.rpc.api.Client'), \
     patch('solders.keypair.Keypair'):
    from trader import calculate_trade_parameters, process_approved_token, lambda_handler

def test_calculate_trade_parameters():
    """Testa o cálculo dos parâmetros de trade."""
    print("Testando calculate_trade_parameters...")
    
    # Teste com score alto
    high_score_params = calculate_trade_parameters(85, 1.0)
    
    assert high_score_params is not None, "Parâmetros não deveriam ser None"
    assert high_score_params['stop_loss_pct'] == 0.10, "Stop loss para score alto deveria ser 10%"
    assert high_score_params['take_profit_pct'] == 0.30, "Take profit para score alto deveria ser 30%"
    assert high_score_params['position_size_pct'] == 0.15, "Position size para score alto deveria ser 15%"
    
    print(f"✓ Score alto (85): SL={high_score_params['stop_loss_pct']:.0%}, TP={high_score_params['take_profit_pct']:.0%}")
    
    # Teste com score médio
    medium_score_params = calculate_trade_parameters(65, 1.0)
    
    assert medium_score_params['stop_loss_pct'] == 0.15, "Stop loss para score médio deveria ser 15%"
    assert medium_score_params['take_profit_pct'] == 0.25, "Take profit para score médio deveria ser 25%"
    
    print(f"✓ Score médio (65): SL={medium_score_params['stop_loss_pct']:.0%}, TP={medium_score_params['take_profit_pct']:.0%}")
    
    # Teste com score baixo
    low_score_params = calculate_trade_parameters(45, 1.0)
    
    assert low_score_params['stop_loss_pct'] == 0.20, "Stop loss para score baixo deveria ser 20%"
    assert low_score_params['take_profit_pct'] == 0.20, "Take profit para score baixo deveria ser 20%"
    
    print(f"✓ Score baixo (45): SL={low_score_params['stop_loss_pct']:.0%}, TP={low_score_params['take_profit_pct']:.0%}")

def test_process_approved_token():
    """Testa o processamento de token aprovado."""
    print("Testando process_approved_token...")
    
    # Mock das funções
    with patch('trader.get_token_price') as mock_price, \
         patch('trader.get_solana_keypair') as mock_keypair, \
         patch('trader.execute_buy_order') as mock_buy, \
         patch('trader.save_trade_to_db') as mock_save:
        
        # Configura os mocks
        mock_price.return_value = 0.001  # $0.001 por token
        mock_keypair.return_value = Mock()
        mock_buy.return_value = {
            'success': True,
            'transaction_signature': 'test_signature_123',
            'amount_tokens': 50000,  # 50k tokens por $50
            'price_per_token': 0.001,
            'slippage': 0.01
        }
        
        # Dados de teste
        analysis_data = {
            'tokenAddress': 'So11111111111111111111111111111111111111112',
            'qualityScore': 75,
            'approved': True
        }
        
        result = process_approved_token(analysis_data)
        
        assert result is not None, "Resultado não deveria ser None"
        assert result['token_address'] == analysis_data['tokenAddress'], "Token address não confere"
        assert result['status'] == 'open', "Status deveria ser 'open'"
        assert 'trade_id' in result, "Trade ID deveria estar presente"
        
        # Verifica se as funções foram chamadas
        mock_price.assert_called()
        mock_buy.assert_called_once()
        mock_save.assert_called_once()
        
        print(f"✓ Trade criado com ID: {result['trade_id']}")

def test_lambda_handler_sqs():
    """Testa o handler do Lambda com evento SQS."""
    print("Testando lambda_handler com SQS...")
    
    # Mock das funções
    with patch('trader.process_approved_token') as mock_process:
        
        mock_process.return_value = {
            'trade_id': 'test_trade_123',
            'token_address': 'So11111111111111111111111111111111111111112',
            'status': 'open'
        }
        
        # Evento de teste (SQS)
        test_event = {
            'Records': [
                {
                    'eventSource': 'aws:sqs',
                    'body': json.dumps({
                        'tokenAddress': 'So11111111111111111111111111111111111111112',
                        'qualityScore': 80,
                        'approved': True
                    })
                }
            ]
        }
        
        result = lambda_handler(test_event, None)
        
        assert result['statusCode'] == 200, f"Status code esperado: 200, recebido: {result['statusCode']}"
        
        # Verifica se process_approved_token foi chamado
        mock_process.assert_called_once()
        
        print("✓ lambda_handler com SQS passou no teste")

def test_lambda_handler_timer():
    """Testa o handler do Lambda com evento de timer."""
    print("Testando lambda_handler com timer...")
    
    # Mock da tabela DynamoDB
    mock_table = Mock()
    mock_table.scan.return_value = {
        'Items': [
            {
                'trade_id': 'test_trade_123',
                'token_address': 'So11111111111111111111111111111111111111112',
                'status': 'open'
            }
        ]
    }
    
    with patch('trader.trader_table', mock_table), \
         patch('trader.monitor_position') as mock_monitor:
        
        # Evento de teste (timer)
        test_event = {
            'source': 'aws.events'
        }
        
        result = lambda_handler(test_event, None)
        
        assert result['statusCode'] == 200, f"Status code esperado: 200, recebido: {result['statusCode']}"
        
        # Verifica se monitor_position foi chamado
        mock_monitor.assert_called_once_with('test_trade_123')
        
        print("✓ lambda_handler com timer passou no teste")

def test_price_unavailable():
    """Testa o comportamento quando o preço não está disponível."""
    print("Testando comportamento com preço indisponível...")
    
    with patch('trader.get_token_price') as mock_price:
        
        # Simula preço indisponível
        mock_price.return_value = 0
        
        analysis_data = {
            'tokenAddress': 'InvalidToken123',
            'qualityScore': 75,
            'approved': True
        }
        
        result = process_approved_token(analysis_data)
        
        assert result is None, "Resultado deveria ser None quando preço não disponível"
        
        print("✓ Teste de preço indisponível passou")

if __name__ == "__main__":
    print("Executando testes do Agente Trader...\n")
    
    try:
        test_calculate_trade_parameters()
        test_process_approved_token()
        test_lambda_handler_sqs()
        test_lambda_handler_timer()
        test_price_unavailable()
        
        print("\n✅ Todos os testes passaram!")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





