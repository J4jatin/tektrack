"""TekTrack - SQLite database setup and XML ingestion."""
import os
import tempfile
import pathlib
import sqlite3
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime

DB_PATH = Path(os.environ.get("TEKTRACK_DB", str(pathlib.Path(tempfile.gettempdir()) / "tektrack.db")))

VALID_STATUSES = [
    "ORDER_RECEIVED", "DESIGN_REVIEW", "MASK_WRITING",
    "QUALITY_CHECK", "APPROVED", "SHIPPED", "DELIVERED",
]

STATUS_TRANSITIONS = {
    "ORDER_RECEIVED": ["DESIGN_REVIEW"],
    "DESIGN_REVIEW": ["MASK_WRITING", "ORDER_RECEIVED"],
    "MASK_WRITING": ["QUALITY_CHECK"],
    "QUALITY_CHECK": ["APPROVED", "MASK_WRITING"],
    "APPROVED": ["SHIPPED"],
    "SHIPPED": ["DELIVERED"],
    "DELIVERED": [],
}


def get_connection(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(db_path=None):
    if db_path is None:
        db_path = DB_PATH
    with get_connection(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                id          TEXT PRIMARY KEY,
                customer    TEXT NOT NULL,
                mask_type   TEXT NOT NULL,
                layer       TEXT NOT NULL,
                quantity    INTEGER NOT NULL CHECK(quantity > 0),
                priority    TEXT NOT NULL CHECK(priority IN ('NORMAL','HIGH','CRITICAL')),
                status      TEXT NOT NULL,
                engineer    TEXT NOT NULL,
                notes       TEXT DEFAULT '',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS status_log (
                log_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id    TEXT NOT NULL REFERENCES orders(id),
                old_status  TEXT,
                new_status  TEXT NOT NULL,
                changed_at  TEXT NOT NULL,
                changed_by  TEXT DEFAULT 'system'
            );
        """)


def ingest_xml(xml_path, db_path=None):
    if db_path is None:
        db_path = DB_PATH
    tree = ET.parse(xml_path)
    root = tree.getroot()
    inserted = updated = skipped = 0
    with get_connection(db_path) as conn:
        for el in root.findall("order"):
            oid = el.get("id")
            if not oid:
                skipped += 1
                continue
            status = el.findtext("status", "ORDER_RECEIVED")
            if status not in VALID_STATUSES:
                skipped += 1
                continue
            priority = el.findtext("priority", "NORMAL")
            if priority not in ("NORMAL", "HIGH", "CRITICAL"):
                skipped += 1
                continue
            data = {
                "id": oid,
                "customer": el.findtext("customer", ""),
                "mask_type": el.findtext("mask_type", ""),
                "layer": el.findtext("layer", ""),
                "quantity": int(el.findtext("quantity", "1")),
                "priority": priority,
                "status": status,
                "engineer": el.findtext("engineer", ""),
                "notes": el.findtext("notes", ""),
                "created_at": el.findtext("created_at", datetime.now().isoformat()),
                "updated_at": el.findtext("updated_at", datetime.now().isoformat()),
            }
            existing = conn.execute("SELECT status FROM orders WHERE id=?", (oid,)).fetchone()
            if existing is None:
                conn.execute(
                    "INSERT INTO orders VALUES "
                    "(:id,:customer,:mask_type,:layer,:quantity,:priority,:status,:engineer,:notes,:created_at,:updated_at)",
                    data
                )
                conn.execute(
                    "INSERT INTO status_log(order_id,old_status,new_status,changed_at) VALUES(?,?,?,?)",
                    (oid, None, status, datetime.now().isoformat())
                )
                inserted += 1
            else:
                old_status = existing["status"]
                conn.execute(
                    "UPDATE orders SET customer=:customer,mask_type=:mask_type,layer=:layer,"
                    "quantity=:quantity,priority=:priority,status=:status,engineer=:engineer,"
                    "notes=:notes,updated_at=:updated_at WHERE id=:id",
                    data
                )
                if old_status != status:
                    conn.execute(
                        "INSERT INTO status_log(order_id,old_status,new_status,changed_at) VALUES(?,?,?,?)",
                        (oid, old_status, status, datetime.now().isoformat())
                    )
                updated += 1
    return {"inserted": inserted, "updated": updated, "skipped": skipped}
