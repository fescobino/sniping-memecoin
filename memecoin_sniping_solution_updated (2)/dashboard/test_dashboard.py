#!/usr/bin/env python3
"""
Script de teste para o Dashboard Flask.
Este script testa as rotas da API sem depender de AWS.
"""

import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Adiciona o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_dashboard_routes():
    """Testa as rotas do dashboard."""
    print("🧪 Testando rotas do dashboard...")
    
    # Mock das dependências AWS
    with patch('boto3.resource') as mock_dynamodb, \
         patch('boto3.client') as mock_s3, \
         patch('src.routes.trading.dynamodb'), \
         patch('src.routes.trading.s3'), \
         patch('src.routes.notifications.secrets_manager'):
        
        # Configurar mocks
        mock_table = Mock()
        mock_table.scan.return_value = {
            'Items': [
                {
                    'trade_id': 'test_1',
                    'status': 'closed',
                    'pnl': 25.50,
                    'entry_price': 1.0,
                    'exit_price': 1.255,
                    'quality_score': 75,
                    'is_dry_run': True,
                    'entry_time': '2023-01-01T10:00:00Z',
                    'exit_time': '2023-01-01T12:00:00Z'
                },
                {
                    'trade_id': 'test_2',
                    'status': 'open',
                    'entry_price': 1.0,
                    'quality_score': 65,
                    'is_dry_run': False,
                    'entry_time': '2023-01-01T14:00:00Z'
                }
            ]
        }
        
        mock_dynamodb.return_value.Table.return_value = mock_table
        
        # Importar app após configurar mocks
        from src.main import app
        
        # Configurar cliente de teste
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Teste 1: Página principal
        print("📄 Testando página principal...")
        response = client.get('/')
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        assert b'Memecoin Sniping Dashboard' in response.data, "Título não encontrado na página"
        print("✅ Página principal OK")
        
        # Teste 2: API de métricas
        print("📊 Testando API de métricas...")
        response = client.get('/api/trading/metrics')
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        
        data = json.loads(response.data)
        assert 'total_trades' in data, "Campo total_trades não encontrado"
        assert 'win_rate' in data, "Campo win_rate não encontrado"
        assert 'total_pnl' in data, "Campo total_pnl não encontrado"
        print("✅ API de métricas OK")
        
        # Teste 3: API de trades
        print("📋 Testando API de trades...")
        response = client.get('/api/trading/trades')
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        
        trades = json.loads(response.data)
        assert isinstance(trades, list), "Resposta deveria ser uma lista"
        # Lista pode estar vazia em ambiente de teste
        print("✅ API de trades OK")
        
        # Teste 4: API de performance
        print("📈 Testando API de performance...")
        response = client.get('/api/trading/performance')
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        
        performance = json.loads(response.data)
        assert isinstance(performance, list), "Resposta deveria ser uma lista"
        print("✅ API de performance OK")
        
        # Teste 5: API de status
        print("🔍 Testando API de status...")
        response = client.get('/api/trading/status')
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        
        status = json.loads(response.data)
        assert 'system_status' in status, "Campo system_status não encontrado"
        print("✅ API de status OK")
        
        print("\n🎉 Todos os testes do dashboard passaram!")
        return True

def test_notification_routes():
    """Testa as rotas de notificação."""
    print("\n🔔 Testando rotas de notificação...")
    
    with patch('src.routes.notifications.secrets_manager') as mock_secrets, \
         patch('src.routes.notifications.requests') as mock_requests:
        
        # Configurar mocks
        mock_secrets.get_secret_value.return_value = {
            'SecretString': '{"botToken": "test_token"}'
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_requests.post.return_value = mock_response
        
        from src.main import app
        app.config['TESTING'] = True
        client = app.test_client()
        
        # Teste de envio de notificação
        print("📱 Testando envio de notificação...")
        response = client.post('/api/notifications/telegram/send', 
                             json={
                                 'chat_id': '@test_channel',
                                 'message': 'Teste de notificação'
                             })
        
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        print("✅ Envio de notificação OK")
        
        # Teste de alerta de trade
        print("💰 Testando alerta de trade...")
        response = client.post('/api/notifications/alerts/trade',
                             json={
                                 'trade_data': {
                                     'trade_id': 'test_123',
                                     'token_address': 'So11111111111111111111111111111111111111112',
                                     'amount_usd': 100,
                                     'quality_score': 75,
                                     'entry_price': 1.0,
                                     'is_dry_run': True
                                 },
                                 'alert_type': 'new_trade'
                             })
        
        assert response.status_code == 200, f"Status esperado: 200, recebido: {response.status_code}"
        print("✅ Alerta de trade OK")
        
        print("🎉 Todos os testes de notificação passaram!")
        return True

def test_mock_data():
    """Testa com dados simulados para demonstração."""
    print("\n🎭 Testando com dados simulados...")
    
    # Simular dados de trading
    mock_trades = [
        {
            'trade_id': f'demo_{i}',
            'status': 'closed' if i % 3 == 0 else 'open',
            'pnl': (i * 10 - 50) if i % 3 == 0 else 0,
            'entry_price': 1.0 + (i * 0.1),
            'exit_price': 1.0 + (i * 0.15) if i % 3 == 0 else None,
            'quality_score': 50 + (i * 5),
            'is_dry_run': i % 2 == 0,
            'entry_time': f'2023-01-{i+1:02d}T10:00:00Z',
            'exit_time': f'2023-01-{i+1:02d}T12:00:00Z' if i % 3 == 0 else None,
            'token_address': f'So{i:>46}',
            'amount_usd': 100 + (i * 10)
        }
        for i in range(10)
    ]
    
    # Calcular métricas simuladas
    closed_trades = [t for t in mock_trades if t['status'] == 'closed']
    total_pnl = sum(t['pnl'] for t in closed_trades)
    win_rate = len([t for t in closed_trades if t['pnl'] > 0]) / len(closed_trades) if closed_trades else 0
    
    print(f"📊 Dados simulados gerados:")
    print(f"   - Total de trades: {len(mock_trades)}")
    print(f"   - Trades fechados: {len(closed_trades)}")
    print(f"   - P&L total: ${total_pnl:.2f}")
    print(f"   - Win rate: {win_rate:.1%}")
    
    print("✅ Dados simulados OK")
    return True

if __name__ == "__main__":
    print("🚀 Iniciando testes do Dashboard...")
    
    try:
        # Executar todos os testes
        test_dashboard_routes()
        test_notification_routes()
        test_mock_data()
        
        print("\n🎉 Todos os testes passaram com sucesso!")
        print("\n📋 Resumo dos testes:")
        print("   ✅ Rotas do dashboard")
        print("   ✅ Sistema de notificações")
        print("   ✅ Dados simulados")
        print("\n🌐 Para testar localmente:")
        print("   cd dashboard")
        print("   source venv/bin/activate")
        print("   python src/main.py")
        print("   Acesse: http://localhost:5000")
        
    except Exception as e:
        print(f"\n❌ Erro nos testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)





