"""Regression tests for defects found in the launch audit."""
import io
import zipfile
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy import func, select
from app.core.startup_checks import ConfigurationError, assert_safe_database_role
from app.services import ingestion
from app.models import Product


@pytest.mark.parametrize('value', ['1.5', 'NaN', 'Infinity', '-1', '2147483648'])
def test_invalid_inventory_quantities(value):
    result = ingestion.validate_rows('inventory', [{'warehouse_name': 'W', 'product_sku': 'P', 'quantity': value}],
        {'warehouse_name': 'warehouse_name', 'product_sku': 'product_sku', 'quantity': 'quantity'})
    assert result['rejected'] == 1


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1'])
def test_invalid_product_cost(value):
    result = ingestion.validate_rows('products', [{'sku': 'P', 'name': 'Product', 'unit_cost': value, 'unit_price': '5'}],
        {k: k for k in ['sku', 'name', 'unit_cost', 'unit_price']})
    assert result['rejected'] == 1


@pytest.mark.parametrize('content', [b'a,a\n1,2', b'a,b\n1,2,3', b'a\n\xff', b'a\n\x00'])
def test_malformed_csv(content):
    with pytest.raises(ValueError):
        ingestion.parse_upload('file.csv', content)


def test_workbook_expansion_limit(monkeypatch):
    monkeypatch.setattr(ingestion, 'MAX_EXPANDED_BYTES', 100)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('large.xml', 'a' * 101)
    with pytest.raises(ValueError, match='expanded'):
        ingestion.parse_upload('file.xlsx', data.getvalue())


def test_excel_values_and_formula_rejection():
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.append(['sku', 'name', 'unit_cost', 'unit_price'])
    ws.append(['P', 'Product', 2, 5])
    out = io.BytesIO(); wb.save(out)
    assert ingestion.parse_upload('data.xlsx', out.getvalue())['rows'][0]['sku'] == 'P'
    ws['C2'] = '=1+1'
    out = io.BytesIO(); wb.save(out)
    with pytest.raises(ValueError, match='formulas'):
        ingestion.parse_upload('data.xlsx', out.getvalue())


@pytest.mark.parametrize('mapping', ['[]', '{', '{"sku": 4}', 'null'])
def test_invalid_mapping_is_client_error(owner_client, mapping):
    response = owner_client.post('/api/v1/data/import/preview',
        data={'entity': 'products', 'mapping': mapping},
        files={'file': ('products.csv', b'sku,name,unit_cost,unit_price\nA,Alpha,2,5', 'text/csv')})
    assert response.status_code == 400


def test_duplicate_import_preserves_valid_rows(db, org_a):
    org, _ = org_a
    rows = [{'sku': sku, 'name': 'Product', 'unit_cost': '2', 'unit_price': '5'} for sku in ['A', 'A', 'B']]
    result = ingestion.commit_import(db, organization_id=org.id, entity='products', rows=rows,
        mapping={k: k for k in rows[0]}, source_name='test.csv', source_type='csv')
    assert result['rows_imported'] == 2
    assert result['rows_rejected'] == 1
    assert 'INSERT' not in str(result['errors'])
    assert db.scalar(select(func.count()).select_from(Product).where(Product.organization_id == org.id)) == 2


@pytest.mark.parametrize('superuser,bypass', [(True, False), (False, True)])
def test_runtime_database_bypass_is_rejected(superuser, bypass):
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.return_value.one.return_value = SimpleNamespace(rolsuper=superuser, rolbypassrls=bypass)
    with pytest.raises(ConfigurationError):
        assert_safe_database_role(engine)


def test_unknown_carrier_does_not_simulate_other_shipments(db, tenant_ctx, shipment_a):
    from app.services.simulation_engine import run_simulation
    from app.schemas.entities import SimulationRequest
    result = run_simulation(db, SimulationRequest(simulation_type='transportation_disruption', carrier='UNKNOWN-CARRIER', duration_days=3, severity=0.5))
    assert result['impacts']['revenue_impact_usd'] == 0


def test_legacy_jwt_helper_round_trip_and_tamper(monkeypatch):
    from app.core.config import settings
    from app.core.security import create_access_token, decode_token
    monkeypatch.setattr(settings, 'JWT_SECRET_KEY', 'test-key-with-at-least-thirty-two-characters')
    token = create_access_token('123', 'viewer')
    assert decode_token(token)['sub'] == '123'
    assert decode_token(token + 'tampered') is None


def test_enterprise_jobs_reject_unsigned_production_payloads(monkeypatch):
    import asyncio
    from app.core.config import settings
    from app.jobs.enterprise import run_workflow, generate_org_predictions
    monkeypatch.setattr(settings, 'ENVIRONMENT', 'production')
    with pytest.raises(PermissionError, match='Missing signature'):
        asyncio.run(run_workflow(None, '00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002'))
    with pytest.raises(PermissionError, match='Missing signature'):
        asyncio.run(generate_org_predictions(None, '00000000-0000-0000-0000-000000000001'))


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql'])
def test_provider_database_urls_use_installed_driver(scheme):
    from app.core.config import Settings
    config = Settings(_env_file=None, DATABASE_URL=f'{scheme}://user:p%40ss@localhost/db')
    assert config.DATABASE_URL == 'postgresql+psycopg://user:p%40ss@localhost/db'
