"""Encrypted, operator-only sales inquiries. No existing data is changed."""
from alembic import op
import sqlalchemy as sa

revision = "0016_sales_leads"
down_revision = "0015_api_token_rls_lookup"
branch_labels = None
depends_on = None


def upgrade():
    # Legacy bootstrap migrations use current ORM metadata on fresh databases.
    if sa.inspect(op.get_bind()).has_table('sales_leads'):
        columns = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('sales_leads')}
        if not {'id', 'details_encrypted', 'created_at'} <= columns:
            raise RuntimeError('Existing sales_leads schema does not match migration')
        return
    op.create_table('sales_leads',
        sa.Column('id', sa.Uuid(), primary_key=True),
        sa.Column('details_encrypted', sa.LargeBinary(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('sales_leads')
