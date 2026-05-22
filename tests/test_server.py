"""Tests for FastAPI server endpoints."""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from src.server import app
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "kalendbot"

    def test_health_has_waha_status(self, client):
        response = client.get("/health")
        data = response.json()
        assert "waha_session" in data


class TestStatusEndpoint:
    def test_status_returns_pending(self, client):
        response = client.get("/status")
        assert response.status_code == 200
        data = response.json()
        assert "pending_events" in data


class TestWebhookEndpoint:
    def test_webhook_ignores_unknown_event(self, client):
        response = client.post("/webhook/whatsapp", json={"event": "unknown"})
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_webhook_handles_session_status(self, client):
        response = client.post("/webhook/whatsapp", json={
            "event": "session.status",
            "payload": {"status": "CONNECTED"},
        })
        assert response.status_code == 200
        assert response.json()["status"] == "noted"

    def test_correlation_id_in_response(self, client):
        response = client.get("/health")
        assert "x-correlation-id" in response.headers
