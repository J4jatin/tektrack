"""TekTrack - Analytics routes."""
from fastapi import APIRouter
import backend.database as db_module
from backend.database import VALID_STATUSES
from backend.models import AnalyticsSummary

router = APIRouter(prefix="/analytics", tags=["analytics"])


def _conn():
    return db_module.get_connection()


@router.get("/summary", response_model=AnalyticsSummary)
def get_summary():
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        by_status = {s: 0 for s in VALID_STATUSES}
        for row in conn.execute("SELECT status, COUNT(*) as cnt FROM orders GROUP BY status").fetchall():
            by_status[row["status"]] = row["cnt"]
        by_priority = {"NORMAL": 0, "HIGH": 0, "CRITICAL": 0}
        for row in conn.execute("SELECT priority, COUNT(*) as cnt FROM orders GROUP BY priority").fetchall():
            by_priority[row["priority"]] = row["cnt"]
        by_customer = {}
        for row in conn.execute("SELECT customer, COUNT(*) as cnt FROM orders GROUP BY customer ORDER BY cnt DESC").fetchall():
            by_customer[row["customer"]] = row["cnt"]
        critical_ip = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE priority='CRITICAL' AND status NOT IN ('SHIPPED','DELIVERED')"
        ).fetchone()[0]
    return AnalyticsSummary(
        total_orders=total, by_status=by_status, by_priority=by_priority,
        by_customer=by_customer, critical_in_progress=critical_ip,
    )


@router.get("/pipeline")
def get_pipeline():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT id, customer, mask_type, priority, status, engineer, updated_at FROM orders ORDER BY updated_at DESC"
        ).fetchall()
    pipeline = {s: [] for s in VALID_STATUSES}
    for r in rows:
        pipeline[r["status"]].append(dict(r))
    return pipeline


@router.get("/throughput")
def get_throughput():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT strftime('%Y-W%W', updated_at) as week, COUNT(*) as delivered "
            "FROM orders WHERE status='DELIVERED' GROUP BY week ORDER BY week DESC LIMIT 12"
        ).fetchall()
    return [dict(r) for r in rows]
