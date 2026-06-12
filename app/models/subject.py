"""
MODEL: Subject
Subjects tied to a curriculum Level. curriculum_system = '844' or 'CBC'.
"""
from app import db


class Subject(db.Model):
    __tablename__ = 'subjects'

    id = db.Column(db.Integer, primary_key=True)
    tag = db.Column(db.String(80), unique=True, nullable=False)   # 'physics_senior'
    name = db.Column(db.String(150), nullable=False)              # 'Physics'
    level_id = db.Column(db.Integer, db.ForeignKey('levels.id'), nullable=False)
    sublevel_id = db.Column(db.Integer, db.ForeignKey('sublevels.id'), nullable=True)
    curriculum_system = db.Column(db.Integer, db.ForeignKey('curriculum_system.id'), nullable=True,)  
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    sublevel = db.relationship('SubLevel', backref='subjects', lazy='joined')
    topics = db.relationship('Topic', backref='subject', lazy='dynamic', cascade='all, delete-orphan')

    # Relationship to CurriculumSystem via Level -> CurriculumSystem
    curriculum_system_obj = db.relationship(
        'CurriculumSystem',
        secondary='levels',
        primaryjoin='Subject.level_id == Level.id',
        secondaryjoin='Level.curriculum_system_id == CurriculumSystem.id',
        viewonly=True,
        uselist=False,
    )


    def to_dict(self, include_topics=False):
        d = {
            'id': self.id,
            'tag': self.tag,
            'name': self.name,
            'level_id': self.level_id,
            'level_name': self.level.name if self.level else None,
            'sublevel_id': self.sublevel_id,
            'sublevel_name': self.sublevel.name if self.sublevel else None,
            'curriculum_system': self.curriculum_system_obj.name if self.curriculum_system_obj else None,
            'curriculum_system_id':self.curriculum_system,
        }
        if include_topics:
            d['topics'] = [t.to_dict() for t in self.topics.order_by('id')]
        return d

    def __repr__(self):
        return f'<Subject {self.name}>'
