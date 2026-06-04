"""TekTrack pytest fixtures — cross-platform temp DBs, no-lifespan test app."""
import pytest
import uuid
import tempfile
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

import backend.database as db_module
from backend.database import init_db, ingest_xml

SAMPLE_XML = Path(__file__).parent.parent / "backend" / "data" / "sample_orders.xml"


def _tmp_db(suffix=""):
    uid = uuid.uuid4().hex[:8]
    return Path(tempfile.gettempdir()) / f"tektrack_{uid}{suffix}.db"


def _make_app():
    from backend.routes.orders import router as orders_router
    from backend.routes.analytics import router as analytics_router
    app = FastAPI(title="TekTrack Test")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    app.include_router(orders_router)
    app.include_router(analytics_router)

    @app.get("/")
    def root():
        return {"status": "ok", "service": "TekTrack API", "version": "1.0.0"}

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
def tmp_db(monkeypatch):
    db = _tmp_db()
    monkeypatch.setattr(db_module, "DB_PATH", db)
    init_db(db)
    yield db
    try:
        db.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture
def seeded_db(monkeypatch):
    db = _tmp_db("_s")
    monkeypatch.setattr(db_module, "DB_PATH", db)
    init_db(db)
    ingest_xml(SAMPLE_XML, db)
    yield db
    try:
        db.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture
def client(seeded_db):
    with TestClient(_make_app()) as c:
        yield c


@pytest.fixture
def empty_client(tmp_db):
    with TestClient(_make_app()) as c:
        yield c
