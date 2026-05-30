"""
CONTROLLER: Authentication
Handles /auth/login, /auth/register, /auth/logout
"""
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, bcrypt
from app.models.user import User
from app.models.role import Role
from app.models.wallet import Wallet

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    """POST /auth/register  — Create a new client account."""
    data = request.get_json()

    # ── Validation ─────────────────────────────────────────────────
    required = ['name', 'username', 'email', 'password']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'success': False, 'error': f'"{field}" is required.'}), 400

    if len(data['password']) < 8:
        return jsonify({'success': False, 'error': 'Password must be at least 8 characters.'}), 400

    if data['password'] != data.get('confirm_password', ''):
        return jsonify({'success': False, 'error': 'Passwords do not match.'}), 400

    if User.query.filter_by(username=data['username'].strip()).first():
        return jsonify({'success': False, 'error': 'Username already taken.'}), 409

    if User.query.filter_by(email=data['email'].strip().lower()).first():
        return jsonify({'success': False, 'error': 'Email already registered.'}), 409

    # ── Create user ────────────────────────────────────────────────
    client_role = Role.query.filter_by(tag='client').first()
    if not client_role:
        return jsonify({'success': False, 'error': 'System configuration error.'}), 500

    pw_hash = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        name=data['name'].strip(),
        username=data['username'].strip(),
        email=data['email'].strip().lower(),
        password=pw_hash,
        role_id=client_role.id,
        region=data.get('region', '').strip() or None,
    )
    db.session.add(user)
    db.session.flush()  # get user.id

    # Create wallet for the new user
    db.session.add(Wallet(user_id=user.id, balance=0.0))
    db.session.commit()

    login_user(user, remember=False)
    user.last_login = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({'success': True, 'user': user.to_dict()}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """POST /auth/login — Authenticate user."""
    data = request.get_json()
    identifier = data.get('username', '').strip()
    password = data.get('password', '')

    if not identifier or not password:
        return jsonify({'success': False, 'error': 'Username/email and password are required.'}), 400

    # Allow login by username or email
    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({'success': False, 'error': 'Invalid credentials. Please try again.'}), 401

    if not user.is_active:
        return jsonify({'success': False, 'error': 'Your account has been disabled. Contact support.'}), 403

    login_user(user, remember=data.get('remember', False))
    user.last_login = datetime.now(timezone.utc)
    user.last_active = datetime.now(timezone.utc)
    db.session.commit()

    # Ensure wallet exists (edge case for seeded users)
    if not user.wallet:
        db.session.add(Wallet(user_id=user.id, balance=0.0))
        db.session.commit()

    return jsonify({'success': True, 'user': user.to_dict()}), 200


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """POST /auth/logout — Log out and record logout time."""
    current_user.last_logout = datetime.now(timezone.utc)
    db.session.commit()
    logout_user()
    return jsonify({'success': True, 'message': 'Logged out successfully.'}), 200


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """GET /auth/me — Return current user profile."""
    return jsonify({'success': True, 'user': current_user.to_dict()}), 200
