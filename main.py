"""TekTrack - FastAPI entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pathlib import Path
from backend.database import init_db, ingest_xml


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        xml_path = Path(__file__).parent / "backend" / "data" / "sample_orders.xml"
        if xml_path.exists():
            result = ingest_xml(xml_path)
            print(f"[TekTrack] Seeded DB: {result}")
    except Exception as e:
        print(f"[TekTrack] Warning: DB init skipped ({e})")
    yield


app = FastAPI(title="TekTrack API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

from backend.routes.orders import router as orders_router
from backend.routes.analytics import router as analytics_router
app.include_router(orders_router)
app.include_router(analytics_router)


@app.get("/", tags=["health"])
def root():
    return {"status": "ok", "service": "TekTrack API", "version": "1.0.0"}


@app.get("/health", tags=["health"])
def health():
    return {"status": "healthy"}
