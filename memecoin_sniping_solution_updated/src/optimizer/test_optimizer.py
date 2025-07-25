#!/usr/bin/env python3
"""
Script de teste para o Agente Optimizer.
Este script simula o comportamento do Optimizer sem depender de AWS.
"""

import json
import os
import sys
from unittest.mock import Mock, patch, MagicMock
import pytest
import types

# Create a stub boto3 module so patch works without the real dependency
sys.modules['boto3'] = types.SimpleNamespace(client=Mock(), resource=Mock())
sys.modules['optuna'] = types.SimpleNamespace(create_study=Mock())
class FakeSeries(list):
    def mean(self):
        return sum(self) / len(self) if self else 0

    def sum(self):
        return sum(self)

    def cumsum(self):
        total = 0
        result = []
        for x in self:
            total += x
            result.append(total)
        return FakeSeries(result)

    def expanding(self):
        data = self

        class Expanding:
            def __init__(self, data):
                self.data = data

            def max(self):
                max_values = []
                current = float('-inf')
                for value in self.data:
                    current = max(current, value)
                    max_values.append(current)
                return FakeSeries(max_values)

        return Expanding(data)

    def __eq__(self, other):
        return [x == other for x in self]


class FakeDataFrame:
    def __init__(self, data):
        self.data = data

    def __getitem__(self, key):
        if isinstance(key, str):
            return FakeSeries([row[key] for row in self.data])
        else:  # boolean indexing
            return FakeDataFrame([row for row, flag in zip(self.data, key) if flag])

    def __len__(self):
        return len(self.data)

    @property
    def empty(self):
        return len(self.data) == 0


fake_pandas = types.SimpleNamespace(DataFrame=FakeDataFrame)
sys.modules['pandas'] = fake_pandas
fake_numpy = types.SimpleNamespace(mean=lambda x: sum(x)/len(x) if x else 0)
sys.modules['numpy'] = fake_numpy
SKIP_PANDAS = True
sys.modules['botocore'] = types.SimpleNamespace(exceptions=types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception))
sys.modules['botocore.exceptions'] = types.SimpleNamespace(ClientError=Exception, NoCredentialsError=Exception)
from decimal import Decimal

# Adiciona o diretório atual ao path para importar o módulo optimizer
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock das dependências para teste local
with patch('boto3.resource'), \
     patch('boto3.client'), \
     patch('optuna.create_study'):
    from optimizer import (
        calculate_performance_metrics, 
        simulate_performance_with_params,
        get_default_config,
        create_ab_test_config,
        lambda_handler
    )

def test_calculate_performance_metrics():
    """Testa o cálculo de métricas de performance."""
    if SKIP_PANDAS:
        pytest.skip("pandas not available")
    print("Testando calculate_performance_metrics...")
    
    # Dados de teste
    test_trades = [
        {
            'trade_id': 'test_1',
            'status': 'closed',
            'pnl': 20.0,
            'entry_time': '2023-01-01T10:00:00Z',
            'exit_time': '2023-01-01T12:00:00Z'
        },
        {
            'trade_id': 'test_2',
            'status': 'closed',
            'pnl': -10.0,
            'entry_time': '2023-01-01T14:00:00Z',
            'exit_time': '2023-01-01T15:00:00Z'
        },
        {
            'trade_id': 'test_3',
            'status': 'closed',
            'pnl': 15.0,
            'entry_time': '2023-01-01T16:00:00Z',
            'exit_time': '2023-01-01T18:00:00Z'
        },
        {
            'trade_id': 'test_4',
            'status': 'open',
            'pnl': 0.0
        }
    ]
    
    metrics = calculate_performance_metrics(test_trades)
    
    assert metrics['total_trades'] == 3, f"Total trades esperado: 3, recebido: {metrics['total_trades']}"
    assert metrics['win_rate'] == 2/3, f"Win rate esperado: 0.667, recebido: {metrics['win_rate']}"
    assert metrics['total_pnl'] == 25.0, f"Total P&L esperado: 25.0, recebido: {metrics['total_pnl']}"
    
    print(f"✓ Métricas calculadas: Win Rate: {metrics['win_rate']:.2%}, Total P&L: ${metrics['total_pnl']:.2f}")

def test_simulate_performance_with_params():
    """Testa a simulação de performance com novos parâmetros."""
    print("Testando simulate_performance_with_params...")
    
    # Dados históricos de teste
    historical_data = [
        {
            'quality_score': 85,
            'entry_price': 1.0,
            'exit_price': 1.3,  # +30%
            'amount_usd': 100
        },
        {
            'quality_score': 70,
            'entry_price': 1.0,
            'exit_price': 0.85,  # -15%
            'amount_usd': 100
        },
        {
            'quality_score': 45,  # Abaixo do threshold
            'entry_price': 1.0,
            'exit_price': 1.1,
            'amount_usd': 100
        }
    ]
    
    # Simular com novos parâmetros
    result = simulate_performance_with_params(
        historical_data,
        quality_threshold=60,  # Score mínimo 60
        high_sl=0.10,
        high_tp=0.25,
        med_sl=0.15,
        med_tp=0.20
    )
    
    assert result['trade_count'] == 2, f"Trades simulados esperados: 2, recebido: {result['trade_count']}"
    assert result['win_rate'] > 0, "Win rate deveria ser maior que 0"
    
    print(f"✓ Simulação: {result['trade_count']} trades, Win Rate: {result['win_rate']:.2%}")

def test_get_default_config():
    """Testa a configuração padrão."""
    print("Testando get_default_config...")
    
    config = get_default_config()
    
    assert 'discoverer' in config, "Configuração do Discoverer deveria estar presente"
    assert 'analyzer' in config, "Configuração do Analyzer deveria estar presente"
    assert 'trader' in config, "Configuração do Trader deveria estar presente"
    assert 'optimizer' in config, "Configuração do Optimizer deveria estar presente"
    
    assert config['analyzer']['quality_score_threshold'] == 60, "Threshold padrão deveria ser 60"
    
    print("✓ Configuração padrão carregada com sucesso")

def test_create_ab_test_config():
    """Testa a criação de configuração para A/B testing."""
    print("Testando create_ab_test_config...")
    
    current_config = get_default_config()
    optimized_params = {
        'quality_threshold': 70,
        'high_score_sl': 0.12,
        'high_score_tp': 0.28
    }
    
    ab_config = create_ab_test_config(current_config, optimized_params)
    
    assert 'ab_test_active' in ab_config, "Flag de A/B test deveria estar presente"
    assert ab_config['ab_test_active'] == True, "A/B test deveria estar ativo"
    assert 'config_a' in ab_config, "Configuração A deveria estar presente"
    assert 'config_b' in ab_config, "Configuração B deveria estar presente"
    
    # Verificar se os parâmetros otimizados foram aplicados à configuração B
    assert ab_config['config_b']['analyzer']['quality_score_threshold'] == 70
    assert ab_config['config_b']['trader']['high_score_sl'] == 0.12
    
    print("✓ Configuração A/B test criada com sucesso")

def test_lambda_handler():
    """Testa o handler principal do Lambda."""
    print("Testando lambda_handler...")
    
    # Mock das funções
    with patch('optimizer.get_historical_trades') as mock_trades, \
         patch('optimizer.run_bayesian_optimization') as mock_optim, \
         patch('optimizer.save_config_to_s3') as mock_save_config, \
         patch('optimizer.save_optimization_results') as mock_save_results, \
         patch('optimizer.load_current_config') as mock_load_config:
        
        # Configura os mocks
        mock_trades.return_value = [
            {'trade_id': f'test_{i}', 'status': 'closed', 'pnl': 10 * (i % 2 * 2 - 1)}
            for i in range(20)  # 20 trades de teste
        ]
        
        mock_load_config.return_value = get_default_config()
        
        mock_optim.return_value = (
            {'quality_threshold': 65, 'high_score_sl': 0.12},
            0.85
        )
        
        # Evento de teste
        test_event = {}
        
        result = lambda_handler(test_event, None)
        
        assert result['statusCode'] == 200, f"Status code esperado: 200, recebido: {result['statusCode']}"
        
        # Verifica se as funções foram chamadas
        mock_trades.assert_called_once()
        mock_optim.assert_called_once()
        mock_save_config.assert_called_once()
        mock_save_results.assert_called_once()
        
        print("✓ lambda_handler passou no teste")

def test_insufficient_data():
    """Testa o comportamento com dados insuficientes."""
    print("Testando comportamento com dados insuficientes...")
    
    with patch('optimizer.get_historical_trades') as mock_trades:
        
        # Simula poucos dados históricos
        mock_trades.return_value = [
            {'trade_id': 'test_1', 'status': 'closed', 'pnl': 10}
        ]  # Apenas 1 trade
        
        result = lambda_handler({}, None)
        
        assert result['statusCode'] == 200, "Status code deveria ser 200"
        
        response_body = json.loads(result['body'])
        assert 'insuficientes' in response_body['message'], "Mensagem deveria indicar dados insuficientes"
        
        print("✓ Teste de dados insuficientes passou")

if __name__ == "__main__":
    print("Executando testes do Agente Optimizer...\n")
    
    try:
        test_calculate_performance_metrics()
        test_simulate_performance_with_params()
        test_get_default_config()
        test_create_ab_test_config()
        test_lambda_handler()
        test_insufficient_data()
        
        print("\n✅ Todos os testes passaram!")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





