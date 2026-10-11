"""Register the SAP Business One connector type."""
from alembic import op

revision = "0017_sap_business_one"
down_revision = "0016_sales_leads"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name == "postgresql":
        # SQLAlchemy SAEnum(ConnectorType) persists member names.
        op.execute("ALTER TYPE connector_type ADD VALUE IF NOT EXISTS 'SAP_BUSINESS_ONE'")


def downgrade():
    # Retain the enum value to avoid deleting configured connections.
    pass
