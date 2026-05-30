"""
CONTROLLER: Admin Panel
Restricted to roles: admin, superuser.
Handles user management, revenue reporting, and content management.
"""
from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db, bcrypt
from app.models.user import User, UserHistory
from app.models.role import Role
from app.models.wallet import Wallet, TransactionHistory, Payment, WalletTransaction
from app.models.pricing import GeneratedDocument, DocumentPricing

admin_bp = Blueprint('admin_panel', __name__)


def _admin_required():
    if not current_user.is_authenticated or not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin access required.'}), 403
    return None


def _permission_required(permission):
    if not current_user.is_authenticated or not current_user.can(permission):
        return jsonify({'success': False, 'error': 'Permission denied.'}), 403
    return None


def _current_user_can_manage_target(user, action='manage'):
    if not current_user.is_authenticated or not user or not user.role:
        return False, 'Permission denied.'

    if current_user.id == user.id:
        if action == 'view':
            return True, None
        return False, 'You cannot modify your own account.'

    if current_user.role.tag == 'superuser':
        return True, None

    if current_user.role.tag == 'admin':
        if user.role.tag == 'superuser':
            return False, 'Admin cannot manage a superuser account.'
        return True, None

    if current_user.role.tag == 'support':
        if user.role.tag in ('admin', 'superuser'):
            return False, 'Support cannot access admin or superuser accounts.'
        if action != 'view' and user.role.tag == 'support':
            return False, 'Support cannot manage fellow support accounts.'
        return True, None

    return False, 'Permission denied.'


# ── OVERVIEW ──────────────────────────────────────────────────────
@admin_bp.route('/overview', methods=['GET'])
@login_required
def overview():
    err = _admin_required() or _permission_required('view_revenue')
    if err: return err

    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_docs = GeneratedDocument.query.count()

    # Revenue: actual = sum of all payments (debits)
    actual_revenue = db.session.query(func.sum(Payment.amount)).scalar() or 0.0
    # Potential revenue = sum of all wallet balances
    potential_revenue = db.session.query(func.sum(Wallet.balance)).scalar() or 0.0
    # Total deposited
    total_deposited = db.session.query(func.sum(WalletTransaction.amount)).scalar() or 0.0

    role_counts = Role.count_all()

    return jsonify({
        'success': True,
        'data': {
            'total_users': total_users,
            'active_users': active_users,
            'total_docs_generated': total_docs,
            'actual_revenue': round(actual_revenue, 2),
            'potential_revenue': round(potential_revenue, 2),
            'total_deposited': round(total_deposited, 2),
            'role_counts': role_counts,
        }
    })


# ── REVENUE BY DAY ────────────────────────────────────────────────
@admin_bp.route('/revenue/daily', methods=['GET'])
@login_required
def revenue_daily():
    err = _admin_required() or _permission_required('view_revenue')
    if err: return err

    days = int(request.args.get('days', 30))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    results = db.session.query(
        func.date(TransactionHistory.created_at).label('day'),
        TransactionHistory.tag,
        func.sum(TransactionHistory.amount).label('total')
    ).filter(
        TransactionHistory.created_at >= since
    ).group_by(
        func.date(TransactionHistory.created_at),
        TransactionHistory.tag
    ).order_by('day').all()

    daily = {}
    for day, tag, total in results:
        key = str(day)
        if key not in daily:
            daily[key] = {'date': key, 'in': 0.0, 'out': 0.0}
        daily[key][tag] = round(float(total), 2)

    return jsonify({'success': True, 'data': list(daily.values())})


# ── ALL TRANSACTIONS ──────────────────────────────────────────────
@admin_bp.route('/transactions', methods=['GET'])
@login_required
def transactions():
    err = _admin_required() or _permission_required('view_revenue')
    if err: return err

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    txns = TransactionHistory.query\
        .order_by(TransactionHistory.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        'success': True,
        'data': [t.to_dict() for t in txns.items],
        'total': txns.total,
        'pages': txns.pages,
        'page': page,
    })


# ── USER MANAGEMENT ───────────────────────────────────────────────
@admin_bp.route('/users', methods=['GET'])
@login_required
def list_users():
    err = _admin_required() or _permission_required('view_users')
    if err: return err
    query = request.args.get('search', '').strip()
    q = User.query
    if current_user.is_support():
        q = q.join(Role).filter(Role.tag.notin_(['admin', 'superuser']))
    if query:
        search = f'%{query}%'
        q = q.filter(
            (User.name.ilike(search)) |
            (User.username.ilike(search)) |
            (User.email.ilike(search))
        )
    users = q.order_by(User.created_at.desc()).all()
    return jsonify({'success': True, 'data': [u.to_dict() for u in users]})


@admin_bp.route('/users', methods=['POST'])
@login_required
def create_user():
    err = _admin_required() or _permission_required('manage_users')
    if err: return err
    data = request.get_json() or {}
    required = ['name', 'username', 'email', 'password', 'role_tag']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'success': False, 'error': f'"{field}" is required.'}), 400

    if len(data['password']) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters.'}), 400

    if User.query.filter_by(username=data['username'].strip()).first():
        return jsonify({'success': False, 'error': 'Username already taken.'}), 409

    if User.query.filter_by(email=data['email'].strip().lower()).first():
        return jsonify({'success': False, 'error': 'Email already registered.'}), 409

    role = Role.query.filter_by(tag=data['role_tag'].strip()).first()
    if not role:
        return jsonify({'success': False, 'error': 'Role not found.'}), 404

    if role.tag == 'superuser' and current_user.role.tag != 'superuser':
        return jsonify({'success': False, 'error': 'Only superusers can create superuser accounts.'}), 403

    pw_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        name=data['name'].strip(),
        username=data['username'].strip(),
        email=data['email'].strip().lower(),
        password=pw_hash,
        role_id=role.id,
        region=data.get('region', '').strip() or None,
    )
    db.session.add(user)
    db.session.flush()

    db.session.add(Wallet(user_id=user.id, balance=0.0))
    db.session.commit()

    return jsonify({'success': True, 'user': user.to_dict()}), 201


@admin_bp.route('/users/<int:user_id>/disable', methods=['POST', 'GET'])
@login_required
def disable_user(user_id):
    err = _admin_required() or _permission_required('modify_user_status')
    if err: return err
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': "You cannot disable your own account."}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user)
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    user.is_active = False
    db.session.commit()
    return jsonify({'success': True, 'message': f'{user.name} disabled.'})


@admin_bp.route('/users/<int:user_id>/enable', methods=['POST', 'GET'])
@login_required
def enable_user(user_id):
    err = _admin_required() or _permission_required('modify_user_status')
    if err: return err
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user)
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    user.is_active = True
    db.session.commit()
    return jsonify({'success': True, 'message': f'{user.name} enabled.'})


@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    err = _admin_required() or _permission_required('manage_users')
    if err: return err
    if user_id == current_user.id:
        return jsonify({'success': False, 'error': "You cannot delete your own account."}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user)
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'success': True, 'message': f'User {user.name} deleted.'})


@admin_bp.route('/users/<int:user_id>/role', methods=['PUT'])
@login_required
def change_role(user_id):
    err = _admin_required() or _permission_required('manage_users')
    if err: return err
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user)
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    data = request.get_json() or {}
    role = Role.query.filter_by(tag=data.get('role_tag', '')).first()
    if not role:
        return jsonify({'success': False, 'error': 'Role not found.'}), 404
    if role.tag == 'superuser' and current_user.role.tag != 'superuser':
        return jsonify({'success': False, 'error': 'Only superusers can assign superuser role.'}), 403
    if current_user.role.tag == 'support' and role.tag != 'client':
        return jsonify({'success': False, 'error': 'Support may only assign client roles.'}), 403
    if current_user.role.tag == 'admin' and role.tag == 'superuser':
        return jsonify({'success': False, 'error': 'Admin cannot assign superuser role.'}), 403
    user.role_id = role.id
    db.session.commit()
    return jsonify({'success': True, 'user': user.to_dict()})


@admin_bp.route('/users/<int:user_id>/transactions', methods=['GET'])
@login_required
def user_transactions(user_id):
    err = _admin_required() or _permission_required('view_transactions')
    if err: return err
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user, action='view')
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    txns = TransactionHistory.query.filter_by(user_id=user_id).order_by(TransactionHistory.created_at.desc()).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in txns]})


@admin_bp.route('/users/<int:user_id>/payments', methods=['GET'])
@login_required
def user_payments(user_id):
    err = _admin_required() or _permission_required('view_transactions')
    if err: return err
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    allowed, message = _current_user_can_manage_target(user, action='view')
    if not allowed:
        return jsonify({'success': False, 'error': message}), 403
    payments = Payment.query.filter_by(user_id=user_id).order_by(Payment.payment_time.desc()).all()
    return jsonify({'success': True, 'data': [p.to_dict() for p in payments]})


@admin_bp.route('/users/<int:user_id>/refund', methods=['POST'])
@login_required
def refund_user_payment(user_id):
    err = _admin_required() or _permission_required('process_refund')
    if err: return err
    data = request.get_json() or {}
    payment = None
    if data.get('payment_id'):
        payment = db.session.get(Payment, data['payment_id'])
    elif data.get('transaction_id'):
        payment = Payment.query.filter_by(transaction_id=data['transaction_id']).first()
    if not payment or payment.user_id != user_id:
        return jsonify({'success': False, 'error': 'Payment not found.'}), 404
    if payment.is_refunded:
        return jsonify({'success': False, 'error': 'Payment has already been refunded.'}), 400
    wallet = payment.user.wallet
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0.0)
        db.session.add(wallet)
        db.session.flush()
    wallet.credit(
        amount=payment.amount,
        reference=f'REFUND-{payment.transaction_id}',
        money_system='refund'
    )
    payment.is_refunded = True
    db.session.commit()
    return jsonify({
        'success': True,
        'message': f'Refunded KES {payment.amount:.2f} to {payment.user.name}.',
        'payment': payment.to_dict(),
        'new_balance': wallet.balance,
    })


# ── DOC GENERATION STATS ──────────────────────────────────────────
@admin_bp.route('/doc-stats', methods=['GET'])
@login_required
def doc_stats():
    err = _admin_required() or _permission_required('view_revenue')
    if err: return err
    stats = db.session.query(
        GeneratedDocument.subject_name,
        GeneratedDocument.grade,
        GeneratedDocument.curriculum_system,
        func.count(GeneratedDocument.id).label('count')
    ).group_by(
        GeneratedDocument.subject_name,
        GeneratedDocument.grade,
        GeneratedDocument.curriculum_system
    ).order_by(func.count(GeneratedDocument.id).desc()).limit(20).all()

    return jsonify({'success': True, 'data': [
        {'subject': s, 'grade': g, 'system': cs, 'count': c}
        for s, g, cs, c in stats
    ]})


# ── USER ACTIVITY ─────────────────────────────────────────────────
@admin_bp.route('/users/<int:user_id>/activity', methods=['GET'])
@login_required
def user_activity(user_id):
    err = _admin_required() or _permission_required('view_users')
    if err: return err
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'success': False, 'error': 'User not found.'}), 404
    history = UserHistory.query.filter_by(user_id=user_id)\
        .order_by(UserHistory.last_visited.desc()).all()
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'activity': [h.to_dict() for h in history],
    })
