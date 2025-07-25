#!/usr/bin/env python3
"""Testes para o Agente Executor."""

import json
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from executor import Executor, lambda_handler


def test_execute_trade_paper_mode():
    """Verifica execução em modo paper."""
    print("Testando execute_trade em paper mode...")

    with patch('executor.MODE', 'paper'):
        exec_agent = Executor()
        # Evita logs em S3/Dynamo mocks
        with patch.object(exec_agent, 'log_price_series'):
            result = exec_agent.execute_trade(
                'token123',
                0.85,
                {'threshold': 0.7, 'amount': 10}
            )

    assert result['status'] == 'simulated_success'
    assert result['pnl'] != 0
    print("✓ execute_trade em paper mode OK")


def test_execute_trade_real_fallback():
    """Verifica fallback quando score abaixo do threshold."""
    print("Testando execute_trade fallback no modo real...")

    with patch('executor.MODE', 'real'):
        exec_agent = Executor()
        with patch.object(exec_agent, 'log_price_series'):
            result = exec_agent.execute_trade(
                'token456',
                0.4,
                {'threshold': 0.7, 'amount': 5}
            )

    assert result['status'] == 'fallback_applied'
    assert result['pnl'] == 0.0
    print("✓ execute_trade fallback OK")


def test_lambda_handler():
    """Teste simples do lambda_handler."""
    print("Testando lambda_handler do Executor...")
    with patch('executor.MODE', 'paper'):
        event = {
            'Records': [
                {
                    'body': json.dumps({
                        'token_address': 'token999',
                        'confidence_score': 0.9,
                        'trade_params': {'threshold': 0.7, 'amount': 10}
                    })
                }
            ]
        }
        response = lambda_handler(event, None)

    body = json.loads(response['body'])
    assert response['statusCode'] == 200
    assert body['status'] in ['simulated_success', 'executed_success']
    print("✓ lambda_handler OK")
