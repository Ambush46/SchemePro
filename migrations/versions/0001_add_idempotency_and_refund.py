"""add idempotency keys and payment refund flag

Revision ID: 0001_add_idempotency_and_refund
Revises: 
Create Date: 2026-05-30 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_add_idempotency_and_refund'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add idempotency_key to wallet_transactions
    with op.batch_alter_table('wallet_transactions') as batch_op:
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=100), nullable=True))
    # Create unique index for idempotency_key on wallet_transactions
    op.create_index('uq_wallet_transactions_idempotency_key', 'wallet_transactions', ['idempotency_key'], unique=True)

    # Add idempotency_key and is_refunded to payments
    with op.batch_alter_table('payments') as batch_op:
        batch_op.add_column(sa.Column('idempotency_key', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('is_refunded', sa.Boolean(), nullable=False, server_default=sa.text('0')))
    # Create unique index for idempotency_key on payments
    op.create_index('uq_payments_idempotency_key', 'payments', ['idempotency_key'], unique=True)


def downgrade():
    # Drop indexes then columns
    try:
        op.drop_index('uq_payments_idempotency_key', table_name='payments')
    except Exception:
        pass
    with op.batch_alter_table('payments') as batch_op:
        batch_op.drop_column('is_refunded')
        batch_op.drop_column('idempotency_key')

    try:
        op.drop_index('uq_wallet_transactions_idempotency_key', table_name='wallet_transactions')
    except Exception:
        pass
    with op.batch_alter_table('wallet_transactions') as batch_op:
        batch_op.drop_column('idempotency_key')
