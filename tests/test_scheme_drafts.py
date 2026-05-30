from app.models.subject import Subject


class TestSchemeDrafts:
    def test_save_and_load_draft_across_sessions(self, auth_client, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
        payload = {
            'subject_id': physics.id,
            'step': 3,
            'params': {
                'grade': 'Form 3',
                'term': 1,
                'lessonsPerWeek': 5,
                'weeks': 10,
                'startWeek': 1,
                'doubleLesson': '',
                'startTopicId': str(physics.id),
                'startSubtopicId': None,
                'endTopicId': str(physics.id),
                'endSubtopicId': None,
            },
            'breaks': [{'week': 4, 'type': 'Midterm', 'wholeWeek': True, 'startLesson': 1}],
            'generated': [{'wk': '1', 'lsn': '1-5', 'topic': 'Measurements', 'subtopic': 'Length'}],
            'references': ['Saved reference'],
            'doc_id': 99,
        }

        save_res = auth_client.post('/scheme/drafts', json=payload)
        assert save_res.status_code == 200
        saved = save_res.get_json()['draft']
        assert saved['subject_id'] == physics.id
        assert saved['step'] == 3
        assert saved['payload']['params']['grade'] == 'Form 3'
        assert saved['payload']['breaks'][0]['type'] == 'Midterm'

        other_client = app.test_client()
        login = other_client.post('/auth/login', json={'username': 'testclient', 'password': 'TestPass1234'})
        assert login.status_code == 200

        load_res = other_client.get('/scheme/drafts')
        assert load_res.status_code == 200
        loaded = load_res.get_json()['draft']
        assert loaded['subject_id'] == physics.id
        assert loaded['step'] == 3
        assert loaded['payload']['generated'][0]['topic'] == 'Measurements'
        assert loaded['payload']['references'] == ['Saved reference']

    def test_drafts_require_auth(self, client):
        assert client.get('/scheme/drafts').status_code in (401, 302)
