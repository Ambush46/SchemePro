"""
MODEL: Level & SubLevel
Represents the Kenya education system hierarchy.
e.g. Level = 'Senior School'  →  SubLevel = 'Form 3'
"""
from app import db


class Level(db.Model):
    __tablename__ = 'levels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)      # 'Junior School (CBC)'
    tag = db.Column(db.String(50), unique=True, nullable=False)  # 'junior_cbc'
    curriculum_system = db.Column(db.String(10), nullable=False, default='844')  # '844' | 'CBC'

    # Relationships
    sublevels = db.relationship('SubLevel', backref='level', lazy='dynamic', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='level', lazy='dynamic')

    def to_dict(self, include_sublevels=True):
        d = {
            'id': self.id,
            'name': self.name,
            'tag': self.tag,
            'curriculum_system': self.curriculum_system,
        }
        if include_sublevels:
            d['sublevels'] = [s.to_dict() for s in self.sublevels.order_by('tag')]
        return d

    def __repr__(self):
        return f'<Level {self.tag}>'


class SubLevel(db.Model):
    __tablename__ = 'sublevels'

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(20), nullable=False)       # 'form3', 'grade7'
    name = db.Column(db.String(50), nullable=False)      # 'Form 3', 'Grade 7'
    level_id = db.Column(db.Integer, db.ForeignKey('levels.id'), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'tag': self.tag, 'name': self.name, 'level_id': self.level_id}

    def __repr__(self):
        return f'<SubLevel {self.name}>'
