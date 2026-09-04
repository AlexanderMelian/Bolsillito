"""link transactions to investment transactions

Revision ID: 651d236e3fcc
Revises: ec59ddbb48d2
Create Date: 2026-09-04 12:18:48.410134

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '651d236e3fcc'
down_revision: Union[str, Sequence[str], None] = 'ec59ddbb48d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('transactions', sa.Column('investment_transaction_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'transactions_investment_transaction_id_fkey',
        'transactions', 'investment_transactions', ['investment_transaction_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Alembic autogenerate deja el nombre de la constraint en `None` porque el proyecto no
    # define una naming convention en Base.metadata -- sin nombre explícito, este downgrade
    # falla (Postgres exige un nombre para DROP CONSTRAINT). Se usa el nombre que Postgres le
    # asigna por default (`<tabla>_<columna>_fkey`), verificado con `\d transactions`.
    op.drop_constraint('transactions_investment_transaction_id_fkey', 'transactions', type_='foreignkey')
    op.drop_column('transactions', 'investment_transaction_id')
