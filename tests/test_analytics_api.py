"""
TekTrack — Integration tests for /analytics API endpoints.
"""
import pytest


class TestAnalyticsSummary:
    def test_summary_returns_correct_total(self, client):
        r = client.get("/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_orders"] == 8

    def test_summary_has_all_status_keys(self, client):
        r = client.get("/analytics/summary")
        data = r.json()
        expected_statuses = [
            "ORDER_RECEIVED", "DESIGN_REVIEW", "MASK_WRITING",
            "QUALITY_CHECK", "APPROVED", "SHIPPED", "DELIVERED"
        ]
        for s in expected_statuses:
            assert s in data["by_status"]

    def test_summary_critical_count(self, client):
        r = client.get("/analytics/summary")
        data = r.json()
        assert data["critical_in_progress"] >= 0

    def test_summary_by_customer(self, client):
        r = client.get("/analytics/summary")
        data = r.json()
        assert "Intel Fab Dresden" in data["by_customer"]
        assert data["by_customer"]["Intel Fab Dresden"] == 2

    def test_empty_db_summary(self, empty_client):
        r = empty_client.get("/analytics/summary")
        assert r.status_code == 200
        data = r.json()
        assert data["total_orders"] == 0


class TestPipeline:
    def test_pipeline_has_all_statuses(self, client):
        r = client.get("/analytics/pipeline")
        assert r.status_code == 200
        data = r.json()
        assert "ORDER_RECEIVED" in data
        assert "DELIVERED" in data

    def test_pipeline_orders_in_correct_bucket(self, client):
        r = client.get("/analytics/pipeline")
        data = r.json()
        shipped = data.get("SHIPPED", [])
        assert any(o["id"] == "TK-2026-004" for o in shipped)


class TestThroughput:
    def test_throughput_returns_list(self, client):
        r = client.get("/analytics/throughput")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
