from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "SherlskyyCommand"
    assert data["version"] == settings.APP_VERSION
    # assert data["message"] == "Homepage running well."


def test_health_endpoint(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        lambda: True,
    )

    response = client.get("api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "online"
    assert data["application"] == "SherlskyyCommand"


def test_health_endpoint_reports_database_offline(monkeypatch):
    monkeypatch.setattr(
        "app.api.routes.health.check_database_connection",
        lambda: False,
    )

    response = client.get("api/v1/health")

    assert response.status_code == 503
    assert response.json()["detail"]["database"] == "offline"
