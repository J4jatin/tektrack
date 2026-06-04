"""TekTrack - Orders CRUD routes."""
from fastapi import APIRouter, HTTPException, Query
from datetime import datetime
from typing import Optional, List
import backend.database as db_module
from backend.database import VALID_STATUSES, STATUS_TRANSITIONS
from backend.models import OrderCreate, StatusUpdate, OrderResponse, StatusLogEntry

router = APIRouter(prefix="/orders", tags=["orders"])


def _conn():
    return db_module.get_connection()


@router.get("/", response_model=List[OrderResponse])
def list_orders(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    customer: Optional[str] = Query(None),
):
    query = "SELECT * FROM orders WHERE 1=1"
    params = []
    if status:
        if status not in VALID_STATUSES:
            raise HTTPException(400, f"Invalid status: {status}")
        query += " AND status=?"
        params.append(status)
    if priority:
        query += " AND priority=?"
        params.append(priority.upper())
    if customer:
        query += " AND customer LIKE ?"
        params.append(f"%{customer}%")
    query += " ORDER BY CASE priority WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END, updated_at DESC"
    with _conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: str):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    if not row:
        raise HTTPException(404, f"Order {order_id} not found")
    return dict(row)


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(order: OrderCreate):
    now = datetime.now().isoformat()
    with _conn() as conn:
        if conn.execute("SELECT id FROM orders WHERE id=?", (order.id,)).fetchone():
            raise HTTPException(409, f"Order {order.id} already exists")
        conn.execute(
            "INSERT INTO orders (id,customer,mask_type,layer,quantity,priority,status,engineer,notes,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (order.id, order.customer, order.mask_type, order.layer, order.quantity,
             order.priority, "ORDER_RECEIVED", order.engineer, order.notes or "", now, now)
        )
        conn.execute(
            "INSERT INTO status_log(order_id,old_status,new_status,changed_at) VALUES(?,?,?,?)",
            (order.id, None, "ORDER_RECEIVED", now)
        )
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order.id,)).fetchone()
    return dict(row)


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_status(order_id: str, payload: StatusUpdate):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Order {order_id} not found")
        current = row["status"]
        allowed = STATUS_TRANSITIONS.get(current, [])
        if payload.new_status not in allowed:
            raise HTTPException(400, f"Invalid transition: {current} -> {payload.new_status}. Allowed: {allowed}")
        now = datetime.now().isoformat()
        conn.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (payload.new_status, now, order_id))
        conn.execute(
            "INSERT INTO status_log(order_id,old_status,new_status,changed_at,changed_by) VALUES(?,?,?,?,?)",
            (order_id, current, payload.new_status, now, payload.changed_by)
        )
        updated = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    return dict(updated)


@router.get("/{order_id}/log", response_model=List[StatusLogEntry])
def get_status_log(order_id: str):
    with _conn() as conn:
        if not conn.execute("SELECT id FROM orders WHERE id=?", (order_id,)).fetchone():
            raise HTTPException(404, f"Order {order_id} not found")
        logs = conn.execute(
            "SELECT * FROM status_log WHERE order_id=? ORDER BY changed_at ASC", (order_id,)
        ).fetchall()
    return [dict(l) for l in logs]


@router.delete("/{order_id}", status_code=204)
def delete_order(order_id: str):
    with _conn() as conn:
        row = conn.execute("SELECT status FROM orders WHERE id=?", (order_id,)).fetchone()
        if not row:
            raise HTTPException(404, f"Order {order_id} not found")
        if row["status"] != "ORDER_RECEIVED":
            raise HTTPException(400, "Only ORDER_RECEIVED orders can be deleted")
        conn.execute("DELETE FROM status_log WHERE order_id=?", (order_id,))
        conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
