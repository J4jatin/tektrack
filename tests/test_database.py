"""
TekTrack — Unit tests for database layer (XML ingestion, SQL queries).
"""
import pytest
import xml.etree.ElementTree as ET
from pathlib import Path

from backend.database import init_db, ingest_xml, get_connection, VALID_STATUSES, STATUS_TRANSITIONS


SAMPLE_XML = Path(__file__).parent.parent / "backend" / "data" / "sample_orders.xml"


class TestInitDB:
    def test_creates_orders_table(self, tmp_db):
        with get_connection(tmp_db) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
            names = [t["name"] for t in tables]
        assert "orders" in names
        assert "status_log" in names

    def test_idempotent(self, tmp_db):
        """Calling init_db twice should not raise."""
        init_db(tmp_db)
        init_db(tmp_db)


class TestXMLIngestion:
    def test_ingest_sample_xml(self, tmp_db):
        result = ingest_xml(SAMPLE_XML, tmp_db)
        assert result["inserted"] == 8
        assert result["updated"] == 0
        assert result["skipped"] == 0

    def test_upsert_does_not_duplicate(self, tmp_db):
        ingest_xml(SAMPLE_XML, tmp_db)
        result2 = ingest_xml(SAMPLE_XML, tmp_db)
        assert result2["inserted"] == 0
        assert result2["updated"] == 8

    def test_invalid_status_skipped(self, tmp_path, tmp_db):
        bad_xml = tmp_path / "bad.xml"
        bad_xml.write_text("""<?xml version="1.0"?>
        <photomask_orders>
          <order id="TK-2026-BAD">
            <customer>Test</customer><mask_type>ArF</mask_type><layer>M1</layer>
            <quantity>1</quantity><priority>NORMAL</priority>
            <status>INVALID_STATUS</status>
            <created_at>2026-01-01</created_at><updated_at>2026-01-01</updated_at>
            <engineer>Test</engineer>
          </order>
        </photomask_orders>
        """)
        result = ingest_xml(bad_xml, tmp_db)
        assert result["skipped"] == 1
        assert result["inserted"] == 0

    def test_orders_persisted_in_sql(self, tmp_db):
        ingest_xml(SAMPLE_XML, tmp_db)
        with get_connection(tmp_db) as conn:
            count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        assert count == 8

    def test_status_log_written_on_ingest(self, tmp_db):
        ingest_xml(SAMPLE_XML, tmp_db)
        with get_connection(tmp_db) as conn:
            logs = conn.execute("SELECT COUNT(*) FROM status_log").fetchone()[0]
        assert logs == 8


class TestStateMachine:
    def test_valid_statuses_list(self):
        assert "ORDER_RECEIVED" in VALID_STATUSES
        assert "DELIVERED" in VALID_STATUSES
        assert len(VALID_STATUSES) == 7

    def test_transitions_coverage(self):
        for status in VALID_STATUSES:
            assert status in STATUS_TRANSITIONS

    def test_delivered_is_terminal(self):
        assert STATUS_TRANSITIONS["DELIVERED"] == []
