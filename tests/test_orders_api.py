"""
TekTrack — Integration tests for /orders API endpoints.
"""
import pytest


class TestHealthEndpoints:
    def test_root(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["service"] == "TekTrack API"

    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"


class TestListOrders:
    def test_returns_all_orders(self, client):
        r = client.get("/orders/")
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 8

    def test_filter_by_status(self, client):
        r = client.get("/orders/", params={"status": "QUALITY_CHECK"})
        assert r.status_code == 200
        orders = r.json()
        assert all(o["status"] == "QUALITY_CHECK" for o in orders)

    def test_filter_by_priority(self, client):
        r = client.get("/orders/", params={"priority": "CRITICAL"})
        assert r.status_code == 200
        orders = r.json()
        assert all(o["priority"] == "CRITICAL" for o in orders)

    def test_filter_by_customer(self, client):
        r = client.get("/orders/", params={"customer": "Bosch"})
        assert r.status_code == 200
        orders = r.json()
        assert all("Bosch" in o["customer"] for o in orders)

    def test_invalid_status_filter_returns_400(self, client):
        r = client.get("/orders/", params={"status": "NONEXISTENT"})
        assert r.status_code == 400


class TestGetOrder:
    def test_get_existing_order(self, client):
        r = client.get("/orders/TK-2026-001")
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "TK-2026-001"
        assert data["customer"] == "Intel Fab Dresden"

    def test_get_nonexistent_order_returns_404(self, client):
        r = client.get("/orders/TK-9999-999")
        assert r.status_code == 404


class TestCreateOrder:
    def test_create_valid_order(self, client):
        payload = {
            "id": "TK-2026-099",
            "customer": "Test Semiconductor",
            "mask_type": "ArF 193nm",
            "layer": "Metal3",
            "quantity": 2,
            "priority": "NORMAL",
            "engineer": "J. Shah",
            "notes": "Test order",
        }
        r = client.post("/orders/", json=payload)
        assert r.status_code == 201
        data = r.json()
        assert data["id"] == "TK-2026-099"
        assert data["status"] == "ORDER_RECEIVED"

    def test_duplicate_order_returns_409(self, client):
        payload = {
            "id": "TK-2026-001",
            "customer": "Dup", "mask_type": "ArF 193nm",
            "layer": "M1", "quantity": 1,
            "priority": "NORMAL", "engineer": "Test",
        }
        r = client.post("/orders/", json=payload)
        assert r.status_code == 409

    def test_invalid_id_format_returns_422(self, client):
        payload = {
            "id": "BADID",
            "customer": "X", "mask_type": "ArF",
            "layer": "M1", "quantity": 1,
            "priority": "NORMAL", "engineer": "Test",
        }
        r = client.post("/orders/", json=payload)
        assert r.status_code == 422

    def test_invalid_priority_returns_422(self, client):
        payload = {
            "id": "TK-2026-098",
            "customer": "X", "mask_type": "ArF",
            "layer": "M1", "quantity": 1,
            "priority": "ULTRA", "engineer": "Test",
        }
        r = client.post("/orders/", json=payload)
        assert r.status_code == 422


class TestStatusUpdate:
    def test_valid_transition(self, client):
        # TK-2026-005 is ORDER_RECEIVED → DESIGN_REVIEW
        r = client.patch("/orders/TK-2026-005/status", json={"new_status": "DESIGN_REVIEW"})
        assert r.status_code == 200
        assert r.json()["status"] == "DESIGN_REVIEW"

    def test_invalid_transition_returns_400(self, client):
        # TK-2026-001 is QUALITY_CHECK → cannot jump to SHIPPED
        r = client.patch("/orders/TK-2026-001/status", json={"new_status": "SHIPPED"})
        assert r.status_code == 400

    def test_update_nonexistent_order_returns_404(self, client):
        r = client.patch("/orders/TK-9999-999/status", json={"new_status": "DESIGN_REVIEW"})
        assert r.status_code == 404

    def test_status_log_updated_after_transition(self, client):
        client.patch("/orders/TK-2026-005/status", json={"new_status": "DESIGN_REVIEW", "changed_by": "test"})
        r = client.get("/orders/TK-2026-005/log")
        assert r.status_code == 200
        logs = r.json()
        last_log = logs[-1]
        assert last_log["new_status"] == "DESIGN_REVIEW"
        assert last_log["changed_by"] == "test"


class TestDeleteOrder:
    def test_delete_order_received(self, client):
        # Create then delete
        client.post("/orders/", json={
            "id": "TK-2026-099", "customer": "Del Test",
            "mask_type": "ArF", "layer": "M1", "quantity": 1,
            "priority": "NORMAL", "engineer": "Test"
        })
        r = client.delete("/orders/TK-2026-099")
        assert r.status_code == 204

    def test_cannot_delete_in_progress_order(self, client):
        # TK-2026-002 is MASK_WRITING — not ORDER_RECEIVED
        r = client.delete("/orders/TK-2026-002")
        assert r.status_code == 400
