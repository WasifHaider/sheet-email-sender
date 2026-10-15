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
