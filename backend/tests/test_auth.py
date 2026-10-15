import time

import jwt
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.auth import create_session_token, decode_session_token, get_current_user


def _request_with_cookie(token: str | None) -> Request:
    cookie_header = f"session={token}".encode() if token else b""
    headers = [(b"cookie", cookie_header)] if token else []
    scope = {"type": "http", "headers": headers}
    return Request(scope)


def test_create_and_decode_session_token_roundtrip(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token("user-1", "a@x.com")
    payload = decode_session_token(token)
    assert payload["user_id"] == "user-1"
    assert payload["email"] == "a@x.com"


def test_get_current_user_missing_cookie_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request_with_cookie(None))
    assert exc_info.value.status_code == 401


def test_get_current_user_invalid_token_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request_with_cookie("not-a-real-token"))
    assert exc_info.value.status_code == 401


def test_get_current_user_expired_token_raises_401(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    expired = jwt.encode(
        {"user_id": "user-1", "email": "a@x.com", "exp": int(time.time()) - 10},
        "test-secret",
        algorithm="HS256",
    )
    with pytest.raises(HTTPException) as exc_info:
        get_current_user(_request_with_cookie(expired))
    assert exc_info.value.status_code == 401


def test_get_current_user_valid_cookie_returns_user(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token("user-1", "a@x.com")
    user = get_current_user(_request_with_cookie(token))
    assert user == {"id": "user-1", "email": "a@x.com"}


from fastapi.testclient import TestClient

from app.main import app
from app.db import get_supabase
from app.routers import auth as auth_router


def test_google_callback_creates_new_user_and_sets_cookie(fake_db, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")

    async def fake_authorize_access_token(request):
        return {
            "refresh_token": "refresh-abc",
            "userinfo": {"sub": "google-123", "email": "a@x.com", "name": "A"},
        }

    monkeypatch.setattr(auth_router.oauth.google, "authorize_access_token", fake_authorize_access_token)
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app, follow_redirects=False)

    response = client.get("/auth/google/callback")

    assert response.status_code in (302, 307)
    assert "session" in response.cookies

    users = fake_db.table("users").select("*").eq("google_sub", "google-123").execute().data
    assert len(users) == 1
    assert users[0]["refresh_token"] == "refresh-abc"

    app.dependency_overrides.clear()


def test_google_callback_updates_existing_user_without_losing_refresh_token(fake_db, monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    fake_db.table("users").insert(
        [{"google_sub": "google-123", "email": "old@x.com", "name": "Old", "refresh_token": "original-refresh"}]
    ).execute()

    async def fake_authorize_access_token(request):
        return {
            "refresh_token": None,
            "userinfo": {"sub": "google-123", "email": "new@x.com", "name": "New"},
        }

    monkeypatch.setattr(auth_router.oauth.google, "authorize_access_token", fake_authorize_access_token)
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app, follow_redirects=False)

    client.get("/auth/google/callback")

    users = fake_db.table("users").select("*").eq("google_sub", "google-123").execute().data
    assert len(users) == 1
    assert users[0]["email"] == "new@x.com"
    assert users[0]["refresh_token"] == "original-refresh"

    app.dependency_overrides.clear()
