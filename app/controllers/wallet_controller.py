"""
CONTROLLER: Wallet
Handles top-up and balance queries.
POST /wallet/topup   — Add funds (M-Pesa, Pesapal, Card, Bank)
GET  /wallet/balance — Current balance
GET  /wallet/history — Transaction history for current user
"""
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.wallet import Wallet, WalletTransaction, TransactionHistory

wallet_bp = Blueprint('wallet', __name__)


@wallet_bp.route('/balance', methods=['GET'])
@login_required
def balance():
    """GET /wallet/balance"""
    wallet = current_user.wallet
    return jsonify({
        'success': True,
        'balance': wallet.balance if wallet else 0.0,
    })


@wallet_bp.route('/topup', methods=['POST'])
@login_required
def topup():
    """
    POST /wallet/topup
    Body: { amount: float, method: 'mpesa'|'pesapal'|'card'|'bank', reference: str }
    In production, reference would be verified against payment gateway callback.
    """
    data = request.get_json()
    amount = float(data.get('amount', 0))
    method = data.get('method', 'mpesa').strip().lower()
    reference = data.get('reference', '').strip()

    # ── Validation ─────────────────────────────────────────────────
    if amount < 1:
        return jsonify({'success': False, 'error': 'Minimum top-up is KES 1.'}), 400

    VALID_METHODS = ('mpesa', 'pesapal', 'card', 'bank')
    if method not in VALID_METHODS:
        return jsonify({'success': False, 'error': f'Invalid payment method. Use one of: {VALID_METHODS}'}), 400

    if not reference:
        # In dev, generate a dummy reference
        import uuid
        reference = f'{method.upper()}-{str(uuid.uuid4())[:8].upper()}'

    # ── Ensure wallet exists ───────────────────────────────────────
    wallet = current_user.wallet
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0.0)
        db.session.add(wallet)
        db.session.flush()

    idempotency_key = data.get('idempotency_key')
    if idempotency_key:
        existing_txn = WalletTransaction.query.filter_by(
            user_id=current_user.id,
            idempotency_key=idempotency_key,
            amount=amount,
            money_system=method
        ).first()
        if existing_txn:
            return jsonify({
                'success': True,
                'message': 'Top-up already processed.',
                'new_balance': wallet.balance,
                'reference': existing_txn.reference,
                'transaction_id': existing_txn.transaction_id,
            })

    # ── Credit wallet ──────────────────────────────────────────────
    try:
        wallet.credit(amount=amount, reference=reference, money_system=method, idempotency_key=idempotency_key)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

    current_user.record_activity('wallet_topup')

    return jsonify({
        'success': True,
        'message': f'KES {amount:.2f} added via {method.upper()}.',
        'new_balance': wallet.balance,
        'reference': reference,
    })


@wallet_bp.route('/history', methods=['GET'])
@login_required
def history():
    """GET /wallet/history — Last 50 transactions for current user."""
    txns = TransactionHistory.query\
        .filter_by(user_id=current_user.id)\
        .order_by(TransactionHistory.created_at.desc())\
        .limit(50).all()
    return jsonify({'success': True, 'data': [t.to_dict() for t in txns]})
