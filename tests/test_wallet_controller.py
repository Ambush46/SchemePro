class TestWalletController:
    def test_get_balance_admin(self, admin_client):
        res = admin_client.get('/wallet/balance')
        assert res.status_code == 200 and res.get_json()['balance'] == 500.0

    def test_get_balance_new_user_is_zero(self, auth_client):
        res = auth_client.get('/wallet/balance')
        assert res.status_code == 200 and res.get_json()['balance'] == 0.0

    def test_topup_mpesa(self, auth_client):
        res = auth_client.post('/wallet/topup', json={
            'amount': 300.0,
            'method': 'mpesa',
            'reference': 'MPESA001',
        })
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True and data['new_balance'] == 300.0

    def test_topup_pesapal(self, auth_client):
        res = auth_client.post('/wallet/topup', json={
            'amount': 150.0,
            'method': 'pesapal',
            'reference': 'PESA001',
        })
        assert res.status_code == 200

    def test_topup_card(self, auth_client):
        res = auth_client.post('/wallet/topup', json={
            'amount': 200.0,
            'method': 'card',
            'reference': 'CARD001',
        })
        assert res.status_code == 200

    def test_topup_bank(self, auth_client):
        res = auth_client.post('/wallet/topup', json={
            'amount': 1000.0,
            'method': 'bank',
            'reference': 'BANK001',
        })
        assert res.status_code == 200

    def test_topup_invalid_method(self, auth_client):
        assert auth_client.post('/wallet/topup', json={'amount': 100.0, 'method': 'cash'}).status_code == 400

    def test_topup_zero_amount(self, auth_client):
        assert auth_client.post('/wallet/topup', json={'amount': 0, 'method': 'mpesa'}).status_code == 400

    def test_topup_negative_amount(self, auth_client):
        assert auth_client.post('/wallet/topup', json={'amount': -50, 'method': 'mpesa'}).status_code == 400

    def test_topup_accumulates(self, auth_client):
        auth_client.post('/wallet/topup', json={'amount': 100, 'method': 'mpesa', 'reference': 'A'})
        auth_client.post('/wallet/topup', json={'amount': 200, 'method': 'mpesa', 'reference': 'B'})
        bal = auth_client.get('/wallet/balance').get_json()['balance']
        assert bal == 300.0

    def test_wallet_history_after_topup(self, auth_client):
        auth_client.post('/wallet/topup', json={'amount': 100, 'method': 'mpesa', 'reference': 'X'})
        res = auth_client.get('/wallet/history')
        assert res.status_code == 200 and len(res.get_json()['data']) >= 1

    def test_balance_requires_auth(self, client):
        assert client.get('/wallet/balance').status_code in (401, 302)
