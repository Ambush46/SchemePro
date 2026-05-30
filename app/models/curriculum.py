"""
MODELS: Topic, SubTopic, Content
Curriculum hierarchy below Subject.
  Subject → Topic (Strand) → SubTopic (Sub-strand) → Content
"""
from app import db


class Topic(db.Model):
    """Topic (844) or Strand (CBC)."""
    __tablename__ = 'topics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subjects.id'), nullable=False)
    order = db.Column(db.Integer, default=0)

    subtopics = db.relationship('SubTopic', backref='topic', lazy='dynamic',
                                cascade='all, delete-orphan', order_by='SubTopic.order')

    def to_dict(self, include_subtopics=True):
        d = {'id': self.id, 'name': self.name, 'subject_id': self.subject_id, 'order': self.order}
        if include_subtopics:
            d['subtopics'] = [s.to_dict() for s in self.subtopics]
        return d

    def __repr__(self):
        return f'<Topic {self.name}>'


class SubTopic(db.Model):
    """Sub-topic (844) or Sub-strand (CBC)."""
    __tablename__ = 'subtopics'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('topics.id'), nullable=False)
    order = db.Column(db.Integer, default=0)

    content = db.relationship('Content', backref='subtopic', uselist=False,
                              cascade='all, delete-orphan')

    def to_dict(self, include_content=True):
        d = {'id': self.id, 'name': self.name, 'topic_id': self.topic_id}
        if include_content and self.content:
            d['content'] = self.content.to_dict()
        return d

    def __repr__(self):
        return f'<SubTopic {self.name}>'


class Content(db.Model):
    """
    Detailed content for a subtopic.
    Includes teaching aids, number of lessons, and Key Inquiry Questions (KIQs) for CBC.
    """
    __tablename__ = 'content'

    id = db.Column(db.Integer, primary_key=True)
    subtopic_id = db.Column(db.Integer, db.ForeignKey('subtopics.id'), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=True)                    # Teaching/learning materials
    num_lessons = db.Column(db.Integer, default=1)                 # Recommended lessons
    key_inquiry_question = db.Column(db.Text, nullable=True)       # KIQs (CBC)
    learning_outcomes = db.Column(db.Text, nullable=True)          # Specific outcomes
    activities = db.Column(db.Text, nullable=True)                 # Learning activities
    references = db.Column(db.Text, nullable=True)                 # Book references

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'num_lessons': self.num_lessons,
            'key_inquiry_question': self.key_inquiry_question,
            'learning_outcomes': self.learning_outcomes,
            'activities': self.activities,
            'references': self.references,
        }
