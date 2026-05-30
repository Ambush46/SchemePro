"""
MODEL: User
Stores user accounts, roles, and activity tracking.
"""
from datetime import datetime, timezone
from flask_login import UserMixin

from app import db


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)              # bcrypt hash
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    # Concrete column used by admin enable/disable and Flask-Login.
    # Some migrations previously used an `active` column; we keep a backward-
    # compatible alias below.
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    region = db.Column(db.String(100), nullable=True)                 # e.g. 'Nairobi'
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    last_logout = db.Column(db.DateTime(timezone=True), nullable=True)
    last_active = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    wallet = db.relationship('Wallet', backref='user', uselist=False, cascade='all, delete-orphan')
    history_entries = db.relationship('UserHistory', backref='user', lazy='dynamic', cascade='all, delete-orphan')
    payments = db.relationship('Payment', backref='user', lazy='dynamic')
    wallet_transactions = db.relationship('WalletTransaction', backref='user', lazy='dynamic')
    transaction_history = db.relationship('TransactionHistory', backref='user', lazy='dynamic')
    generated_docs = db.relationship('GeneratedDocument', backref='user', lazy='dynamic')
    scheme_draft = db.relationship('SchemeDraft', backref='user', uselist=False, cascade='all, delete-orphan')

    # Flask-Login requires get_id to return string
    def get_id(self):
        return str(self.id)


    @property
    def wallet_balance(self) -> float:
        return self.wallet.balance if self.wallet else 0.0

    def can(self, permission: str) -> bool:
        return self.role.can(permission) if self.role else False

    def is_admin(self) -> bool:
        return self.role.tag in ('admin', 'superuser', 'support') if self.role else False

    def is_support(self) -> bool:
        return self.role.tag == 'support' if self.role else False

    # Flask-Login's UserMixin looks for an `is_active` attribute.
    # We store it as a real DB column, so no hybrid property is needed.


    def record_activity(self, feature: str):
        """Log which feature/page the user visited."""
        from app import db as _db
        entry = UserHistory.query.filter_by(user_id=self.id, feature=feature).first()
        if entry:
            entry.visit_count += 1
            entry.last_visited = datetime.now(timezone.utc)
        else:
            entry = UserHistory(user_id=self.id, feature=feature)
            _db.session.add(entry)
        self.last_active = datetime.now(timezone.utc)
        _db.session.commit()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'username': self.username,
            'email': self.email,
            'role': self.role.tag if self.role else None,
            'role_name': self.role.name if self.role else None,
            'is_active': self.is_active,
            'region': self.region,
            'wallet_balance': self.wallet_balance,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'last_logout': self.last_logout.isoformat() if self.last_logout else None,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f'<User {self.username}>'


class UserHistory(db.Model):
    """Tracks which features a user has visited and how often."""
    __tablename__ = 'user_history'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feature = db.Column(db.String(100), nullable=False)     # e.g. 'scheme_generator', 'admin_revenue'
    visit_count = db.Column(db.Integer, default=1)
    last_visited = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'feature': self.feature,
            'visit_count': self.visit_count,
            'last_visited': self.last_visited.isoformat(),
        }
