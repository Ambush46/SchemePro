"""
MODEL: Role
Defines user roles and their permissions within SchemePro.
"""
from app import db


class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(50), unique=True, nullable=False)   # e.g. 'admin', 'client'
    name = db.Column(db.String(100), nullable=False)              # e.g. 'Administrator'

    # Relationships
    users = db.relationship('User', backref='role', lazy='dynamic')

    ROLE_HIERARCHY = {
        'client': 0,
        'support': 1,
        'admin': 2,
        'superuser': 3,
    }

    # ── Permissions map ────────────────────────────────────────────
    PERMISSIONS = {
        'superuser': ['manage_users', 'manage_roles', 'manage_content',
                      'manage_pricing', 'view_revenue', 'generate_scheme', 'download_doc',
                      'view_users', 'modify_user_status', 'view_transactions', 'process_refund'],
        'admin':     ['manage_users', 'manage_content', 'manage_pricing',
                      'view_revenue', 'generate_scheme', 'download_doc',
                      'view_users', 'modify_user_status', 'view_transactions', 'process_refund'],
        'support':   ['view_users', 'modify_user_status', 'view_transactions', 'process_refund',
                      'generate_scheme', 'download_doc'],
        'client':    ['generate_scheme', 'download_doc'],
    }

    def can(self, permission: str) -> bool:
        return permission in self.PERMISSIONS.get(self.tag, [])

    def rank(self) -> int:
        return self.ROLE_HIERARCHY.get(self.tag, 0)

    @classmethod
    def count_by_tag(cls, tag: str) -> int:
        """Return number of users with a given role tag."""
        role = cls.query.filter_by(tag=tag).first()
        return role.users.count() if role else 0

    @classmethod
    def count_all(cls) -> dict:
        """Return counts for all roles."""
        return {r.tag: r.users.count() for r in cls.query.all()}

    def to_dict(self):
        return {
            'id': self.id,
            'tag': self.tag,
            'name': self.name,
            'user_count': self.users.count(),
        }

    def __repr__(self):
        return f'<Role {self.tag}>'
