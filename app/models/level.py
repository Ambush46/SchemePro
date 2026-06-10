"""
MODEL: Level & SubLevel
Represents the Kenya education system hierarchy.
e.g. Level = 'Senior School'  →  SubLevel = 'Form 3'
"""
from app import db

class CurriculumSystem(db.Model):
    __tablename__ = "curriculum_system"  # Changed to match foreign key convention
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    tag = db.Column(db.String(100), unique=True)
    __table_args__ = (
        db.UniqueConstraint('tag', name='uq_curriculum_system_tag'),
    )
    
    level = db.relationship(
        'Level',
        backref='curriculum_system',
        lazy='dynamic',
        foreign_keys='Level.curriculum_system_id',
    )


    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'tag': self.tag,
        }

class Level(db.Model):
    __tablename__ = 'levels'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)      
    tag = db.Column(db.String(50), unique=True, nullable=False)  
    
    # FIX: Ensure this string matches the __tablename__ of CurriculumSystem
    curriculum_system_id = db.Column(db.Integer, db.ForeignKey('curriculum_system.id'), nullable=False)

    # Relationships
    sublevels = db.relationship('SubLevel', backref='level', lazy='dynamic', cascade='all, delete-orphan')
    subjects = db.relationship('Subject', backref='level', lazy='dynamic', cascade='all, delete-orphan')

    def to_dict(self, include_sublevels=True):
        d = {
            'id': self.id,
            'name': self.name,
            'tag': self.tag,
            'curriculum_system': self.curriculum_system.name if self.curriculum_system else None,
        }
        if include_sublevels:
            d['sublevels'] = [s.to_dict() for s in self.sublevels.order_by(SubLevel.tag)]
        return d

    def __repr__(self):
        return f'<Level {self.tag}>'


class SubLevel(db.Model):
    __tablename__ = 'sublevels'

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(20), nullable=False)       
    name = db.Column(db.String(50), nullable=False)      
    level_id = db.Column(db.Integer, db.ForeignKey('levels.id'), nullable=False)

    def to_dict(self):
        return {'id': self.id, 'tag': self.tag, 'name': self.name, 'level_id': self.level_id}

    def __repr__(self):
        return f'<SubLevel {self.name}>'
