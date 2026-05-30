import pytest
from app import create_app, db


@pytest.fixture(scope='function')
def app():
    test_app = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'WTF_CSRF_ENABLED': False,
    })
    with test_app.app_context():
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    client.post('/auth/register', json={
        'name': 'Test Teacher',
        'username': 'testclient',
        'email': 'teacher@test.com',
        'password': 'TestPass1234',
        'confirm_password': 'TestPass1234',
        'region': 'Nairobi',
    })
    return client


@pytest.fixture
def admin_client(client):
    client.post('/auth/login', json={'username': 'admin', 'password': 'Admin@1234'})
    return client


@pytest.fixture
def support_client(client, app):
    with app.app_context():
        from app.models.role import Role
        from app.models.user import User
        from app import bcrypt

        role = Role.query.filter_by(tag='support').first()
        if not role:
            pytest.skip('Support role not available')

        existing = User.query.filter_by(username='supportuser').first()
        if not existing:
            pw_hash = bcrypt.generate_password_hash('SupportPass123').decode('utf-8')
            support_user = User(
                name='Support Staff',
                username='supportuser',
                email='support@test.com',
                password=pw_hash,
                role_id=role.id,
            )
            db.session.add(support_user)
            db.session.commit()
        client.post('/auth/login', json={'username': 'supportuser', 'password': 'SupportPass123'})
    return client
