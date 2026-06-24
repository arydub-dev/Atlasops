"""Pytest fixtures: isolated SQLite DB, seeded data, and an authenticated client."""
import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./_test.db")
os.environ.setdefault("SEED_ON_STARTUP", "false")

import pytest
from fastapi.testclient import TestClient

from app.cli import init_db
from app.core.database import Base, SessionLocal, engine
from app.main import app
from app.seed import synthetic


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    synthetic.seed_all(
        db,
        n_suppliers=8,
        n_products=10,
        n_warehouses=4,
        n_shipments=120,
        inventory_history_snapshots=1,
        verbose=False,
    )
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    if os.path.exists("_test.db"):
        os.remove("_test.db")


@pytest.fixture()
def client():
    return TestClient(app)


def _token(client: TestClient, email: str, password: str) -> str:
    r = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture()
def ops_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'ops@scc.io', 'ops12345')}"}


@pytest.fixture()
def analyst_headers(client):
    return {"Authorization": f"Bearer {_token(client, 'analyst@scc.io', 'analyst123')}"}
