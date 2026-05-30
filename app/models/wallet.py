"""
MODELS: Wallet, WalletTransaction, Payment, TransactionHistory
Financial models for the SchemePro payment system.

Flow:
  User tops up → WalletTransaction (credit) → Wallet.balance increases
  User downloads → Payment (debit) → Wallet.balance decreases
  Both write to TransactionHistory for admin reporting.
"""
import uuid
from datetime import datetime, timezone
from app import db


def _new_uuid():
    """Generate a sequential UUID (UUID v4 for now; use uuid6 lib in prod for true sequential)."""
    return str(uuid.uuid4())


class Wallet(db.Model):
    """One wallet per user. Acts as a running balance ledger."""
    __tablename__ = 'wallets'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0.0, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True),
                           default=lambda: datetime.now(timezone.utc),
                           onupdate=lambda: datetime.now(timezone.utc))

    def credit(self, amount: float, reference: str, money_system: str, idempotency_key: str = None, session=None):
        """Add funds to wallet and record in WalletTransaction + TransactionHistory."""
        if amount <= 0:
            raise ValueError('Credit amount must be positive.')
        self.balance += round(amount, 2)
        txn = WalletTransaction(
            transaction_id=_new_uuid(),
            user_id=self.user_id,
            amount=amount,
            reference=reference,
            money_system=money_system,
            idempotency_key=idempotency_key,
            tag='credit',
        )
        hist = TransactionHistory(
            transaction_number=_new_uuid(),
            user_id=self.user_id,
            amount=amount,
            tag='in',
            source='wallet_topup',
        )
        db.session.add_all([txn, hist])
        return txn

    def debit(self, amount: float, doc_type: str, idempotency_key: str = None, session=None):
        """Deduct funds for a document download. Raises if insufficient."""
        if amount <= 0:
            raise ValueError('Debit amount must be positive.')
        if self.balance < amount:
            raise ValueError('Insufficient balance for payment.')
        self.balance = round(self.balance - amount, 2)
        payment = Payment(
            transaction_id=_new_uuid(),
            user_id=self.user_id,
            amount=amount,
            doc_type=doc_type,
            balance_after=self.balance,
            idempotency_key=idempotency_key,
        )
        hist = TransactionHistory(
            transaction_number=_new_uuid(),
            user_id=self.user_id,
            amount=amount,
            tag='out',
            source=f'download_{doc_type}',
        )
        db.session.add_all([payment, hist])
        return payment

    def to_dict(self):
        return {'user_id': self.user_id, 'balance': round(self.balance, 2),
                'updated_at': self.updated_at.isoformat() if self.updated_at else None}


class WalletTransaction(db.Model):
    """Records every top-up into the wallet."""
    __tablename__ = 'wallet_transactions'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(40), unique=True, nullable=False, default=_new_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    reference = db.Column(db.String(100), nullable=True)    # M-Pesa ref, Pesapal ref, etc.
    money_system = db.Column(db.String(30), nullable=False) # 'mpesa', 'pesapal', 'card', 'bank'
    idempotency_key = db.Column(db.String(100), unique=True, nullable=True)
    tag = db.Column(db.String(10), default='credit')        # always 'credit' here
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'amount': self.amount,
            'reference': self.reference,
            'money_system': self.money_system,
            'idempotency_key': self.idempotency_key,
            'tag': self.tag,
            'created_at': self.created_at.isoformat(),
        }


class Payment(db.Model):
    """Records every document download payment (debit from wallet)."""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(40), unique=True, nullable=False, default=_new_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    doc_type = db.Column(db.String(10), nullable=False)     # 'pdf', 'docx', 'zip'
    balance_after = db.Column(db.Float, nullable=False)     # Wallet balance after deduction
    payment_time = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    idempotency_key = db.Column(db.String(100), unique=True, nullable=True)
    is_refunded = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return {
            'transaction_id': self.transaction_id,
            'amount': self.amount,
            'doc_type': self.doc_type,
            'balance_after': self.balance_after,
            'payment_time': self.payment_time.isoformat(),
            'idempotency_key': self.idempotency_key,
            'is_refunded': self.is_refunded,
        }


class TransactionHistory(db.Model):
    """
    Unified view of all financial activity (credits + debits).
    Admin uses this for revenue reporting.
    """
    __tablename__ = 'transaction_history'

    id = db.Column(db.Integer, primary_key=True)
    transaction_number = db.Column(db.String(40), unique=True, nullable=False, default=_new_uuid)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tag = db.Column(db.String(5), nullable=False)    # 'in' (deposit) | 'out' (payment)
    source = db.Column(db.String(50), nullable=True) # 'wallet_topup' | 'download_pdf' etc.
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'transaction_number': self.transaction_number,
            'amount': self.amount,
            'tag': self.tag,
            'source': self.source,
            'user': self.user.name if self.user else None,
            'created_at': self.created_at.isoformat(),
        }
