"""
MODELS: GeneratedDocument, DocumentPricing
Tracks every generated scheme and admin-configurable per-format prices.
"""
import uuid
from datetime import datetime, timezone
from app import db


class GeneratedDocument(db.Model):
    """
    Logs each scheme of work generation.
    Powers admin dashboard: 'which subject/grade has been generated most'.
    """
    __tablename__ = 'generated_documents'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=True)
    subject_name = db.Column(db.String(150), nullable=False)
    grade = db.Column(db.String(50), nullable=False)        # 'Form 3', 'Grade 7'
    term = db.Column(db.Integer, nullable=False)
    curriculum_system = db.Column(db.String(10), nullable=False)  # '844' | 'CBC'
    doc_type = db.Column(db.String(10), nullable=True)            # 'pdf' | 'docx' | 'zip' (set on download)
    generated_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    downloaded_at = db.Column(db.DateTime(timezone=True), nullable=True)
    payment_ref = db.Column(db.String(40), nullable=True)         # FK to Payment.transaction_id

    subject = db.relationship('Subject', backref='generated_docs')

    def to_dict(self):
        return {
            'id': self.id,
            'subject_name': self.subject_name,
            'grade': self.grade,
            'term': self.term,
            'curriculum_system': self.curriculum_system,
            'doc_type': self.doc_type,
            'generated_at': self.generated_at.isoformat(),
            'downloaded_at': self.downloaded_at.isoformat() if self.downloaded_at else None,
        }


class DocumentPricing(db.Model):
    """Admin-configurable price per document type."""
    __tablename__ = 'document_pricing'

    id = db.Column(db.Integer, primary_key=True)
    doc_type = db.Column(db.String(10), unique=True, nullable=False)  # 'pdf', 'docx', 'zip'
    label = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0.0)
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {'doc_type': self.doc_type, 'label': self.label, 'price': self.price}
