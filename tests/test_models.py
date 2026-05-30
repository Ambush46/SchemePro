import pytest

from app import db
from app.models.role import Role
from app.models.user import User
from app.models.wallet import WalletTransaction, Payment, TransactionHistory
from app.models.level import Level
from app.models.subject import Subject
from app.models.curriculum import Topic, SubTopic
from app.models.pricing import DocumentPricing


class TestRoleModel:
    def test_roles_seeded(self, app):
        with app.app_context():
            assert Role.query.count() == 4
            tags = {r.tag for r in Role.query.all()}
            assert tags == {'superuser', 'admin', 'support', 'client'}

    def test_superuser_can_manage_users(self, app):
        with app.app_context():
            su = Role.query.filter_by(tag='superuser').first()
            assert su.can('manage_users') is True

    def test_client_cannot_manage_users(self, app):
        with app.app_context():
            r = Role.query.filter_by(tag='client').first()
            assert r.can('manage_users') is False

    def test_client_can_generate_scheme(self, app):
        with app.app_context():
            r = Role.query.filter_by(tag='client').first()
            assert r.can('generate_scheme') is True

    def test_support_cannot_manage_pricing(self, app):
        with app.app_context():
            r = Role.query.filter_by(tag='support').first()
            assert r.can('manage_pricing') is False

    def test_admin_can_manage_pricing(self, app):
        with app.app_context():
            r = Role.query.filter_by(tag='admin').first()
            assert r.can('manage_pricing') is True

    def test_role_count_by_tag(self, app):
        with app.app_context():
            assert Role.count_by_tag('superuser') == 1
            assert Role.count_by_tag('client') == 0

    def test_role_count_all(self, app):
        with app.app_context():
            counts = Role.count_all()
            assert 'superuser' in counts and 'client' in counts

    def test_role_to_dict(self, app):
        with app.app_context():
            r = Role.query.filter_by(tag='admin').first()
            d = r.to_dict()
            assert d['tag'] == 'admin' and 'name' in d


class TestUserModel:
    def test_admin_seeded(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            assert admin is not None
            assert admin.role.tag == 'superuser'

    def test_wallet_created_for_admin(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            assert admin.wallet is not None
            assert admin.wallet.balance == 500.0

    def test_is_admin_true_for_superuser(self, app):
        with app.app_context():
            assert User.query.filter_by(username='admin').first().is_admin() is True

    def test_is_admin_false_for_client(self, app, client):
        client.post('/auth/register', json={
            'name': 'T',
            'username': 'ttt',
            'email': 'ttt@t.com',
            'password': 'Pass12345',
            'confirm_password': 'Pass12345',
        })
        with app.app_context():
            u = User.query.filter_by(username='ttt').first()
            assert u.is_admin() is False

    def test_wallet_balance_property(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            assert admin.wallet_balance == 500.0

    def test_record_activity_creates_history(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.record_activity('scheme_generator')
            from app.models.user import UserHistory

            entry = UserHistory.query.filter_by(
                user_id=admin.id,
                feature='scheme_generator',
            ).first()
            assert entry is not None and entry.visit_count == 1

    def test_record_activity_increments_count(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.record_activity('wallet_topup')
            admin.record_activity('wallet_topup')
            from app.models.user import UserHistory

            entry = UserHistory.query.filter_by(
                user_id=admin.id,
                feature='wallet_topup',
            ).first()
            assert entry.visit_count == 2

    def test_to_dict_excludes_password(self, app):
        with app.app_context():
            d = User.query.filter_by(username='admin').first().to_dict()
            assert 'password' not in d
            assert d['username'] == 'admin'


class TestWalletModel:
    def test_credit_increases_balance(self, app):
        with app.app_context():
            w = User.query.filter_by(username='admin').first().wallet
            initial = w.balance
            w.credit(200.0, 'MPESA001', 'mpesa')
            db.session.commit()
            assert w.balance == initial + 200.0

    def test_credit_creates_wallet_transaction(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.wallet.credit(100.0, 'MPESA002', 'mpesa')
            db.session.commit()
            txn = WalletTransaction.query.filter_by(user_id=admin.id).first()
            assert txn is not None and txn.money_system == 'mpesa'

    def test_credit_creates_transaction_history_in(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.wallet.credit(100.0, 'MPESA003', 'mpesa')
            db.session.commit()
            hist = TransactionHistory.query.filter_by(user_id=admin.id, tag='in').first()
            assert hist is not None

    def test_debit_decreases_balance(self, app):
        with app.app_context():
            w = User.query.filter_by(username='admin').first().wallet
            initial = w.balance
            w.debit(30.0, 'pdf')
            db.session.commit()
            assert w.balance == round(initial - 30.0, 2)

    def test_debit_creates_payment_record(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.wallet.debit(30.0, 'pdf')
            db.session.commit()
            p = Payment.query.filter_by(user_id=admin.id, doc_type='pdf').first()
            assert p is not None

    def test_debit_creates_transaction_history_out(self, app):
        with app.app_context():
            admin = User.query.filter_by(username='admin').first()
            admin.wallet.debit(30.0, 'pdf')
            db.session.commit()
            hist = TransactionHistory.query.filter_by(user_id=admin.id, tag='out').first()
            assert hist is not None

    def test_debit_insufficient_balance_raises(self, app):
        with app.app_context():
            w = User.query.filter_by(username='admin').first().wallet
            with pytest.raises(ValueError, match='Insufficient'):
                w.debit(99999.0, 'pdf')

    def test_credit_negative_raises(self, app):
        with app.app_context():
            w = User.query.filter_by(username='admin').first().wallet
            with pytest.raises(ValueError):
                w.credit(-50.0, 'X', 'mpesa')

    def test_credit_zero_raises(self, app):
        with app.app_context():
            w = User.query.filter_by(username='admin').first().wallet
            with pytest.raises(ValueError):
                w.credit(0.0, 'X', 'mpesa')


class TestCurriculumModels:
    def test_levels_seeded(self, app):
        with app.app_context():
            assert Level.query.count() >= 3
            assert {l.tag for l in Level.query.all()} >= {'senior', 'junior_cbc', 'upper_primary'}

    def test_sublevels_seeded(self, app):
        with app.app_context():
            senior = Level.query.filter_by(tag='senior').first()
            assert senior.sublevels.count() == 4

    def test_subjects_seeded(self, app):
        with app.app_context():
            assert Subject.query.count() >= 15
            p = Subject.query.filter_by(tag='physics_senior').first()
            assert p is not None and p.curriculum_system == '844'

    def test_cbc_subject_seeded(self, app):
        with app.app_context():
            s = Subject.query.filter_by(tag='sci_junior').first()
            assert s is not None and s.curriculum_system == 'CBC'

    def test_topics_seeded_for_physics(self, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
            topics = Topic.query.filter_by(subject_id=physics.id).all()
            assert len(topics) >= 4

    def test_subtopics_with_content_seeded(self, app):
        with app.app_context():
            physics = Subject.query.filter_by(tag='physics_senior').first()
            topic = Topic.query.filter_by(subject_id=physics.id, name='Linear Motion').first()
            assert topic is not None
            sts = SubTopic.query.filter_by(topic_id=topic.id).all()
            assert len(sts) >= 2
            for st in sts:
                assert st.content is not None
                assert st.content.num_lessons >= 1
                assert st.content.key_inquiry_question is not None

    def test_cbc_topics_seeded(self, app):
        with app.app_context():
            sc = Subject.query.filter_by(tag='sci_junior').first()
            topics = Topic.query.filter_by(subject_id=sc.id).all()
            assert len(topics) >= 2
            for t in topics:
                for st in SubTopic.query.filter_by(topic_id=t.id).all():
                    if st.content:
                        assert st.content.key_inquiry_question is not None

    def test_pricing_seeded(self, app):
        with app.app_context():
            for doc_type, price in [('pdf', 30.0), ('docx', 50.0), ('zip', 70.0)]:
                p = DocumentPricing.query.filter_by(doc_type=doc_type).first()
                assert p is not None and p.price == price
