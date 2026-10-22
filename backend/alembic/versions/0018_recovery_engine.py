"""Add recovery source records and human decision snapshots, with FORCE RLS.

Existing operational tables and rows are unchanged. Downgrade removes only the
new module's tables and therefore requires an explicit data-retention decision.
"""
from alembic import op
import sqlalchemy as sa
revision='0018_recovery_engine'
down_revision='0017_sap_business_one'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    common=lambda:[sa.Column('id',sa.Uuid(),primary_key=True),sa.Column('organization_id',sa.Uuid(),sa.ForeignKey('organizations.id',ondelete='CASCADE'),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.Column('updated_at',sa.DateTime(timezone=True),nullable=False)]
    if not sa.inspect(bind).has_table('recovery_records'):
        op.create_table('recovery_records',*common(),sa.Column('kind',sa.String(32),nullable=False),sa.Column('source_key',sa.String(160),nullable=False),sa.Column('data',sa.JSON(),nullable=False),sa.UniqueConstraint('organization_id','kind','source_key'))
        op.create_index('ix_recovery_records_organization_id','recovery_records',['organization_id'])
    if not sa.inspect(bind).has_table('recovery_cases'):
        op.create_table('recovery_cases',*common(),sa.Column('incident_id',sa.Uuid(),sa.ForeignKey('incidents.id'),nullable=False),sa.Column('work_order',sa.String(160),nullable=False),sa.Column('status',sa.String(32),nullable=False),sa.Column('data',sa.JSON(),nullable=False))
        op.create_index('ix_recovery_cases_organization_id','recovery_cases',['organization_id'])
    for name in ('recovery_records','recovery_cases'):
        expected={'id','organization_id','created_at','updated_at','data'}|({'kind','source_key'} if name=='recovery_records' else {'incident_id','work_order','status'})
        if not expected<={c['name'] for c in sa.inspect(bind).get_columns(name)}:raise RuntimeError('Recovery table schema does not match migration')
        if bind.dialect.name=='postgresql':
            op.execute(sa.text(f'ALTER TABLE {name} ENABLE ROW LEVEL SECURITY'))
            op.execute(sa.text(f'ALTER TABLE {name} FORCE ROW LEVEL SECURITY'))
            existing=bind.execute(sa.text('SELECT policyname FROM pg_policies WHERE tablename=:name'),{'name':name}).scalars().all()
            if not existing:
                op.execute(sa.text(f"CREATE POLICY tenant_isolation ON {name} USING (organization_id = NULLIF(current_setting('app.current_org_id',true),'')::uuid) WITH CHECK (organization_id = NULLIF(current_setting('app.current_org_id',true),'')::uuid)"))

def downgrade():
    op.drop_table('recovery_cases')
    op.drop_table('recovery_records')
