from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["application"] == "SherlskyyCommand"
    assert data["version"] == "0.1.0"
    # assert data["message"] == "Homepage running well."

def test_health_endpoint():
    response = client.get("api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["application"] == "SherlskyyCommand"
