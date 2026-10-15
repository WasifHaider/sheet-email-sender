# Google OAuth Login & Per-User Gmail Sending Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single shared SMTP sender with "Sign in with Google" login, where every user sends through their own Gmail account via the Gmail API, and all data becomes multi-tenant (scoped to the logged-in user).

**Architecture:** FastAPI gains an OAuth2 Authorization Code flow (via `authlib`) that issues our own signed-JWT session cookie. A new `users` table stores each user's Google refresh token. `email_jobs` gains a `user_id` column, and every existing endpoint is scoped to the authenticated user. The mailer swaps `smtplib` for direct Gmail API calls, authenticated per-send with a freshly-minted access token from the job owner's stored refresh token. The frontend gains a login screen and a router guard that redirects unauthenticated visitors there.

**Tech Stack:** `authlib` (OAuth2 client), `PyJWT` (session tokens), `itsdangerous` (required by Starlette's `SessionMiddleware`, which `authlib` uses internally for OAuth state) — all new backend deps. No new frontend deps.

**Spec:** [docs/superpowers/specs/2026-10-15-google-oauth-login-design.md](../specs/2026-10-15-google-oauth-login-design.md)

## Global Constraints

- Google sign-in only — no email/password signup (per spec decision).
- Sheet's required columns become `To, Subject, Email Content` — `From` is no longer read from the sheet.
- Every table/endpoint is scoped to `user_id` — fully multi-tenant.
- Refresh tokens stored as plain DB columns (explicit tradeoff, not encrypted at rest).
- CORS must use an explicit origin list (`FRONTEND_URL` env var), not `"*"`, because cookie-based sessions require `allow_credentials=True`.
- `backend/.env` already has `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SESSION_SECRET` set.

---

## File Structure

```
backend/
├── requirements.txt            # + authlib, pyjwt, itsdangerous
├── db/
│   └── migration_002_users_and_ownership.sql   # new
├── app/
│   ├── auth.py                  # new: session JWT create/decode, get_current_user dependency
│   ├── main.py                  # modified: SessionMiddleware, explicit CORS, register auth router
│   ├── sheet_parser.py          # modified: drop From column requirement
│   ├── mailer.py                # modified: smtplib -> Gmail API (get_access_token, send_via_gmail_api)
│   ├── scheduler.py             # modified: process_job uses per-user Gmail tokens
│   └── routers/
│       ├── auth.py              # new: /auth/google/login, /auth/google/callback, /auth/me, /auth/logout
│       ├── upload.py            # modified: requires auth, sets user_id/from_email
│       ├── batches.py           # modified: requires auth, scoped to user_id
│       └── jobs.py              # modified: requires auth, scoped to user_id
└── tests/
    ├── test_auth.py             # new
    ├── test_sheet_parser.py     # modified (drop From assertions)
    ├── test_upload.py           # modified (auth override, user_id/from_email assertions)
    ├── test_batches.py          # modified (auth override, ownership scoping)
    ├── test_jobs.py             # modified (auth override, ownership scoping)
    ├── test_mailer.py           # modified (Gmail API instead of SMTP)
    └── test_scheduler.py        # modified (per-user token flow)

frontend/
├── src/
│   ├── api/client.js            # modified: withCredentials, API_BASE_URL export
│   ├── composables/
│   │   └── useAuth.js           # new: reactive user state, checkAuth(), logout()
│   ├── router/index.js          # modified: /login route + navigation guard
│   ├── App.vue                  # modified: show user email + logout button
│   └── views/
│       ├── LoginView.vue        # new
│       └── UploadView.vue       # modified: required-columns hint drops "From"
```

Auth concerns are isolated in their own files (`app/auth.py` the dependency, `app/routers/auth.py` the endpoints) so existing routers only gain a `Depends(get_current_user)` line and a `.eq("user_id", ...)` filter — no restructuring of their existing logic.

---

### Task 1: Session JWT helpers

**Files:**
- Modify: `backend/requirements.txt`
- Create: `backend/app/auth.py`
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Produces: `create_session_token(user_id: str, email: str) -> str` and `get_current_user(request: Request) -> dict` (returns `{"id": str, "email": str}`, raises `HTTPException(401)`), used by `routers/auth.py` (Task 3) and every protected router (Task 5).

- [ ] **Step 1: Add new dependencies to `backend/requirements.txt`**

Add these three lines to the existing file:
```
authlib==1.3.2
pyjwt==2.9.0
itsdangerous==2.2.0
```

- [ ] **Step 2: Install the new dependencies**

Run (from `backend/`):
```bash
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

- [ ] **Step 3: Write the failing tests**

Create `backend/tests/test_auth.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they fail**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.auth'`

- [ ] **Step 5: Write the implementation**

Create `backend/app/auth.py`:
```python
import os
import time

import jwt
from fastapi import HTTPException, Request

SESSION_COOKIE_NAME = "session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def create_session_token(user_id: str, email: str) -> str:
    secret = os.environ["SESSION_SECRET"]
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": int(time.time()) + SESSION_MAX_AGE_SECONDS,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_session_token(token: str) -> dict:
    secret = os.environ["SESSION_SECRET"]
    return jwt.decode(token, secret, algorithms=["HS256"])


def get_current_user(request: Request) -> dict:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_session_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    return {"id": payload["user_id"], "email": payload["email"]}
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v`
Expected: PASS (5 passed)

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/app/auth.py backend/tests/test_auth.py
git commit -m "feat: add session JWT helpers and get_current_user dependency"
```

---

### Task 2: Supabase schema migration — users table + email_jobs ownership

**Files:**
- Create: `backend/db/migration_002_users_and_ownership.sql`

**Interfaces:**
- Produces: the `users` table (`id, google_sub, email, name, refresh_token, created_at`) and `email_jobs.user_id` column, used by every later backend task.

- [ ] **Step 1: Create `backend/db/migration_002_users_and_ownership.sql`**

```sql
create table if not exists users (
    id uuid primary key default gen_random_uuid(),
    google_sub text not null unique,
    email text not null,
    name text,
    refresh_token text not null,
    created_at timestamptz not null default now()
);

alter table email_jobs
    add column if not exists user_id uuid references users(id);

create index if not exists idx_email_jobs_user_id on email_jobs (user_id);
```

- [ ] **Step 2: Run this SQL in the Supabase project's SQL editor**

Open the Supabase dashboard → SQL Editor → paste the contents of `backend/db/migration_002_users_and_ownership.sql` → Run. Verify the `users` table appears under Table Editor, and `email_jobs` now has a `user_id` column.

- [ ] **Step 3: Commit**

```bash
git add backend/db/migration_002_users_and_ownership.sql
git commit -m "feat: add users table and email_jobs.user_id migration"
```

---

### Task 3: Google OAuth login + callback endpoints

**Files:**
- Create: `backend/app/routers/auth.py`
- Modify: `backend/app/main.py` (register router, add `SessionMiddleware`, switch CORS to explicit origins)
- Test: `backend/tests/test_auth.py` (append)

**Interfaces:**
- Consumes: `create_session_token` (Task 1), `FakeSupabase`/`fake_db` fixture (existing `conftest.py`).
- Produces: `GET /auth/google/login` (redirects to Google), `GET /auth/google/callback` (sets the `session` cookie, redirects to `{FRONTEND_URL}/upload`). Exposes `oauth` (an `authlib` `OAuth` registry) as `app.routers.auth.oauth` so tests can monkeypatch `oauth.google.authorize_access_token`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_auth.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v -k callback`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.routers.auth'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/routers/auth.py`:
```python
import os

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..auth import SESSION_MAX_AGE_SECONDS, SESSION_COOKIE_NAME, create_session_token
from ..db import get_supabase

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=os.environ.get("GOOGLE_CLIENT_ID"),
    client_secret=os.environ.get("GOOGLE_CLIENT_SECRET"),
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile https://www.googleapis.com/auth/gmail.send",
        "prompt": "consent",
        "access_type": "offline",
    },
)


@router.get("/auth/google/login")
async def google_login(request: Request):
    redirect_uri = os.environ["GOOGLE_REDIRECT_URI"]
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback")
async def google_callback(request: Request, db=Depends(get_supabase)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token["userinfo"]
    sub = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name")
    refresh_token = token.get("refresh_token")

    existing = db.table("users").select("*").eq("google_sub", sub).execute().data
    if existing:
        user_id = existing[0]["id"]
        update_fields = {"email": email, "name": name}
        if refresh_token:
            update_fields["refresh_token"] = refresh_token
        db.table("users").update(update_fields).eq("id", user_id).execute()
    else:
        inserted = db.table("users").insert(
            [{"google_sub": sub, "email": email, "name": name, "refresh_token": refresh_token}]
        ).execute().data
        user_id = inserted[0]["id"]

    session_token = create_session_token(user_id, email)
    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    response = RedirectResponse(url=f"{frontend_url}/upload")
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
    )
    return response
```

- [ ] **Step 4: Wire `SessionMiddleware`, explicit CORS, and the new router into `backend/app/main.py`**

Read the current file first, then apply this replacement:
```python
import asyncio
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .routers import auth, batches, jobs, upload
from .scheduler import scheduler_loop

app = FastAPI(title="Sheet Email Sender")

app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SESSION_SECRET", "dev-secret"))

frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(upload.router)
app.include_router(batches.router)
app.include_router(jobs.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduler_loop())
```

- [ ] **Step 5: Add `FRONTEND_URL` to `backend/.env.example`**

Add this line:
```
FRONTEND_URL=http://localhost:5173
```

- [ ] **Step 6: Run tests to verify they pass**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v`
Expected: PASS (7 passed)

- [ ] **Step 7: Run the full backend test suite to confirm nothing broke**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest -v`
Expected: all tests pass (existing tests are unaffected by this task — they don't exercise auth yet)

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers/auth.py backend/app/main.py backend/.env.example backend/tests/test_auth.py
git commit -m "feat: add Google OAuth login and callback endpoints"
```

---

### Task 4: `/auth/me` and `/auth/logout` endpoints

**Files:**
- Modify: `backend/app/routers/auth.py` (add two routes)
- Test: `backend/tests/test_auth.py` (append)

**Interfaces:**
- Consumes: `get_current_user` (Task 1).
- Produces: `GET /auth/me` returning `{"id": str, "email": str}` or `401`; `POST /auth/logout` clearing the session cookie.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_auth.py`:
```python
from app.auth import SESSION_COOKIE_NAME, create_session_token, get_current_user


def test_me_returns_401_without_cookie():
    client = TestClient(app)
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_user_with_valid_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token("user-1", "a@x.com")
    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, token)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json() == {"id": "user-1", "email": "a@x.com"}


def test_logout_clears_cookie(monkeypatch):
    monkeypatch.setenv("SESSION_SECRET", "test-secret")
    token = create_session_token("user-1", "a@x.com")
    client = TestClient(app)
    client.cookies.set(SESSION_COOKIE_NAME, token)

    response = client.post("/auth/logout")

    assert response.status_code == 200
    set_cookie = response.headers.get("set-cookie", "")
    assert "session=" in set_cookie and ("Max-Age=0" in set_cookie or "expires=" in set_cookie.lower())
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v -k "me_ or logout"`
Expected: FAIL (404, routes don't exist yet)

- [ ] **Step 3: Write the implementation**

Append to `backend/app/routers/auth.py`:
```python
from fastapi.responses import JSONResponse


@router.get("/auth/me")
def me(user: dict = Depends(get_current_user)):
    return user


@router.post("/auth/logout")
def logout():
    response = JSONResponse({"status": "logged_out"})
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
```

Add `get_current_user` to the import from `..auth` at the top of the file (it already imports `SESSION_MAX_AGE_SECONDS, SESSION_COOKIE_NAME, create_session_token` — extend that line to include `get_current_user`).

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_auth.py -v`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/auth.py backend/tests/test_auth.py
git commit -m "feat: add /auth/me and /auth/logout endpoints"
```

---

### Task 5: Scope existing endpoints to the authenticated user, drop sheet's From column

**Files:**
- Modify: `backend/app/sheet_parser.py`
- Modify: `backend/app/routers/upload.py`
- Modify: `backend/app/routers/batches.py`
- Modify: `backend/app/routers/jobs.py`
- Test: `backend/tests/test_sheet_parser.py`, `backend/tests/test_upload.py`, `backend/tests/test_batches.py`, `backend/tests/test_jobs.py` (all modified)

**Interfaces:**
- Consumes: `get_current_user` (Task 1).
- Produces: every protected endpoint now requires `user: dict = Depends(get_current_user)` and scopes its Supabase queries to `user_id`. `parse_sheet` no longer returns a `from_email` key sourced from the sheet (callers set it from the authenticated user instead).

- [ ] **Step 1: Update `backend/tests/test_sheet_parser.py` for the dropped `From` column**

Replace the whole file:
```python
import io
import pytest
from app.sheet_parser import parse_sheet, SheetParseError


def _csv_bytes(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


def test_parse_sheet_happy_path():
    csv_text = (
        "To,Subject,Email Content,CC,Attachment,Date,Time\n"
        "a@x.com,Hello,Hi there,c@x.com,report.pdf,2026-12-01,09:30:00\n"
    )
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    assert rows == [
        {
            "to_email": "a@x.com",
            "subject": "Hello",
            "content": "Hi there",
            "cc": "c@x.com",
            "attachment_filename": "report.pdf",
            "send_date": "2026-12-01",
            "send_time": "09:30:00",
        }
    ]


def test_parse_sheet_blank_optional_columns():
    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    row = rows[0]
    assert row["cc"] is None
    assert row["attachment_filename"] is None
    assert row["send_date"] is None
    assert row["send_time"] is None


def test_parse_sheet_missing_required_column_raises():
    csv_text = "Subject,Email Content\nHello,Hi there\n"
    with pytest.raises(SheetParseError, match="To"):
        parse_sheet(_csv_bytes(csv_text), "sheet.csv")
```

- [ ] **Step 2: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_sheet_parser.py -v`
Expected: FAIL (`test_parse_sheet_happy_path` — actual dict still has `from_email`)

- [ ] **Step 3: Update `backend/app/sheet_parser.py`**

Replace the whole file:
```python
from typing import BinaryIO, Optional
import pandas as pd

REQUIRED_COLUMNS = ["To", "Subject", "Email Content"]


class SheetParseError(Exception):
    pass


def parse_sheet(file_obj: BinaryIO, filename: str) -> list[dict]:
    if filename.lower().endswith(".csv"):
        df = pd.read_csv(file_obj)
    else:
        df = pd.read_excel(file_obj)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SheetParseError(f"Missing required columns: {', '.join(missing)}")

    rows = []
    for _, row in df.iterrows():
        rows.append(
            {
                "to_email": str(row["To"]).strip(),
                "subject": str(row["Subject"]).strip(),
                "content": str(row["Email Content"]),
                "cc": _clean_optional(row.get("CC")),
                "attachment_filename": _clean_optional(row.get("Attachment")),
                "send_date": _parse_date(row.get("Date")),
                "send_time": _parse_time(row.get("Time")),
            }
        )
    return rows


def _clean_optional(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip()
    return text or None


def _parse_date(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    return pd.to_datetime(value).date().isoformat()


def _parse_time(value) -> Optional[str]:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()
    return pd.to_datetime(value).time().isoformat()
```

- [ ] **Step 4: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_sheet_parser.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Update `backend/tests/test_upload.py` for auth + user scoping**

Replace the whole file:
```python
import io
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}


def test_upload_parses_and_stores_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert "batch_id" in body
    assert len(body["rows"]) == 1
    row = body["rows"][0]
    assert row["status"] == "pending_review"
    assert row["to_email"] == "a@x.com"
    assert row["user_id"] == "user-1"
    assert row["from_email"] == "me@x.com"

    app.dependency_overrides.clear()


def test_upload_requires_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_upload_auto_links_single_attachment_to_blank_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = {
        "sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv"),
        "attachments": ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf"),
    }
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert response.json()["rows"][0]["attachment_filename"] == "report.pdf"

    app.dependency_overrides.clear()


def test_upload_does_not_auto_link_when_multiple_attachments(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    csv_text = "To,Subject,Email Content\na@x.com,Hello,Hi there\n"
    files = [
        ("sheet", ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")),
        ("attachments", ("report.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")),
        ("attachments", ("notes.txt", io.BytesIO(b"hi"), "text/plain")),
    ]
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    assert response.json()["rows"][0]["attachment_filename"] is None

    app.dependency_overrides.clear()
```

- [ ] **Step 6: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_upload.py -v`
Expected: FAIL (`401` tests pass trivially since no auth exists yet, but the "requires_authentication" test expects 401 and currently gets 200 — and `user_id`/`from_email` assertions fail with `KeyError`)

- [ ] **Step 7: Update `backend/app/routers/upload.py`**

Replace the whole file:
```python
import pathlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..auth import get_current_user
from ..db import get_supabase
from ..sheet_parser import SheetParseError, parse_sheet

router = APIRouter()
UPLOAD_DIR = pathlib.Path("uploads")


@router.post("/upload")
async def upload_sheet(
    sheet: UploadFile = File(...),
    attachments: list[UploadFile] = File(default=[]),
    db=Depends(get_supabase),
    user: dict = Depends(get_current_user),
):
    try:
        rows = parse_sheet(sheet.file, sheet.filename)
    except SheetParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    batch_id = str(uuid.uuid4())
    batch_dir = UPLOAD_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    attachment_names = []
    for attachment in attachments:
        contents = await attachment.read()
        (batch_dir / attachment.filename).write_bytes(contents)
        attachment_names.append(attachment.filename)

    fallback_attachment = attachment_names[0] if len(attachment_names) == 1 else None
    if fallback_attachment:
        for row in rows:
            if not row.get("attachment_filename"):
                row["attachment_filename"] = fallback_attachment

    records = [
        {
            **row,
            "batch_id": batch_id,
            "status": "pending_review",
            "user_id": user["id"],
            "from_email": user["email"],
        }
        for row in rows
    ]
    result = db.table("email_jobs").insert(records).execute()
    return {"batch_id": batch_id, "rows": result.data}
```

- [ ] **Step 8: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_upload.py -v`
Expected: PASS (4 passed)

- [ ] **Step 9: Update `backend/tests/test_batches.py` for auth + ownership scoping**

Replace the whole file:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}
OTHER_USER = {"id": "user-2", "email": "other@x.com"}


def test_get_batch_returns_only_the_caller_s_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review", "user_id": "user-1"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "z@x.com", "status": "pending_review", "user_id": "user-2"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()


def test_batches_require_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 401

    app.dependency_overrides.clear()


def test_confirm_batch_queues_rows_without_date(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review",
          "send_date": None, "send_time": None, "user_id": "user-1"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.post("/batches/b1/confirm")

    assert response.status_code == 200
    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b1").execute().data
    assert rows[0]["status"] == "queued"

    app.dependency_overrides.clear()


def test_confirm_batch_schedules_future_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b2", "to_email": "a@x.com", "status": "pending_review",
          "send_date": "2099-01-01", "send_time": "09:00:00", "user_id": "user-1"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    client.post("/batches/b2/confirm")

    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b2").execute().data
    assert rows[0]["status"] == "scheduled"

    app.dependency_overrides.clear()


def test_confirm_batch_does_not_touch_another_user_s_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b3", "to_email": "z@x.com", "status": "pending_review",
          "send_date": None, "send_time": None, "user_id": "user-2"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    client.post("/batches/b3/confirm")

    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b3").execute().data
    assert rows[0]["status"] == "pending_review"

    app.dependency_overrides.clear()
```

- [ ] **Step 10: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_batches.py -v`
Expected: FAIL (no ownership filtering yet — cross-user rows leak, 401 test fails)

- [ ] **Step 11: Update `backend/app/routers/batches.py`**

Replace the whole file:
```python
from datetime import datetime

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..db import get_supabase

router = APIRouter()


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db=Depends(get_supabase), user: dict = Depends(get_current_user)):
    result = (
        db.table("email_jobs")
        .select("*")
        .eq("batch_id", batch_id)
        .eq("user_id", user["id"])
        .execute()
    )
    return {"rows": result.data}


@router.post("/batches/{batch_id}/confirm")
def confirm_batch(batch_id: str, db=Depends(get_supabase), user: dict = Depends(get_current_user)):
    rows = (
        db.table("email_jobs")
        .select("*")
        .eq("batch_id", batch_id)
        .eq("user_id", user["id"])
        .execute()
        .data
    )
    now = datetime.now()

    for row in rows:
        send_date = row.get("send_date")
        if not send_date:
            new_status = "queued"
        else:
            send_time = row.get("send_time") or "00:00:00"
            scheduled_at = datetime.fromisoformat(f"{send_date}T{send_time}")
            new_status = "queued" if scheduled_at <= now else "scheduled"
        db.table("email_jobs").update({"status": new_status}).eq("id", row["id"]).execute()

    return {"batch_id": batch_id, "status": "confirmed"}
```

- [ ] **Step 12: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_batches.py -v`
Expected: PASS (5 passed)

- [ ] **Step 13: Update `backend/tests/test_jobs.py` for auth + ownership scoping**

Replace the whole file:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase
from app.auth import get_current_user

FAKE_USER = {"id": "user-1", "email": "me@x.com"}


def test_list_jobs_filters_by_status_and_owner(fake_db):
    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "to_email": "a@x.com", "status": "sent", "user_id": "user-1"},
            {"batch_id": "b1", "to_email": "b@x.com", "status": "failed", "user_id": "user-1"},
            {"batch_id": "b1", "to_email": "z@x.com", "status": "failed", "user_id": "user-2"},
        ]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    client = TestClient(app)

    response = client.get("/jobs", params={"status": "failed"})

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["to_email"] == "b@x.com"

    app.dependency_overrides.clear()


def test_jobs_require_authentication(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/jobs")

    assert response.status_code == 401

    app.dependency_overrides.clear()
```

- [ ] **Step 14: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_jobs.py -v`
Expected: FAIL (no ownership filtering yet)

- [ ] **Step 15: Update `backend/app/routers/jobs.py`**

Replace the whole file:
```python
from typing import Optional

from fastapi import APIRouter, Depends

from ..auth import get_current_user
from ..db import get_supabase

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db=Depends(get_supabase),
    user: dict = Depends(get_current_user),
):
    query = db.table("email_jobs").select("*").eq("user_id", user["id"])
    if status:
        query = query.eq("status", status)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    result = query.order("created_at", desc=True).execute()
    return {"jobs": result.data}
```

- [ ] **Step 16: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_jobs.py -v`
Expected: PASS (2 passed)

- [ ] **Step 17: Run the full backend test suite**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest -v`
Expected: all tests pass

- [ ] **Step 18: Commit**

```bash
git add backend/app/sheet_parser.py backend/app/routers/upload.py backend/app/routers/batches.py backend/app/routers/jobs.py backend/tests/test_sheet_parser.py backend/tests/test_upload.py backend/tests/test_batches.py backend/tests/test_jobs.py
git commit -m "feat: scope all endpoints to the authenticated user, drop sheet's From column"
```

---

### Task 6: Mailer rewrite — Gmail API instead of SMTP

**Files:**
- Modify: `backend/app/mailer.py`
- Test: `backend/tests/test_mailer.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `build_message(job, attachment_path)` (unchanged signature/behavior), `get_access_token(refresh_token: str) -> str`, `send_via_gmail_api(access_token: str, msg: EmailMessage) -> None` — both used by `scheduler.py` (Task 7), replacing the old `send_message`.

- [ ] **Step 1: Write the failing tests**

Replace `backend/tests/test_mailer.py`:
```python
import pathlib
from email.message import EmailMessage

from app.mailer import build_message, get_access_token, send_via_gmail_api


def test_build_message_sets_headers_and_body():
    job = {
        "to_email": "a@x.com",
        "from_email": "b@x.com",
        "cc": "c@x.com",
        "subject": "Hello",
        "content": "Hi there",
    }
    msg = build_message(job, attachment_path=None)

    assert msg["To"] == "a@x.com"
    assert msg["From"] == "b@x.com"
    assert msg["Cc"] == "c@x.com"
    assert msg["Subject"] == "Hello"
    assert msg.get_content().strip() == "Hi there"


def test_build_message_attaches_file(tmp_path):
    attachment = tmp_path / "report.txt"
    attachment.write_text("data")
    job = {"to_email": "a@x.com", "from_email": "b@x.com", "cc": None,
           "subject": "Hello", "content": "Hi there"}

    msg = build_message(job, attachment_path=attachment)

    attachments = list(msg.iter_attachments())
    assert len(attachments) == 1
    assert attachments[0].get_filename() == "report.txt"


class _FakeResponse:
    def __init__(self, json_data):
        self._json_data = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


def test_get_access_token_calls_google_token_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse({"access_token": "new-access-token"})

    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr("app.mailer.httpx.post", fake_post)

    token = get_access_token("refresh-abc")

    assert token == "new-access-token"
    assert captured["url"] == "https://oauth2.googleapis.com/token"
    assert captured["data"]["refresh_token"] == "refresh-abc"
    assert captured["data"]["grant_type"] == "refresh_token"


def test_send_via_gmail_api_posts_base64_message(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None, **kwargs):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"id": "msg-1"})

    monkeypatch.setattr("app.mailer.httpx.post", fake_post)

    msg = EmailMessage()
    msg["To"] = "a@x.com"
    msg["From"] = "b@x.com"
    msg["Subject"] = "Hi"
    msg.set_content("Body")

    send_via_gmail_api("access-token-123", msg)

    assert captured["url"] == "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
    assert captured["headers"]["Authorization"] == "Bearer access-token-123"
    assert "raw" in captured["json"]
```

- [ ] **Step 2: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_mailer.py -v`
Expected: FAIL (`ImportError: cannot import name 'get_access_token'`)

- [ ] **Step 3: Write the implementation**

Replace `backend/app/mailer.py`:
```python
import base64
import os
import pathlib
from email.message import EmailMessage
from typing import Optional

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def build_message(job: dict, attachment_path: Optional[pathlib.Path]) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = job["subject"]
    msg["From"] = job["from_email"]
    msg["To"] = job["to_email"]
    if job.get("cc"):
        msg["Cc"] = job["cc"]
    msg.set_content(job["content"])

    if attachment_path and attachment_path.exists():
        data = attachment_path.read_bytes()
        msg.add_attachment(
            data,
            maintype="application",
            subtype="octet-stream",
            filename=attachment_path.name,
        )
    return msg


def get_access_token(refresh_token: str) -> str:
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"],
            "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def send_via_gmail_api(access_token: str, msg: EmailMessage) -> None:
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("ascii")
    response = httpx.post(
        SEND_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        json={"raw": raw},
        timeout=15,
    )
    response.raise_for_status()
```

- [ ] **Step 4: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_mailer.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Remove unused SMTP env vars from `backend/.env.example`**

Remove the four lines `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD` — they're no longer read by any code after this task.

- [ ] **Step 6: Commit**

```bash
git add backend/app/mailer.py backend/tests/test_mailer.py backend/.env.example
git commit -m "feat: replace SMTP mailer with Gmail API sending"
```

---

### Task 7: Scheduler — per-user Gmail tokens

**Files:**
- Modify: `backend/app/scheduler.py`
- Test: `backend/tests/test_scheduler.py`

**Interfaces:**
- Consumes: `get_access_token`, `send_via_gmail_api` (Task 6), `build_message` (unchanged).
- Produces: `process_job(db, job)` now looks up the job's owning user and sends via Gmail API instead of SMTP. `due_jobs(db)` is unchanged.

- [ ] **Step 1: Write the failing tests**

Replace `backend/tests/test_scheduler.py`:
```python
from datetime import datetime, timedelta

from app.scheduler import due_jobs, process_job


def test_due_jobs_includes_queued_and_past_scheduled(fake_db):
    past_date = (datetime.now() - timedelta(days=1)).date().isoformat()
    future_date = (datetime.now() + timedelta(days=1)).date().isoformat()

    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "status": "queued"},
            {"batch_id": "b1", "status": "scheduled", "send_date": past_date, "send_time": "00:00:00"},
            {"batch_id": "b1", "status": "scheduled", "send_date": future_date, "send_time": "00:00:00"},
            {"batch_id": "b1", "status": "sent"},
        ]
    ).execute()

    due = due_jobs(fake_db)

    assert len(due) == 2
    assert all(job["status"] in ("queued", "scheduled") for job in due)


def test_process_job_marks_sent_on_success(fake_db, monkeypatch):
    fake_db.table("users").insert(
        [{"id": "user-1", "google_sub": "g1", "email": "a@x.com", "refresh_token": "refresh-abc"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"id": "job-1", "batch_id": "b1", "to_email": "a@x.com", "from_email": "a@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued", "user_id": "user-1"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]

    monkeypatch.setattr("app.scheduler.get_access_token", lambda refresh_token: "access-token")
    monkeypatch.setattr("app.scheduler.send_via_gmail_api", lambda access_token, msg: None)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]
    assert updated["status"] == "sent"
    assert updated["sent_at"] is not None


def test_process_job_marks_failed_on_exception(fake_db, monkeypatch):
    fake_db.table("users").insert(
        [{"id": "user-2", "google_sub": "g2", "email": "b@x.com", "refresh_token": "refresh-xyz"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"id": "job-2", "batch_id": "b1", "to_email": "a@x.com", "from_email": "b@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued", "user_id": "user-2"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]

    def _raise(access_token, msg):
        raise RuntimeError("gmail api down")

    monkeypatch.setattr("app.scheduler.get_access_token", lambda refresh_token: "access-token")
    monkeypatch.setattr("app.scheduler.send_via_gmail_api", _raise)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]
    assert updated["status"] == "failed"
    assert "gmail api down" in updated["error_message"]
```

- [ ] **Step 2: Run to verify it fails**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v`
Expected: FAIL (`process_job` still imports/calls the removed `send_message`)

- [ ] **Step 3: Update `backend/app/scheduler.py`**

Replace the whole file:
```python
import asyncio
import pathlib
from datetime import datetime

from .db import get_supabase
from .mailer import build_message, get_access_token, send_via_gmail_api

UPLOAD_DIR = pathlib.Path("uploads")
POLL_SECONDS = 60


def due_jobs(db) -> list[dict]:
    result = db.table("email_jobs").select("*").in_("status", ["queued", "scheduled"]).execute()
    now = datetime.now()
    due = []
    for job in result.data:
        if job["status"] == "queued":
            due.append(job)
            continue
        send_date = job.get("send_date")
        send_time = job.get("send_time") or "00:00:00"
        scheduled_at = datetime.fromisoformat(f"{send_date}T{send_time}")
        if scheduled_at <= now:
            due.append(job)
    return due


def process_job(db, job: dict) -> None:
    attachment_path = None
    if job.get("attachment_filename"):
        attachment_path = UPLOAD_DIR / job["batch_id"] / job["attachment_filename"]

    msg = build_message(job, attachment_path)
    try:
        owner = db.table("users").select("*").eq("id", job["user_id"]).execute().data[0]
        access_token = get_access_token(owner["refresh_token"])
        send_via_gmail_api(access_token, msg)
        update = {"status": "sent", "sent_at": datetime.now().isoformat()}
        if job.get("attachment_filename") and not (attachment_path and attachment_path.exists()):
            update["error_message"] = "Attachment file missing; sent without it"
        db.table("email_jobs").update(update).eq("id", job["id"]).execute()
    except Exception as exc:
        db.table("email_jobs").update(
            {"status": "failed", "error_message": str(exc)}
        ).eq("id", job["id"]).execute()


async def scheduler_loop(db_factory=get_supabase) -> None:
    while True:
        db = db_factory()
        for job in due_jobs(db):
            process_job(db, job)
        await asyncio.sleep(POLL_SECONDS)
```

- [ ] **Step 4: Run to verify it passes**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest tests/test_scheduler.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the full backend test suite**

Run (from `backend/`): `.venv\Scripts\python.exe -m pytest -v`
Expected: all tests pass

- [ ] **Step 6: Commit**

```bash
git add backend/app/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: scheduler sends via the job owner's Gmail API token"
```

---

### Task 8: Frontend — auth state, axios credentials, router guard

**Files:**
- Modify: `frontend/src/api/client.js`
- Create: `frontend/src/composables/useAuth.js`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/.env.example` (add note, no new var needed — `VITE_API_BASE_URL` already exists)

**Interfaces:**
- Produces: `useAuth()` returning `{ user, checked, checkAuth, logout }` (reactive `user` is `null` or `{id, email}`), used by `App.vue` (Task 10) and `LoginView.vue` (Task 9). `API_BASE_URL` exported from `client.js`, used by `LoginView.vue` for the login redirect.

- [ ] **Step 1: Update `frontend/src/api/client.js`**

```javascript
import axios from 'axios'

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true
})

export function uploadSheet(sheetFile, attachmentFiles) {
  const form = new FormData()
  form.append('sheet', sheetFile)
  for (const file of attachmentFiles) {
    form.append('attachments', file)
  }
  return client.post('/upload', form).then((res) => res.data)
}

export function getBatch(batchId) {
  return client.get(`/batches/${batchId}`).then((res) => res.data)
}

export function confirmBatch(batchId) {
  return client.post(`/batches/${batchId}/confirm`).then((res) => res.data)
}

export function listJobs(params = {}) {
  return client.get('/jobs', { params }).then((res) => res.data)
}

export default client
```

- [ ] **Step 2: Create `frontend/src/composables/useAuth.js`**

```javascript
import { ref } from 'vue'
import client from '../api/client'

const user = ref(null)
const checked = ref(false)

async function checkAuth() {
  try {
    const response = await client.get('/auth/me')
    user.value = response.data
  } catch {
    user.value = null
  } finally {
    checked.value = true
  }
}

async function logout() {
  await client.post('/auth/logout')
  user.value = null
}

export function useAuth() {
  return { user, checked, checkAuth, logout }
}
```

- [ ] **Step 3: Add the login route and navigation guard to `frontend/src/router/index.js`**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'
import PreviewView from '../views/PreviewView.vue'
import StatusView from '../views/StatusView.vue'
import LoginView from '../views/LoginView.vue'
import { useAuth } from '../composables/useAuth'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/login', name: 'login', component: LoginView },
  { path: '/upload', name: 'upload', component: UploadView },
  { path: '/preview/:batchId', name: 'preview', component: PreviewView, props: true },
  { path: '/status', name: 'status', component: StatusView }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const { user, checked, checkAuth } = useAuth()
  if (!checked.value) {
    await checkAuth()
  }
  if (to.name !== 'login' && !user.value) {
    return { name: 'login' }
  }
  if (to.name === 'login' && user.value) {
    return { name: 'upload' }
  }
  return true
})

export default router
```

Note: `LoginView.vue` is imported here but created in Task 9 — this task's own verification step (Step 4 below) only checks the file compiles once Task 9 adds the missing file; until then, proceed to Task 9 immediately rather than trying to verify this task in isolation (the two are tightly coupled by this import).

- [ ] **Step 4: Commit (bundled with Task 9, see that task's commit step)**

This task has no standalone commit — continue directly to Task 9, then commit both together.

---

### Task 9: LoginView and App.vue nav updates

**Files:**
- Create: `frontend/src/views/LoginView.vue`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes: `useAuth()` (Task 8), `API_BASE_URL` (Task 8).

- [ ] **Step 1: Create `frontend/src/views/LoginView.vue`**

```vue
<template>
  <div style="min-height: 100vh; display: flex; align-items: center; justify-content: center">
    <div :style="cardStyle">
      <h1 style="font-size: 1.5rem; font-weight: 700; margin: 0 0 8px; text-align: center">
        Sheet Email Sender
      </h1>
      <p style="font-size: 14px; text-align: center; margin: 0 0 24px" :style="{ color: t.muted }">
        Sign in to upload sheets and send email from your own Gmail.
      </p>
      <button :style="buttonStyle" @click="signIn">
        <svg width="18" height="18" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M23.52 12.27c0-.85-.07-1.66-.21-2.45H12v4.64h6.47a5.53 5.53 0 0 1-2.4 3.63v3h3.87c2.27-2.09 3.58-5.17 3.58-8.82z" />
          <path fill="#34A853" d="M12 24c3.24 0 5.96-1.07 7.94-2.91l-3.87-3c-1.08.72-2.45 1.15-4.07 1.15-3.13 0-5.78-2.11-6.73-4.96H1.27v3.11A12 12 0 0 0 12 24z" />
          <path fill="#FBBC05" d="M5.27 14.28A7.2 7.2 0 0 1 4.89 12c0-.79.14-1.56.38-2.28V6.61H1.27A12 12 0 0 0 0 12c0 1.94.46 3.77 1.27 5.39l4-3.11z" />
          <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0A12 12 0 0 0 1.27 6.61l4 3.11C6.22 6.86 8.87 4.75 12 4.75z" />
        </svg>
        Sign in with Google
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from '../composables/useTheme'
import { API_BASE_URL } from '../api/client'

const { t } = useTheme()

const cardStyle = computed(
  () =>
    `background:${t.value.card};border:1px solid ${t.value.line};border-radius:${t.value.r};padding:32px;box-shadow:${t.value.shadow};width:320px`
)

const buttonStyle = computed(
  () =>
    `display:flex;align-items:center;justify-content:center;gap:10px;width:100%;height:44px;border-radius:${t.value.br};border:1px solid ${t.value.line};background:${t.value.card};color:${t.value.ink};font:600 14px 'Geist',sans-serif;cursor:pointer`
)

function signIn() {
  window.location.href = `${API_BASE_URL}/auth/google/login`
}
</script>
```

- [ ] **Step 2: Update `frontend/src/App.vue` to show the user and a logout button**

Read the current file first. In the `<script setup>` block, add:
```javascript
import { onMounted } from 'vue'
import { useAuth } from './composables/useAuth'

const { user, logout } = useAuth()

async function handleLogout() {
  await logout()
  router.push({ name: 'login' })
}
```

(The `route`, `mode`, `toggle`, `t` imports/usages already in the file stay as-is — this only adds to the existing `<script setup>` block, it doesn't replace it.)

In the `<template>`, inside the `<nav>` element, after the theme-toggle `<button>` and before the Upload/Status `<router-link>`s, add:
```vue
<span v-if="user" style="font-size: 13px" :style="{ color: t.muted }">{{ user.email }}</span>
<button v-if="user" :style="toggleStyle" @click="handleLogout" aria-label="Log out">
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"></path>
  </svg>
</button>
```

Also hide the Upload/Status nav links when logged out (wrap the existing `<div style="display: flex; gap: 4px">...Upload/Status router-links...</div>` with `v-if="user"`).

- [ ] **Step 3: Start both dev servers and verify the login flow manually**

Run backend (from `backend/`): `.venv\Scripts\python.exe -m uvicorn app.main:app --reload`
Run frontend (from `frontend/`): `npm run dev`

In the browser:
1. Visit `http://localhost:5173/upload` — expect an immediate redirect to `/login` (no session cookie yet).
2. Click "Sign in with Google" — expect a redirect to Google's real consent screen.
3. Approve with a test-user Google account — expect a redirect back through `/auth/google/callback` to `/upload`, now showing the app with your email in the nav bar.
4. Click the logout icon — expect a redirect to `/login`, and revisiting `/upload` redirects to `/login` again (session cleared).

- [ ] **Step 4: Update `frontend/src/views/UploadView.vue`'s required-columns hint**

Find this line (the subtext under the page heading):
```vue
<p style="margin: 0 0 28px; text-align: center; font-size: 15px" :style="{ color: t.muted }">
  Upload your sheet, review the rows, then send or schedule.
</p>
```
No change needed to that line itself — update the `reqCols` constant further down in the same file:
```javascript
const reqCols = ['To', 'Subject', 'Email Content']
```
(Remove `'From'` from the array — it was `['To', 'From', 'Subject', 'Email Content']` before.)

- [ ] **Step 5: Commit (Tasks 8 and 9 together)**

```bash
git add frontend/src/api/client.js frontend/src/composables/useAuth.js frontend/src/router/index.js frontend/src/views/LoginView.vue frontend/src/App.vue frontend/src/views/UploadView.vue
git commit -m "feat: add Google sign-in flow, router guard, and user nav display"
```

---

## Self-Review Notes

- **Spec coverage:** Google-only auth (Tasks 3-4, 9), custom OAuth via authlib (Task 3), From column dropped (Task 5), fully multi-tenant (Task 5 — every endpoint scoped by `user_id`), refresh tokens as plain columns (Task 2, no encryption added — matches spec's explicit tradeoff), CORS explicit origins (Task 3), Gmail API sending (Tasks 6-7), frontend login/guard (Tasks 8-9) — every spec section has a task.
- **Placeholder scan:** no TBD/TODO; all steps contain full code or exact manual verification steps.
- **Type consistency:** `user` dict shape `{"id": str, "email": str}` is consistent from `get_current_user` (Task 1) through every router (Task 5) and the frontend's `useAuth` (Task 8, matching the JSON shape `/auth/me` returns). `job["user_id"]` / `users.id` foreign key naming consistent between Task 2's schema, Task 5's upload, and Task 7's scheduler lookup. `get_access_token(refresh_token: str) -> str` and `send_via_gmail_api(access_token: str, msg: EmailMessage) -> None` signatures match between Task 6's definition and Task 7's usage/mocking.
