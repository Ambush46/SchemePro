from app import db, bcrypt
from app.models.role import Role
from app.models.user import User
from app.models.subject import Subject
from app.models.curriculum import Topic


class TestAdminController:
    def test_overview_requires_admin(self, auth_client):
        assert auth_client.get('/admin-panel/overview').status_code == 403

    def test_overview_returns_all_fields(self, admin_client):
        res = admin_client.get('/admin-panel/overview')
        assert res.status_code == 200
        d = res.get_json()['data']
        for field in [
            'total_users',
            'active_users',
            'total_docs_generated',
            'actual_revenue',
            'potential_revenue',
            'total_deposited',
            'role_counts',
        ]:
            assert field in d, f'Missing field: {field}'

    def test_list_users_requires_admin(self, auth_client):
        assert auth_client.get('/admin-panel/users').status_code == 403

    def test_list_users_as_admin(self, admin_client):
        res = admin_client.get('/admin-panel/users')
        assert res.status_code == 200 and len(res.get_json()['data']) >= 1

    def test_support_cannot_view_admin_or_superuser(self, support_client):
        res = support_client.get('/admin-panel/users')
        assert res.status_code == 200
        data = res.get_json()['data']
        assert all(u['role'] not in ('admin', 'superuser') for u in data)

    def test_support_cannot_disable_support_or_higher(self, support_client, app):
        with app.app_context():
            from app.models.user import User
            support_role = User.query.filter_by(username='supportuser').first().role
            other_support = User(
                name='Other Support',
                username='support2',
                email='support2@test.com',
                password=User.query.filter_by(username='supportuser').first().password,
                role_id=support_role.id,
            )
            db.session.add(other_support)
            db.session.commit()
            support_id = other_support.id
            superuser_id = User.query.filter_by(username='admin').first().id

        res_support = support_client.post(f'/admin-panel/users/{support_id}/disable')
        res_superuser = support_client.post(f'/admin-panel/users/{superuser_id}/disable')
        assert res_support.status_code == 403
        assert res_superuser.status_code == 403

    def test_disable_user(self, admin_client, app):
        with app.app_context():
            role = Role.query.filter_by(tag='client').first()
            u = User(
                name='Test Teacher',
                username='testclient',
                email='teacher@test.com',
                password=bcrypt.generate_password_hash('TestPass1234').decode('utf-8'),
                role_id=role.id,
            )
            db.session.add(u)
            db.session.commit()
            uid = u.id
        res = admin_client.post(f'/admin-panel/users/{uid}/disable')
        assert res.status_code == 200
        with app.app_context():
            db.session.expire_all()
            assert db.session.get(User, uid).is_active is False

    def test_enable_user(self, admin_client, auth_client, app):
        with app.app_context():
            u = User.query.filter_by(username='testclient').first()
            u.active = False
            db.session.commit()
            uid = u.id
        admin_client.post(f'/admin-panel/users/{uid}/enable')
        with app.app_context():
            db.session.expire_all()
            assert db.session.get(User, uid).is_active is True

    def test_cannot_disable_own_account(self, admin_client, app):
        with app.app_context():
            uid = User.query.filter_by(username='admin').first().id
        assert admin_client.post(f'/admin-panel/users/{uid}/disable').status_code == 400

    def test_revenue_daily(self, admin_client):
        res = admin_client.get('/admin-panel/revenue/daily?days=7')
        assert res.status_code == 200 and 'data' in res.get_json()

    def test_transactions_paginated(self, admin_client):
        res = admin_client.get('/admin-panel/transactions?page=1&per_page=10')
        assert res.status_code == 200
        data = res.get_json()
        assert 'data' in data and 'total' in data and 'pages' in data

    def test_doc_stats(self, admin_client):
        res = admin_client.get('/admin-panel/doc-stats')
        assert res.status_code == 200 and 'data' in res.get_json()

    def test_user_activity(self, admin_client, app):
        with app.app_context():
            uid = User.query.filter_by(username='admin').first().id
        res = admin_client.get(f'/admin-panel/users/{uid}/activity')
        assert res.status_code == 200

    def test_revenue_increases_after_download(self, admin_client, app):
        initial = admin_client.get('/admin-panel/overview').get_json()['data']['actual_revenue']
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
            topics = Topic.query.filter_by(subject_id=physics.id).order_by(Topic.id).all()
        gen = admin_client.post('/scheme/generate', json={
            'subject_id': physics.id,
            'grade': 'Form 3',
            'term': 1,
            'lessons_per_week': 5,
            'weeks': 8,
            'start_week': 1,
            'double_lesson': '',
            'start_topic_id': topics[0].id,
            'start_subtopic_id': None,
            'end_topic_id': topics[-1].id,
            'end_subtopic_id': None,
            'breaks': [],
        }).get_json()
        admin_client.post('/scheme/download', json={
            'doc_id': gen['doc_id'],
            'doc_type': 'pdf',
            'rows': gen['rows'],
            'meta': {
                'subject': 'Physics',
                'grade': 'Form 3',
                'term': 1,
                'curriculum_system': '844',
                'references': [],
            },
        })
        after = admin_client.get('/admin-panel/overview').get_json()['data']['actual_revenue']
        assert after == initial + 30.0
