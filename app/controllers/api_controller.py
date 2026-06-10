"""
CONTROLLER: API (v1)
RESTful JSON endpoints consumed by the SPA frontend.
All endpoints under /api/v1/
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models.level import Level, SubLevel, CurriculumSystem 
from app.models.subject import Subject
from app.models.curriculum import Topic, SubTopic, Content
from app.models.pricing import DocumentPricing, GeneratedDocument

api_bp = Blueprint('api', __name__)


# ── HELPERS ────────────────────────────────────────────────────────
def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin access required.'}), 403
    return None


# ── LEVELS ────────────────────────────────────────────────────────
@api_bp.route('/levels', methods=['GET'])
def get_levels():
    """GET /api/v1/levels — All levels with sublevels (for landing page & SPA)."""
    levels = Level.query.order_by(Level.id).all()
    return jsonify({'success': True, 'data': [l.to_dict() for l in levels]})



@api_bp.route('/levels/<int:level_id>', methods=['PUT'])
@login_required
def update_level(level_id):
    err = _require_admin()
    if err: return err
    data = request.get_json() or {}
    lvl = db.session.get(Level, level_id)
    if not lvl:
        return jsonify({'success': False, 'error': 'Level not found.'}), 404
    if data.get('name'):
        lvl.name = data['name']
    if data.get('tag'):
        if Level.query.filter(Level.tag == data['tag'], Level.id != level_id).first():
            return jsonify({'success': False, 'error': 'Tag already exists.'}), 409
        lvl.tag = data['tag']
        
    # FIX: Resolve the curriculum system tag to a model instance during update
    if data.get('curriculum_system'):
        system_tag = data['curriculum_system']
        system_obj = CurriculumSystem.query.filter_by(tag=system_tag).first()
        if not system_obj:
            return jsonify({'success': False, 'error': f'Curriculum system "{system_tag}" not found.'}), 400
        lvl.curriculum_system = system_obj

    db.session.commit()
    return jsonify({'success': True, 'data': lvl.to_dict()}), 200


@api_bp.route('/levels/<int:level_id>', methods=['DELETE'])
@login_required
def delete_level(level_id):
    err = _require_admin()
    if err: return err
    lvl = db.session.get(Level, level_id)
    if not lvl:
        return jsonify({'success': False, 'error': 'Level not found.'}), 404
    db.session.delete(lvl)
    db.session.commit()
    return jsonify({'success': True}), 200


@api_bp.route('/sublevels', methods=['POST'])
@login_required
def create_sublevel():
    err = _require_admin()
    if err: return err
    data = request.get_json()
    sl = SubLevel(tag=data['tag'], name=data['name'], level_id=data['level_id'])
    db.session.add(sl)
    db.session.commit()
    return jsonify({'success': True, 'data': sl.to_dict()}), 201


# ── SUBJECTS ──────────────────────────────────────────────────────
@api_bp.route('/subjects', methods=['GET'])
def get_subjects():
    """GET /api/v1/subjects?level_id=X&sublevel_id=Y&curriculum_system=Z — Subjects, optionally filtered."""
    level_id = request.args.get('level_id', type=int)
    sublevel_id = request.args.get('sublevel_id', type=int)
    curriculum_system = request.args.get('curriculum_system')
    q = Subject.query.filter_by(is_active=True)
    if level_id:
        q = q.filter_by(level_id=level_id)
    if sublevel_id:
        q = q.filter_by(sublevel_id=sublevel_id)
    if curriculum_system:
        q = q.filter_by(curriculum_system=curriculum_system)
    subjects = q.order_by(Subject.name).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in subjects]})


@api_bp.route('/subjects', methods=['POST'])
@login_required
def create_subject():
    err = _require_admin()
    if err: return err
    data = request.get_json() or {}
    if Subject.query.filter_by(tag=data.get('tag', '')).first():
        return jsonify({'success': False, 'error': 'Subject tag already exists.'}), 409
    level = db.session.get(Level, data.get('level_id'))
    if not level:
        return jsonify({'success': False, 'error': 'Level not found.'}), 404
    sublevel_id = data.get('sublevel_id')
    if sublevel_id:
        sublevel = db.session.get(SubLevel, sublevel_id)
        if not sublevel or sublevel.level_id != level.id:
            return jsonify({'success': False, 'error': 'Sublevel must belong to the selected level.'}), 400
    subj = Subject(
        tag=data['tag'],
        name=data['name'],
        level_id=level.id,
        sublevel_id=sublevel_id,
        curriculum_system=data.get('curriculum_system', level.curriculum_system),
    )
    db.session.add(subj)
    db.session.commit()
    return jsonify({'success': True, 'data': subj.to_dict()}), 201



@api_bp.route('/subjects/<int:subject_id>', methods=['PUT'])
@login_required
def update_subject(subject_id):


    err = _require_admin()
    if err: return err
    data = request.get_json() or {}

    subj = db.session.get(Subject, subject_id)
    if not subj:
        return jsonify({'success': False, 'error': 'Subject not found.'}), 404

    # Validate level/sublevel relationships if provided
    if data.get('level_id') is not None:
        new_level = db.session.get(Level, data.get('level_id'))
        if not new_level:
            return jsonify({'success': False, 'error': 'Level not found.'}), 404
        subj.level_id = new_level.id

        # sublevel check
        if data.get('sublevel_id') is not None:
            new_sublevel_id = data.get('sublevel_id')
            if new_sublevel_id:
                sublevel = db.session.get(SubLevel, new_sublevel_id)
                if not sublevel or sublevel.level_id != new_level.id:
                    return jsonify({'success': False, 'error': 'Sublevel must belong to the selected level.'}), 400
            subj.sublevel_id = new_sublevel_id

    if data.get('name'):
        subj.name = data['name']

    if data.get('tag'):
        if Subject.query.filter(Subject.tag == data['tag'], Subject.id != subject_id).first():
            return jsonify({'success': False, 'error': 'Subject tag already exists.'}), 409
        subj.tag = data['tag']

    if data.get('curriculum_system'):
        subj.curriculum_system = data['curriculum_system']

    # Allow updating sublevel without changing level if client sends it
    if data.get('sublevel_id') is not None and data.get('level_id') is None:
        sublevel_id = data.get('sublevel_id')
        if sublevel_id:
            sublevel = db.session.get(SubLevel, sublevel_id)
            if not sublevel or sublevel.level_id != subj.level_id:
                return jsonify({'success': False, 'error': 'Sublevel must belong to the selected level.'}), 400
        subj.sublevel_id = sublevel_id

    if data.get('is_active') is not None:
        subj.is_active = bool(data.get('is_active'))

    db.session.commit()
    return jsonify({'success': True, 'data': subj.to_dict()}), 200


@api_bp.route('/subjects/<int:subject_id>', methods=['DELETE'])
@login_required
def delete_subject(subject_id):

    err = _require_admin()
    if err: return err
    subj = db.session.get(Subject, subject_id)
    if not subj:
        return jsonify({'success': False, 'error': 'Subject not found.'}), 404
    db.session.delete(subj)
    db.session.commit()

    return jsonify({'success': True}), 200


# ── TOPICS
@api_bp.route('/topics', methods=['GET'])
def get_topics():
    """GET /api/v1/topics?subject_id=X — Topics/Strands for a subject."""
    subject_id = request.args.get('subject_id', type=int)
    if not subject_id:
        return jsonify({'success': False, 'error': 'subject_id is required.'}), 400
    topics = Topic.query.filter_by(subject_id=subject_id).order_by(Topic.order, Topic.id).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in topics]})


@api_bp.route('/topics', methods=['POST'])
@login_required
def create_topic():
    err = _require_admin()
    if err: return err
    data = request.get_json()
    t = Topic(name=data['name'], subject_id=data['subject_id'], order=data.get('order', 0))
    db.session.add(t)
    db.session.commit()
    return jsonify({'success': True, 'data': t.to_dict()}), 201


@api_bp.route('/topics/<int:topic_id>', methods=['PUT'])
@login_required
def update_topic(topic_id):
    err = _require_admin()
    if err: return err
    data = request.get_json() or {}

    t = db.session.get(Topic, topic_id)
    if not t:
        return jsonify({'success': False, 'error': 'Topic not found.'}), 404

    if data.get('name'):
        t.name = data['name']

    if data.get('subject_id') is not None:
        subj = db.session.get(Subject, data.get('subject_id'))
        if not subj:
            return jsonify({'success': False, 'error': 'Subject not found.'}), 404
        t.subject_id = subj.id

    if data.get('order') is not None:
        t.order = int(data.get('order'))

    db.session.commit()
    return jsonify({'success': True, 'data': t.to_dict()}), 200


@api_bp.route('/topics/<int:topic_id>', methods=['DELETE'])
@login_required
def delete_topic(topic_id):

    err = _require_admin()
    if err: return err
    t = db.session.get(Topic, topic_id)
    if not t:
        return jsonify({'success': False, 'error': 'Topic not found.'}), 404
    db.session.delete(t)
    db.session.commit()
    return jsonify({'success': True})


# ── SUBTOPICS ─────────────────────────────────────────────────────
@api_bp.route('/subtopics', methods=['GET'])
def get_subtopics():
    """GET /api/v1/subtopics?topic_id=X"""
    topic_id = request.args.get('topic_id', type=int)
    if not topic_id:
        return jsonify({'success': False, 'error': 'topic_id is required.'}), 400
    sts = SubTopic.query.filter_by(topic_id=topic_id).order_by(SubTopic.order, SubTopic.id).all()
    return jsonify({'success': True, 'data': [s.to_dict() for s in sts]})


@api_bp.route('/subtopics', methods=['POST'])
@login_required
def create_subtopic():
    err = _require_admin()
    if err: return err
    data = request.get_json()
    st = SubTopic(name=data['name'], topic_id=data['topic_id'], order=data.get('order', 0))
    db.session.add(st)
    db.session.flush()
    if data.get('content'):
        c = Content(
            subtopic_id=st.id,
            content=data['content'].get('content'),
            num_lessons=data['content'].get('num_lessons', 1),
            key_inquiry_question=data['content'].get('key_inquiry_question'),
            learning_outcomes=data['content'].get('learning_outcomes'),
            activities=data['content'].get('activities'),
            references=data['content'].get('references'),
        )
        db.session.add(c)
    db.session.commit()
    return jsonify({'success': True, 'data': st.to_dict()}), 201


@api_bp.route('/subtopics/<int:subtopic_id>', methods=['PUT'])
@login_required
def update_subtopic(subtopic_id):
    err = _require_admin()
    if err: return err
    data = request.get_json() or {}

    st = db.session.get(SubTopic, subtopic_id)
    if not st:
        return jsonify({'success': False, 'error': 'Subtopic not found.'}), 404

    if data.get('name'):
        st.name = data['name']

    if data.get('topic_id') is not None:
        t = db.session.get(Topic, data.get('topic_id'))
        if not t:
            return jsonify({'success': False, 'error': 'Topic not found.'}), 404
        st.topic_id = t.id

    if data.get('order') is not None:
        st.order = int(data.get('order'))

    # Content update/create
    if data.get('content') is not None:
        payload = data.get('content') or {}
        if st.content:
            c = st.content
        else:
            c = Content(subtopic_id=st.id)
            db.session.add(c)

        c.content = payload.get('content')
        if payload.get('num_lessons') is not None:
            c.num_lessons = int(payload.get('num_lessons'))
        c.key_inquiry_question = payload.get('key_inquiry_question')
        c.learning_outcomes = payload.get('learning_outcomes')
        c.activities = payload.get('activities')
        c.references = payload.get('references')

    db.session.commit()
    return jsonify({'success': True, 'data': st.to_dict()}), 200


@api_bp.route('/subtopics/<int:subtopic_id>', methods=['DELETE'])
@login_required
def delete_subtopic(subtopic_id):
    err = _require_admin()
    if err: return err

    st = db.session.get(SubTopic, subtopic_id)
    if not st:
        return jsonify({'success': False, 'error': 'Subtopic not found.'}), 404

    db.session.delete(st)
    db.session.commit()
    return jsonify({'success': True}), 200


# ── PRICING ───────────────────────────────────────────────────────
@api_bp.route('/pricing', methods=['GET'])
def get_pricing():

    """GET /api/v1/pricing — Document download prices."""
    prices = DocumentPricing.query.all()
    return jsonify({'success': True, 'data': {p.doc_type: p.to_dict() for p in prices}})


@api_bp.route('/pricing', methods=['PUT'])
@login_required
def update_pricing():
    """PUT /api/v1/pricing — Admin updates prices. Body: {pdf: 30, docx: 50, zip: 70}"""
    err = _require_admin()
    if err: return err
    data = request.get_json()
    for doc_type, price in data.items():
        p = DocumentPricing.query.filter_by(doc_type=doc_type).first()
        if p:
            p.price = float(price)
    db.session.commit()
    prices = DocumentPricing.query.all()
    return jsonify({'success': True, 'data': {p.doc_type: p.to_dict() for p in prices}})


# ── DOC STATS ─────────────────────────────────────────────────────
@api_bp.route('/doc-stats', methods=['GET'])
@login_required
def doc_stats():
    """GET /api/v1/doc-stats — How many times each subject/grade was generated (admin)."""
    err = _require_admin()
    if err: return err
    from sqlalchemy import func
    stats = db.session.query(
        GeneratedDocument.subject_name,
        GeneratedDocument.grade,
        GeneratedDocument.curriculum_system,
        func.count(GeneratedDocument.id).label('count')
    ).group_by(
        GeneratedDocument.subject_name,
        GeneratedDocument.grade,
        GeneratedDocument.curriculum_system
    ).order_by(func.count(GeneratedDocument.id).desc()).all()

    return jsonify({'success': True, 'data': [
        {'subject': s, 'grade': g, 'system': cs, 'count': c}
        for s, g, cs, c in stats
    ]})
