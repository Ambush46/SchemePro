from app.models.user import User


class TestAuthController:
    def test_register_success(self, client):
        res = client.post('/auth/register', json={
            'name': 'New Teacher',
            'username': 'newteacher',
            'email': 'new@test.com',
            'password': 'NewPass1234',
            'confirm_password': 'NewPass1234',
        })
        assert res.status_code == 201
        data = res.get_json()
        assert data['success'] is True and data['user']['username'] == 'newteacher'

    def test_register_creates_wallet_with_zero_balance(self, client, app):
        client.post('/auth/register', json={
            'name': 'Teacher W',
            'username': 'teacherw',
            'email': 'w@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        with app.app_context():
            u = User.query.filter_by(username='teacherw').first()
            assert u.wallet is not None and u.wallet.balance == 0.0

    def test_register_duplicate_username(self, client):
        for username in ['dup', 'dup']:
            client.post('/auth/register', json={
                'name': 'A',
                'username': username,
                'email': f'{username}x@test.com',
                'password': 'Pass12345',
                'confirm_password': 'Pass12345',
            })
        res = client.post('/auth/register', json={
            'name': 'B',
            'username': 'dup',
            'email': 'b@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        assert res.status_code == 409

    def test_register_duplicate_email(self, client):
        client.post('/auth/register', json={
            'name': 'A',
            'username': 'aaa',
            'email': 'same@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        res = client.post('/auth/register', json={
            'name': 'B',
            'username': 'bbb',
            'email': 'same@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        assert res.status_code == 409

    def test_register_password_mismatch(self, client):
        res = client.post('/auth/register', json={
            'name': 'A',
            'username': 'mmm',
            'email': 'mmm@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Different12',
        })
        assert res.status_code == 400
        assert 'match' in res.get_json()['error'].lower()

    def test_register_short_password(self, client):
        res = client.post('/auth/register', json={
            'name': 'A',
            'username': 'sss',
            'email': 'sss@test.com',
            'password': 'short',
            'confirm_password': 'short',
        })
        assert res.status_code == 400

    def test_register_missing_name(self, client):
        res = client.post('/auth/register', json={
            'name': '',
            'username': 'xxx',
            'email': 'xxx@test.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        assert res.status_code == 400

    def test_login_by_username(self, client):
        res = client.post('/auth/login', json={'username': 'admin', 'password': 'Admin@1234'})
        assert res.status_code == 200 and res.get_json()['success'] is True

    def test_login_by_email(self, client):
        res = client.post('/auth/login', json={
            'username': 'admin@schemepro.co.ke',
            'password': 'Admin@1234',
        })
        assert res.status_code == 200

    def test_login_wrong_password(self, client):
        res = client.post('/auth/login', json={'username': 'admin', 'password': 'wrong'})
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = client.post('/auth/login', json={'username': 'nobody', 'password': 'pass'})
        assert res.status_code == 401

    def test_me_authenticated(self, admin_client):
        res = admin_client.get('/auth/me')
        assert res.status_code == 200 and res.get_json()['user']['username'] == 'admin'

    def test_me_unauthenticated(self, client):
        res = client.get('/auth/me')
        assert res.status_code in (401, 302)

    def test_logout(self, admin_client):
        res = admin_client.post('/auth/logout')
        assert res.status_code == 200 and res.get_json()['success'] is True
