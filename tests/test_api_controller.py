from app.models.level import Level
from app.models.subject import Subject
from app.models.curriculum import Topic


class TestAPIController:
    def test_get_curriculum_systems(self, client):
        res = client.get('/api/v1/curriculum-systems')
        assert res.status_code == 200
        data = res.get_json()['data']
        assert len(data) >= 2
        system_tags = [s['tag'] for s in data]
        assert '844' in system_tags
        assert 'CBC' in system_tags

    def test_get_levels(self, client):
        res = client.get('/api/v1/levels')
        assert res.status_code == 200
        assert len(res.get_json()['data']) >= 3

    def test_get_subjects(self, client):
        res = client.get('/api/v1/subjects')
        assert res.status_code == 200
        assert len(res.get_json()['data']) >= 15

    def test_get_subjects_filtered_by_level(self, client, app):
        with app.app_context():
            senior = Level.query.filter_by(tag='senior').first()
        res = client.get(f'/api/v1/subjects?level_id={senior.id}')
        subjects = res.get_json()['data']
        assert all(s['level_id'] == senior.id for s in subjects)
        assert len(subjects) >= 5

    def test_get_topics_requires_subject_id(self, client):
        assert client.get('/api/v1/topics').status_code == 400

    def test_get_topics_for_physics(self, client, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
        res = client.get(f'/api/v1/topics?subject_id={physics.id}')
        assert res.status_code == 200 and len(res.get_json()['data']) >= 4

    def test_get_subtopics(self, client, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
            topic = Topic.query.filter_by(subject_id=physics.id).first()
        res = client.get(f'/api/v1/subtopics?topic_id={topic.id}')
        assert res.status_code == 200 and len(res.get_json()['data']) >= 1

    def test_get_pricing(self, client):
        res = client.get('/api/v1/pricing')
        d = res.get_json()['data']
        assert d['pdf']['price'] == 30.0
        assert d['docx']['price'] == 50.0
        assert d['zip']['price'] == 70.0

    def test_update_pricing_requires_admin(self, auth_client):
        assert auth_client.put('/api/v1/pricing', json={'pdf': 25}).status_code == 403

    def test_update_pricing_as_admin(self, admin_client):
        res = admin_client.put('/api/v1/pricing', json={'pdf': 25.0, 'docx': 45.0, 'zip': 60.0})
        assert res.status_code == 200
        assert res.get_json()['data']['pdf']['price'] == 25.0

    def test_create_topic_requires_admin(self, auth_client, app):
        with app.app_context():
            p = Subject.query.filter_by(tag='physics_senior').first()
        assert auth_client.post('/api/v1/topics', json={'name': 'Radioactivity', 'subject_id': p.id}).status_code == 403

    def test_create_topic_as_admin(self, admin_client, app):
        with app.app_context():
            p = Subject.query.filter_by(tag='physics_senior').first()
        res = admin_client.post('/api/v1/topics', json={'name': 'Radioactivity', 'subject_id': p.id})
        assert res.status_code == 201 and res.get_json()['data']['name'] == 'Radioactivity'

    def test_delete_topic_as_admin(self, admin_client, app):
        with app.app_context():
            p = Subject.query.filter_by(tag='physics_senior').first()
        t_res = admin_client.post('/api/v1/topics', json={'name': 'ToDelete', 'subject_id': p.id})
        tid = t_res.get_json()['data']['id']
        res = admin_client.delete(f'/api/v1/topics/{tid}')
        assert res.status_code == 200

    def test_create_subject_as_admin(self, admin_client, app):
        with app.app_context():
            senior = Level.query.filter_by(tag='senior').first()
        res = admin_client.post('/api/v1/subjects', json={
            'tag': 'agriculture_senior',
            'name': 'Agriculture',
            'level_id': senior.id,
            'curriculum_system': '844',
        })
        assert res.status_code == 201

    def test_create_level_as_admin(self, admin_client):
        res = admin_client.post('/api/v1/levels', json={'name': 'TVET', 'tag': 'tvet'})
        assert res.status_code == 201

    def test_create_level_duplicate_tag(self, admin_client):
        res = admin_client.post('/api/v1/levels', json={'name': 'Dup', 'tag': 'senior'})
        assert res.status_code == 409

    def test_create_sublevel_as_admin(self, admin_client, app):
        with app.app_context():
            senior = Level.query.filter_by(tag='senior').first()
        res = admin_client.post('/api/v1/sublevels', json={'name': 'Form 3', 'tag': 'form_3', 'level_id': senior.id})
        assert res.status_code == 201
        assert res.get_json()['data']['name'] == 'Form 3'
