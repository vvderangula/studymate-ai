"""Tests for authentication endpoints and JWT validation."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unique_email() -> str:
    return f"auth_{uuid.uuid4().hex[:8]}@example.com"


def _register(
    full_name: str = "Test User",
    email: str | None = None,
    password: str = "password123",
):
    return client.post(
        "/auth/register",
        json={"full_name": full_name, "email": email or _unique_email(), "password": password},
    )


def _login(email: str, password: str = "password123"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


# ---------------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------------

def test_register_success():
    response = _register()
    assert response.status_code == 201
    body = response.json()
    assert "@" in body["email"]
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["full_name"] == "Test User"


def test_register_duplicate_email():
    email = _unique_email()
    _register(email=email)
    response = _register(email=email)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_register_invalid_email():
    response = _register(email="not-an-email")
    assert response.status_code == 422


def test_register_short_password():
    response = _register(password="short")
    assert response.status_code == 422
    assert "8" in response.json()["detail"][0]["msg"]


def test_register_empty_name():
    response = _register(full_name="   ")
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

def test_login_success():
    email = _unique_email()
    _register(email=email)
    response = _login(email=email)
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["email"] == email


def test_login_wrong_password():
    email = _unique_email()
    _register(email=email)
    response = _login(email=email, password="wrongpassword")
    assert response.status_code == 401


def test_login_unknown_email():
    response = _login(email=f"nobody_{uuid.uuid4().hex[:6]}@example.com")
    assert response.status_code == 401


def test_login_email_case_insensitive():
    email = _unique_email()
    _register(email=email)
    response = _login(email=email.upper())
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Protected routes
# ---------------------------------------------------------------------------

def test_protected_route_without_token():
    """Accessing a protected endpoint without a token should return 403."""
    response = client.get("/dashboard")
    assert response.status_code in (401, 403)


def test_protected_route_with_invalid_token():
    response = client.get(
        "/dashboard",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert response.status_code == 401


def test_protected_route_with_valid_token():
    res = _register()
    token = res.json()["access_token"]
    response = client.get("/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


def test_get_me_returns_user():
    email = _unique_email()
    res = _register(full_name="Me User", email=email)
    token = res.json()["access_token"]
    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == email
    assert body["full_name"] == "Me User"


def test_pdf_upload_requires_auth():
    """PDF upload must reject requests without a token."""
    import io
    fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
    fake_pdf.name = "test.pdf"
    response = client.post("/pdf/upload", files={"file": ("test.pdf", fake_pdf, "application/pdf")})
    assert response.status_code in (401, 403)
