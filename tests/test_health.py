# Health endpoint tests
# Uses FastAPI's TestClient (backed by httpx) to test the /health route
# without spinning up a real server.

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_200():
    response = client.get("/api/v1/health")
    assert response.status_code == 200


def test_health_response_shape():
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "app_name" in data
