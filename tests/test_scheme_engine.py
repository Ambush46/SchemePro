from app.models.subject import Subject
from app.models.curriculum import Topic
from app.models.pricing import GeneratedDocument


class TestSchemeEngine:
    def _base_payload(self, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
            topics = Topic.query.filter_by(subject_id=physics.id).order_by(Topic.order, Topic.id).all()
            return {
                'subject_id': physics.id,
                'grade': 'Form 3',
                'term': 1,
                'lessons_per_week': 5,
                'weeks': 10,
                'start_week': 1,
                'double_lesson': '',
                'start_topic_id': topics[0].id,
                'start_subtopic_id': None,
                'end_topic_id': topics[-1].id,
                'end_subtopic_id': None,
                'breaks': [],
            }

    def test_generate_returns_rows(self, admin_client, app):
        payload = self._base_payload(app)
        res = admin_client.post('/scheme/generate', json=payload)
        assert res.status_code == 200
        data = res.get_json()
        assert data['success'] is True
        assert len(data['rows']) > 0
        assert 'doc_id' in data
        assert 'references' in data

    def test_generate_844_rows_have_correct_keys(self, admin_client, app):
        payload = self._base_payload(app)
        rows = admin_client.post('/scheme/generate', json=payload).get_json()['rows']
        content = [r for r in rows if r.get('topic') and 'BREAK' not in r['topic'].upper()]
        assert content
        for k in ['wk', 'lsn', 'topic', 'subtopic', 'objectives', 'activities', 'aids', 'reference', 'remarks']:
            assert k in content[0], f'Missing key: {k}'

    def test_generate_cbc_rows_have_correct_keys(self, admin_client, app):
        with app.app_context():
            sc = Subject.query.filter_by(tag='sci_junior').first()
            topics = Topic.query.filter_by(subject_id=sc.id).order_by(Topic.order, Topic.id).all()
        payload = {
            'subject_id': sc.id,
            'grade': 'Grade 8',
            'term': 1,
            'lessons_per_week': 4,
            'weeks': 10,
            'start_week': 1,
            'double_lesson': '',
            'start_topic_id': topics[0].id,
            'start_subtopic_id': None,
            'end_topic_id': topics[-1].id,
            'end_subtopic_id': None,
            'breaks': [],
        }
        rows = admin_client.post('/scheme/generate', json=payload).get_json()['rows']
        content = [r for r in rows if r.get('strand') and 'BREAK' not in r['strand'].upper()]
        assert content
        for k in ['wk', 'lsn', 'strand', 'substrand', 'outcomes', 'inquiry', 'experiences', 'resources', 'assessment', 'refl']:
            assert k in content[0], f'Missing CBC key: {k}'

    def test_generate_with_whole_week_break(self, admin_client, app):
        payload = self._base_payload(app)
        payload['breaks'] = [{'week': 4, 'type': 'Midterm', 'whole_week': True, 'start_lesson': 1}]
        rows = admin_client.post('/scheme/generate', json=payload).get_json()['rows']
        break_rows = [r for r in rows if r.get('topic', '').upper() == 'BREAK' and r.get('wk') == '4']
        assert len(break_rows) >= 1

    def test_generate_with_partial_break(self, admin_client, app):
        payload = self._base_payload(app)
        payload['breaks'] = [{'week': 2, 'type': 'CAT / Test', 'whole_week': False, 'start_lesson': 4}]
        rows = admin_client.post('/scheme/generate', json=payload).get_json()['rows']
        w2 = [r for r in rows if r.get('wk') == '2']
        assert w2, 'Week 2 content row must exist'
        pbrk = [
            r for r in rows
            if r.get('wk') == '' and r.get('topic', '').upper() == 'BREAK' and r.get('lsn') == '4'
        ]
        assert pbrk

    def test_generate_logs_document(self, admin_client, app):
        payload = self._base_payload(app)
        admin_client.post('/scheme/generate', json=payload)
        with app.app_context():
            doc = GeneratedDocument.query.first()
            assert doc is not None
            assert doc.subject_name == 'Physics'
            assert doc.grade == 'Form 3'

    def test_generate_missing_subject_id(self, admin_client):
        res = admin_client.post('/scheme/generate', json={'grade': 'Form 3', 'term': 1})
        assert res.status_code == 400

    def test_generate_invalid_subject_id(self, admin_client):
        res = admin_client.post('/scheme/generate', json={'subject_id': 99999, 'grade': 'Form 3', 'term': 1})
        assert res.status_code == 404

    def test_generate_requires_auth(self, client):
        res = client.post('/scheme/generate', json={'subject_id': 1})
        assert res.status_code in (401, 302)

    def test_download_pdf(self, admin_client, app):
        payload = self._base_payload(app)
        gen = admin_client.post('/scheme/generate', json=payload).get_json()
        res = admin_client.post('/scheme/download', json={
            'doc_id': gen['doc_id'],
            'doc_type': 'pdf',
            'rows': gen['rows'],
            'meta': {
                'subject': 'Physics',
                'grade': 'Form 3',
                'term': 1,
                'curriculum_system': '844',
                'references': gen['references'],
            },
        })
        assert res.status_code == 200
        assert res.mimetype == 'application/pdf'
        assert res.data[:4] == b'%PDF'

    def test_download_docx(self, admin_client, app):
        payload = self._base_payload(app)
        gen = admin_client.post('/scheme/generate', json=payload).get_json()
        res = admin_client.post('/scheme/download', json={
            'doc_id': gen['doc_id'],
            'doc_type': 'docx',
            'rows': gen['rows'],
            'meta': {
                'subject': 'Physics',
                'grade': 'Form 3',
                'term': 1,
                'curriculum_system': '844',
                'references': [],
            },
        })
        assert res.status_code == 200
        assert 'wordprocessingml' in res.mimetype
        assert res.data[:2] == b'PK'

    def test_download_zip(self, admin_client, app):
        payload = self._base_payload(app)
        gen = admin_client.post('/scheme/generate', json=payload).get_json()
        res = admin_client.post('/scheme/download', json={
            'doc_id': gen['doc_id'],
            'doc_type': 'zip',
            'rows': gen['rows'],
            'meta': {
                'subject': 'Physics',
                'grade': 'Form 3',
                'term': 1,
                'curriculum_system': '844',
                'references': [],
            },
        })
        assert res.status_code == 200
        assert res.mimetype == 'application/zip'
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(res.data)) as zf:
            names = zf.namelist()
            assert any('.pdf' in n for n in names)
            assert any('.docx' in n for n in names)
            assert 'README.txt' in names

    def test_download_deducts_wallet(self, admin_client, app):
        payload = self._base_payload(app)
        gen = admin_client.post('/scheme/generate', json=payload).get_json()
        bal_before = admin_client.get('/wallet/balance').get_json()['balance']
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
        bal_after = admin_client.get('/wallet/balance').get_json()['balance']
        assert bal_after == bal_before - 30.0

    def test_download_insufficient_balance(self, auth_client, app):
        payload = self._base_payload(app)
        gen = auth_client.post('/scheme/generate', json=payload).get_json()
        res = auth_client.post('/scheme/download', json={
            'doc_id': gen.get('doc_id'),
            'doc_type': 'pdf',
            'rows': gen.get('rows', [{}]),
            'meta': {
                'subject': 'Physics',
                'grade': 'Form 3',
                'term': 1,
                'curriculum_system': '844',
                'references': [],
            },
        })
        assert res.status_code == 402
        assert res.get_json()['error'] == 'insufficient_balance'

    def test_download_invalid_doc_type(self, admin_client):
        res = admin_client.post('/scheme/download', json={'doc_type': 'xlsx', 'rows': [], 'meta': {}})
        assert res.status_code == 400

    def test_download_requires_auth(self, client):
        res = client.post('/scheme/download', json={'doc_type': 'pdf', 'rows': []})
        assert res.status_code in (401, 302)
