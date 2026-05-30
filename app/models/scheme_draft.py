"""
MODEL: SchemeDraft
Stores the current in-progress scheme-of-work draft for a user.
One draft row per user is updated as the user moves through steps.
"""
import json
from datetime import datetime, timezone
from app import db


class SchemeDraft(db.Model):
    __tablename__ = 'scheme_drafts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    step = db.Column(db.Integer, default=1, nullable=False)
    payload = db.Column(db.Text, nullable=False, default='{}')
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def set_payload(self, payload):
        self.payload = json.dumps(payload or {}, default=str)

    def get_payload(self):
        try:
            return json.loads(self.payload or '{}')
        except (TypeError, ValueError):
            return {}

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'subject_id': self.subject_id,
            'step': self.step,
            'payload': self.get_payload(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
