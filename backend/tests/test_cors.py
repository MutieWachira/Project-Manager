"""Tests for browser cross-origin request security."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_cors_allows_configured_frontend_origin():
    """Allow credentialed preflight requests from the frontend."""

    origin = settings.FRONTEND_URL.rstrip("/")

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/refresh",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": ("content-type,x-csrf-token"),
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"

    allowed_methods = response.headers["access-control-allow-methods"]

    assert "POST" in allowed_methods

    allowed_headers = response.headers["access-control-allow-headers"].lower()

    assert "content-type" in allowed_headers
    assert "x-csrf-token" in allowed_headers


def test_cors_rejects_unapproved_frontend_origin():
    """Do not grant browser access to an unapproved origin."""

    with TestClient(app) as client:
        response = client.options(
            "/api/v1/auth/refresh",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
