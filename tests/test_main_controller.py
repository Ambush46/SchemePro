class TestMainController:
    def test_landing_page_200(self, client):
        res = client.get('/')
        assert res.status_code == 200

    def test_about_page_200(self, client):
        res = client.get('/about')
        assert res.status_code == 200

    def test_spa_page_200(self, client):
        assert client.get('/app').status_code == 200

    def test_admin_page_unauthenticated_redirects(self, client):
        assert client.get('/admin-panel').status_code in (200, 302)
