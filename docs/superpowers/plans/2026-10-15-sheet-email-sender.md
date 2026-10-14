# Sheet-Based Email Sender Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a small web app that lets a user upload an Excel/CSV sheet of emails, preview the parsed rows, confirm, then send/schedule them via SMTP, with a status view to track sent/failed/pending jobs.

**Architecture:** FastAPI backend (REST API, Supabase/Postgres for storage, `asyncio` background task polling every 60s for due emails, `smtplib` for sending) + a separate Vue 3 + Vuetify SPA frontend calling the backend over JSON. No auth, single SMTP sender account, local-only for now (deploy later).

**Tech Stack:** Python 3.11+, FastAPI, Supabase (`supabase-py`), pandas + openpyxl, smtplib, pytest; Node 18+, Vue 3, Vuetify 3, Vite, axios, vue-router.

**Spec:** [docs/superpowers/specs/2026-10-15-sheet-email-sender-design.md](../specs/2026-10-15-sheet-email-sender-design.md)

## Global Constraints

- No authentication / multi-tenant isolation in v1 (per spec "Explicitly out of scope").
- No editing of parsed rows before send — bad rows are fixed by re-uploading the sheet.
- No automatic retries on failed sends.
- SMTP credentials and Supabase credentials come from environment variables only, never hardcoded.
- Frontend UI must stay simple, sleek, minimal — plain cards, generous whitespace, one accent color, no decorative clutter (user's explicit styling request).
- Scheduler polls every 60 seconds (per spec).

---

## File Structure

```
sheet-email-sender/
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── db/
│   │   └── schema.sql
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI app, router registration, startup hook
│   │   ├── db.py               # Supabase client dependency
│   │   ├── sheet_parser.py      # parse_sheet() — sheet → list[dict]
│   │   ├── mailer.py           # build_message(), send_message()
│   │   ├── scheduler.py         # due_jobs(), process_job(), scheduler_loop()
│   │   └── routers/
│   │       ├── __init__.py
│   │       ├── upload.py       # POST /upload
│   │       ├── batches.py      # GET /batches/{id}, POST /batches/{id}/confirm
│   │       └── jobs.py         # GET /jobs
│   └── tests/
│       ├── conftest.py         # FakeSupabase test double
│       ├── test_sheet_parser.py
│       ├── test_upload.py
│       ├── test_batches.py
│       ├── test_jobs.py
│       ├── test_mailer.py
│       └── test_scheduler.py
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── index.html
    ├── .env.example
    └── src/
        ├── main.js
        ├── App.vue
        ├── plugins/
        │   └── vuetify.js      # minimal theme
        ├── router/
        │   └── index.js
        ├── api/
        │   └── client.js       # uploadSheet(), getBatch(), confirmBatch(), listJobs()
        └── views/
            ├── UploadView.vue
            ├── PreviewView.vue
            └── StatusView.vue
```

Backend files are split by responsibility: parsing, mailing, and scheduling are independent modules so each can be unit-tested without a real network call or real SMTP server. Frontend views map 1:1 to the three screens (Upload, Preview+Confirm combined, Status).

---

### Task 1: Backend scaffold, config, and Supabase client

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/__init__.py`
- Create: `backend/app/db.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_main.py`

**Interfaces:**
- Produces: `get_supabase() -> supabase.Client` in `app/db.py` — a FastAPI dependency every router will use via `Depends(get_supabase)`.
- Produces: `app` (the FastAPI instance) in `app/main.py`.

- [ ] **Step 1: Create `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
python-multipart==0.0.9
pandas==2.2.2
openpyxl==3.1.5
supabase==2.7.4
python-dotenv==1.0.1
pytest==8.3.2
pytest-asyncio==0.24.0
httpx==0.27.2
```

- [ ] **Step 2: Create `backend/.env.example`**

```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-or-anon-key
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASSWORD=your-app-password
```

- [ ] **Step 3: Set up the Python environment and install dependencies**

Run:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

- [ ] **Step 4: Create `backend/app/__init__.py`** (empty file, makes `app` a package)

- [ ] **Step 5: Create `backend/app/db.py`**

```python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


def get_supabase() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_KEY"]
    return create_client(url, key)
```

- [ ] **Step 6: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Sheet Email Sender")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 7: Write the failing test**

Create `backend/tests/test_main.py`:
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 8: Run the test to verify it passes**

Run (from `backend/`): `pytest tests/test_main.py -v`
Expected: PASS (this confirms the scaffold and test setup work end to end)

- [ ] **Step 9: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app backend/tests
git commit -m "feat: backend scaffold with FastAPI app and Supabase client dependency"
```

---

### Task 2: Supabase schema

**Files:**
- Create: `backend/db/schema.sql`

**Interfaces:**
- Produces: the `email_jobs` table that every later backend task reads/writes, with exactly these columns: `id, batch_id, to_email, from_email, cc, subject, content, attachment_filename, send_date, send_time, status, error_message, created_at, sent_at`.

- [ ] **Step 1: Create `backend/db/schema.sql`**

```sql
create table if not exists email_jobs (
    id uuid primary key default gen_random_uuid(),
    batch_id uuid not null,
    to_email text not null,
    from_email text not null,
    cc text,
    subject text,
    content text,
    attachment_filename text,
    send_date date,
    send_time time,
    status text not null default 'pending_review',
    error_message text,
    created_at timestamptz not null default now(),
    sent_at timestamptz
);

create index if not exists idx_email_jobs_batch_id on email_jobs (batch_id);
create index if not exists idx_email_jobs_status on email_jobs (status);
```

- [ ] **Step 2: Run this SQL in the Supabase project's SQL editor**

Open the Supabase dashboard → SQL Editor → paste the contents of `backend/db/schema.sql` → Run. Verify the `email_jobs` table appears under Table Editor with the columns listed above.

- [ ] **Step 3: Commit**

```bash
git add backend/db/schema.sql
git commit -m "feat: add email_jobs Supabase schema"
```

---

### Task 3: Sheet parser

**Files:**
- Create: `backend/app/sheet_parser.py`
- Test: `backend/tests/test_sheet_parser.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `parse_sheet(file_obj, filename: str) -> list[dict]` and `SheetParseError` (Exception), used by `routers/upload.py` (Task 4). Each dict has keys: `to_email, from_email, subject, content, cc, attachment_filename, send_date, send_time` — `send_date` is an ISO date string or `None`, `send_time` is an ISO time string or `None`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sheet_parser.py`:
```python
import io
import pytest
from app.sheet_parser import parse_sheet, SheetParseError


def _csv_bytes(text: str) -> io.BytesIO:
    return io.BytesIO(text.encode("utf-8"))


def test_parse_sheet_happy_path():
    csv_text = (
        "To,From,Subject,Email Content,CC,Attachment,Date,Time\n"
        "a@x.com,b@x.com,Hello,Hi there,c@x.com,report.pdf,2026-12-01,09:30:00\n"
    )
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    assert rows == [
        {
            "to_email": "a@x.com",
            "from_email": "b@x.com",
            "subject": "Hello",
            "content": "Hi there",
            "cc": "c@x.com",
            "attachment_filename": "report.pdf",
            "send_date": "2026-12-01",
            "send_time": "09:30:00",
        }
    ]


def test_parse_sheet_blank_optional_columns():
    csv_text = (
        "To,From,Subject,Email Content\n"
        "a@x.com,b@x.com,Hello,Hi there\n"
    )
    rows = parse_sheet(_csv_bytes(csv_text), "sheet.csv")
    row = rows[0]
    assert row["cc"] is None
    assert row["attachment_filename"] is None
    assert row["send_date"] is None
    assert row["send_time"] is None


def test_parse_sheet_missing_required_column_raises():
    csv_text = "From,Subject,Email Content\nb@x.com,Hello,Hi there\n"
    with pytest.raises(SheetParseError, match="To"):
        parse_sheet(_csv_bytes(csv_text), "sheet.csv")
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_sheet_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.sheet_parser'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/sheet_parser.py`:
```python
from typing import BinaryIO, Optional
import pandas as pd

REQUIRED_COLUMNS = ["To", "From", "Subject", "Email Content"]


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
                "from_email": str(row["From"]).strip(),
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

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_sheet_parser.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/sheet_parser.py backend/tests/test_sheet_parser.py
git commit -m "feat: add sheet parser for upload rows"
```

---

### Task 4: Upload endpoint

**Files:**
- Create: `backend/app/routers/__init__.py`
- Create: `backend/app/routers/upload.py`
- Modify: `backend/app/main.py` (register router)
- Create: `backend/tests/conftest.py`
- Test: `backend/tests/test_upload.py`

**Interfaces:**
- Consumes: `parse_sheet`, `SheetParseError` from Task 3; `get_supabase` from Task 1.
- Produces: `POST /upload` returning `{"batch_id": str, "rows": list[dict]}`. Produces `FakeSupabase` test double in `conftest.py`, reused by Tasks 5, 6, 7, 9.

- [ ] **Step 1: Create `backend/app/routers/__init__.py`** (empty file)

- [ ] **Step 2: Create the shared `FakeSupabase` test double in `backend/tests/conftest.py`**

```python
import pytest


class _FakeQuery:
    def __init__(self, table: "_FakeTable"):
        self.table = table
        self.filters = []
        self.action = None
        self.payload = None

    def insert(self, records):
        self.action = "insert"
        self.payload = records if isinstance(records, list) else [records]
        return self

    def select(self, *_args):
        self.action = "select"
        return self

    def update(self, payload):
        self.action = "update"
        self.payload = payload
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def in_(self, column, values):
        self.filters.append((column, set(values)))
        return self

    def order(self, *_args, **_kwargs):
        return self

    def execute(self):
        rows = self.table.rows
        for column, value in self.filters:
            if isinstance(value, set):
                rows = [r for r in rows if r.get(column) in value]
            else:
                rows = [r for r in rows if r.get(column) == value]

        if self.action == "insert":
            for record in self.payload:
                record.setdefault("id", f"id-{len(self.table.rows) + 1}")
                self.table.rows.append(record)
            return _Result(self.payload)

        if self.action == "update":
            for row in rows:
                row.update(self.payload)
            return _Result(rows)

        return _Result(rows)


class _Result:
    def __init__(self, data):
        self.data = data


class _FakeTable:
    def __init__(self):
        self.rows: list[dict] = []

    def query(self):
        return _FakeQuery(self)


class FakeSupabase:
    def __init__(self):
        self._tables: dict[str, _FakeTable] = {}

    def table(self, name: str) -> _FakeQuery:
        self._tables.setdefault(name, _FakeTable())
        return self._tables[name].query()


@pytest.fixture
def fake_db():
    return FakeSupabase()
```

- [ ] **Step 3: Write the failing test**

Create `backend/tests/test_upload.py`:
```python
import io
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_upload_parses_and_stores_rows(fake_db):
    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    csv_text = (
        "To,From,Subject,Email Content\n"
        "a@x.com,b@x.com,Hello,Hi there\n"
    )
    files = {"sheet": ("sheet.csv", io.BytesIO(csv_text.encode()), "text/csv")}
    response = client.post("/upload", files=files)

    assert response.status_code == 200
    body = response.json()
    assert "batch_id" in body
    assert len(body["rows"]) == 1
    assert body["rows"][0]["status"] == "pending_review"
    assert body["rows"][0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()
```

- [ ] **Step 4: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_upload.py -v`
Expected: FAIL (404, no `/upload` route yet)

- [ ] **Step 5: Write the implementation**

Create `backend/app/routers/upload.py`:
```python
import pathlib
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from ..db import get_supabase
from ..sheet_parser import SheetParseError, parse_sheet

router = APIRouter()
UPLOAD_DIR = pathlib.Path("uploads")


@router.post("/upload")
async def upload_sheet(
    sheet: UploadFile = File(...),
    attachments: list[UploadFile] = File(default=[]),
    db=Depends(get_supabase),
):
    try:
        rows = parse_sheet(sheet.file, sheet.filename)
    except SheetParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    batch_id = str(uuid.uuid4())
    batch_dir = UPLOAD_DIR / batch_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    for attachment in attachments:
        contents = await attachment.read()
        (batch_dir / attachment.filename).write_bytes(contents)

    records = [
        {**row, "batch_id": batch_id, "status": "pending_review"} for row in rows
    ]
    result = db.table("email_jobs").insert(records).execute()
    return {"batch_id": batch_id, "rows": result.data}
```

- [ ] **Step 6: Register the router in `backend/app/main.py`**

Add near the top:
```python
from .routers import upload
```
Add after the app is created:
```python
app.include_router(upload.router)
```

- [ ] **Step 7: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_upload.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routers backend/app/main.py backend/tests/conftest.py backend/tests/test_upload.py
git commit -m "feat: add upload endpoint for sheet parsing and storage"
```

---

### Task 5: Batch listing endpoint

**Files:**
- Create: `backend/app/routers/batches.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_batches.py`

**Interfaces:**
- Consumes: `get_supabase` (Task 1), `FakeSupabase`/`fake_db` fixture (Task 4).
- Produces: `GET /batches/{batch_id}` returning `{"rows": list[dict]}`. `router` object exported as `batches.router`, extended by Task 6 in the same file.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_batches.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_get_batch_returns_its_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review"}]
    ).execute()
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b2", "to_email": "z@x.com", "status": "pending_review"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/batches/b1")

    assert response.status_code == 200
    rows = response.json()["rows"]
    assert len(rows) == 1
    assert rows[0]["to_email"] == "a@x.com"

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_batches.py -v`
Expected: FAIL (404, no `/batches/{batch_id}` route yet)

- [ ] **Step 3: Write the implementation**

Create `backend/app/routers/batches.py`:
```python
from fastapi import APIRouter, Depends

from ..db import get_supabase

router = APIRouter()


@router.get("/batches/{batch_id}")
def get_batch(batch_id: str, db=Depends(get_supabase)):
    result = db.table("email_jobs").select("*").eq("batch_id", batch_id).execute()
    return {"rows": result.data}
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Add to the imports:
```python
from .routers import batches
```
Add after `app.include_router(upload.router)`:
```python
app.include_router(batches.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_batches.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/batches.py backend/app/main.py backend/tests/test_batches.py
git commit -m "feat: add batch listing endpoint"
```

---

### Task 6: Confirm endpoint

**Files:**
- Modify: `backend/app/routers/batches.py` (add confirm route)
- Test: `backend/tests/test_batches.py` (add confirm tests)

**Interfaces:**
- Consumes: `get_supabase` (Task 1), `router` from `batches.py` (Task 5).
- Produces: `POST /batches/{batch_id}/confirm` returning `{"batch_id": str, "status": "confirmed"}`, after flipping each row's `status` to `"queued"` (if due now or no date given) or `"scheduled"` (if in the future).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_batches.py`:
```python
def test_confirm_batch_queues_rows_without_date(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b1", "to_email": "a@x.com", "status": "pending_review",
          "send_date": None, "send_time": None}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.post("/batches/b1/confirm")

    assert response.status_code == 200
    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b1").execute().data
    assert rows[0]["status"] == "queued"

    app.dependency_overrides.clear()


def test_confirm_batch_schedules_future_rows(fake_db):
    fake_db.table("email_jobs").insert(
        [{"batch_id": "b2", "to_email": "a@x.com", "status": "pending_review",
          "send_date": "2099-01-01", "send_time": "09:00:00"}]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    client.post("/batches/b2/confirm")

    rows = fake_db.table("email_jobs").select("*").eq("batch_id", "b2").execute().data
    assert rows[0]["status"] == "scheduled"

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_batches.py -v`
Expected: FAIL (404, no confirm route yet)

- [ ] **Step 3: Write the implementation**

Append to `backend/app/routers/batches.py`:
```python
from datetime import datetime


@router.post("/batches/{batch_id}/confirm")
def confirm_batch(batch_id: str, db=Depends(get_supabase)):
    rows = db.table("email_jobs").select("*").eq("batch_id", batch_id).execute().data
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

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_batches.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/batches.py backend/tests/test_batches.py
git commit -m "feat: add confirm endpoint to queue or schedule batch rows"
```

---

### Task 7: Jobs listing endpoint

**Files:**
- Create: `backend/app/routers/jobs.py`
- Modify: `backend/app/main.py` (register router)
- Test: `backend/tests/test_jobs.py`

**Interfaces:**
- Consumes: `get_supabase` (Task 1).
- Produces: `GET /jobs?status=&batch_id=` returning `{"jobs": list[dict]}`, used by the Status view (Task 12).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_jobs.py`:
```python
from fastapi.testclient import TestClient
from app.main import app
from app.db import get_supabase


def test_list_jobs_filters_by_status(fake_db):
    fake_db.table("email_jobs").insert(
        [
            {"batch_id": "b1", "to_email": "a@x.com", "status": "sent"},
            {"batch_id": "b1", "to_email": "b@x.com", "status": "failed"},
        ]
    ).execute()

    app.dependency_overrides[get_supabase] = lambda: fake_db
    client = TestClient(app)

    response = client.get("/jobs", params={"status": "failed"})

    assert response.status_code == 200
    jobs = response.json()["jobs"]
    assert len(jobs) == 1
    assert jobs[0]["to_email"] == "b@x.com"

    app.dependency_overrides.clear()
```

- [ ] **Step 2: Run test to verify it fails**

Run (from `backend/`): `pytest tests/test_jobs.py -v`
Expected: FAIL (404, no `/jobs` route yet)

- [ ] **Step 3: Write the implementation**

Create `backend/app/routers/jobs.py`:
```python
from typing import Optional

from fastapi import APIRouter, Depends

from ..db import get_supabase

router = APIRouter()


@router.get("/jobs")
def list_jobs(
    status: Optional[str] = None,
    batch_id: Optional[str] = None,
    db=Depends(get_supabase),
):
    query = db.table("email_jobs").select("*")
    if status:
        query = query.eq("status", status)
    if batch_id:
        query = query.eq("batch_id", batch_id)
    result = query.order("created_at", desc=True).execute()
    return {"jobs": result.data}
```

- [ ] **Step 4: Register the router in `backend/app/main.py`**

Add to imports:
```python
from .routers import jobs
```
Add after `app.include_router(batches.router)`:
```python
app.include_router(jobs.router)
```

- [ ] **Step 5: Run test to verify it passes**

Run (from `backend/`): `pytest tests/test_jobs.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/jobs.py backend/app/main.py backend/tests/test_jobs.py
git commit -m "feat: add jobs listing endpoint for status tracking"
```

---

### Task 8: Mailer module

**Files:**
- Create: `backend/app/mailer.py`
- Test: `backend/tests/test_mailer.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `build_message(job: dict, attachment_path: pathlib.Path | None) -> EmailMessage` and `send_message(msg: EmailMessage) -> None`, both used by `scheduler.py` (Task 9).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_mailer.py`:
```python
import pathlib
from email.message import EmailMessage

import pytest

from app.mailer import build_message, send_message


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


def test_send_message_calls_smtp(monkeypatch):
    sent = {}

    class FakeSMTP:
        def __init__(self, host, port):
            sent["host"] = host
            sent["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def starttls(self):
            sent["starttls"] = True

        def login(self, user, password):
            sent["login"] = (user, password)

        def send_message(self, msg):
            sent["message"] = msg

    monkeypatch.setenv("SMTP_HOST", "smtp.test.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@test.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setattr("app.mailer.smtplib.SMTP", FakeSMTP)

    msg = EmailMessage()
    msg["To"] = "a@x.com"
    send_message(msg)

    assert sent["host"] == "smtp.test.com"
    assert sent["port"] == 587
    assert sent["login"] == ("user@test.com", "secret")
    assert sent["message"] is msg
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_mailer.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.mailer'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/mailer.py`:
```python
import os
import pathlib
import smtplib
from email.message import EmailMessage
from typing import Optional


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


def send_message(msg: EmailMessage) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ["SMTP_PORT"])
    user = os.environ["SMTP_USER"]
    password = os.environ["SMTP_PASSWORD"]

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)
```

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_mailer.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/mailer.py backend/tests/test_mailer.py
git commit -m "feat: add mailer module for building and sending SMTP messages"
```

---

### Task 9: Scheduler

**Files:**
- Create: `backend/app/scheduler.py`
- Modify: `backend/app/main.py` (start scheduler on startup)
- Test: `backend/tests/test_scheduler.py`

**Interfaces:**
- Consumes: `build_message`, `send_message` (Task 8); `get_supabase` (Task 1); `FakeSupabase` (Task 4).
- Produces: `due_jobs(db) -> list[dict]`, `process_job(db, job: dict) -> None`, `scheduler_loop(db_factory=get_supabase) -> None` (the last one is wired into FastAPI's startup event, not unit tested directly — its building blocks are).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_scheduler.py`:
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
    fake_db.table("email_jobs").insert(
        [{"id": "job-1", "batch_id": "b1", "to_email": "a@x.com", "from_email": "b@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]

    monkeypatch.setattr("app.scheduler.send_message", lambda msg: None)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-1").execute().data[0]
    assert updated["status"] == "sent"
    assert updated["sent_at"] is not None


def test_process_job_marks_failed_on_exception(fake_db, monkeypatch):
    fake_db.table("email_jobs").insert(
        [{"id": "job-2", "batch_id": "b1", "to_email": "a@x.com", "from_email": "b@x.com",
          "cc": None, "subject": "Hi", "content": "Body", "attachment_filename": None,
          "status": "queued"}]
    ).execute()
    job = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]

    def _raise(msg):
        raise RuntimeError("smtp down")

    monkeypatch.setattr("app.scheduler.send_message", _raise)

    process_job(fake_db, job)

    updated = fake_db.table("email_jobs").select("*").eq("id", "job-2").execute().data[0]
    assert updated["status"] == "failed"
    assert "smtp down" in updated["error_message"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `backend/`): `pytest tests/test_scheduler.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.scheduler'`

- [ ] **Step 3: Write the implementation**

Create `backend/app/scheduler.py`:
```python
import asyncio
import pathlib
from datetime import datetime

from .db import get_supabase
from .mailer import build_message, send_message

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
        send_message(msg)
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

- [ ] **Step 4: Run tests to verify they pass**

Run (from `backend/`): `pytest tests/test_scheduler.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Wire the scheduler into startup in `backend/app/main.py`**

Add to imports:
```python
import asyncio
from .scheduler import scheduler_loop
```
Add after the routers are included:
```python
@app.on_event("startup")
async def start_scheduler():
    asyncio.create_task(scheduler_loop())
```

- [ ] **Step 6: Run the full backend test suite to confirm nothing broke**

Run (from `backend/`): `pytest -v`
Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add backend/app/scheduler.py backend/app/main.py backend/tests/test_scheduler.py
git commit -m "feat: add scheduler loop to send due queued and scheduled jobs"
```

---

### Task 10: Frontend scaffold — Vite, Vuetify minimal theme, router, API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.js`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`
- Create: `frontend/src/main.js`
- Create: `frontend/src/App.vue`
- Create: `frontend/src/plugins/vuetify.js`
- Create: `frontend/src/router/index.js`
- Create: `frontend/src/api/client.js`
- Create: `frontend/src/views/UploadView.vue` (placeholder shell, filled in Task 11)

**Interfaces:**
- Produces: `uploadSheet(sheetFile, attachmentFiles) -> Promise`, `getBatch(batchId) -> Promise`, `confirmBatch(batchId) -> Promise`, `listJobs(params) -> Promise` in `src/api/client.js`, used by Tasks 11 and 12.
- Produces: router with named routes `upload`, `preview`, `status`, used by Tasks 11 and 12 for navigation.

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "sheet-email-sender-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "vue": "^3.4.38",
    "vue-router": "^4.4.3",
    "vuetify": "^3.7.0"
  },
  "devDependencies": {
    "@mdi/font": "^7.4.47",
    "@vitejs/plugin-vue": "^5.1.3",
    "vite": "^5.4.2"
  }
}
```

- [ ] **Step 2: Create `frontend/vite.config.js`**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()]
})
```

- [ ] **Step 3: Create `frontend/index.html`**

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Sheet Email Sender</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 4: Create `frontend/.env.example`**

```
VITE_API_BASE_URL=http://localhost:8000
```

- [ ] **Step 5: Create `frontend/src/plugins/vuetify.js`**

```javascript
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'
import '@mdi/font/css/materialdesignicons.css'

export default createVuetify({
  components,
  directives,
  theme: {
    defaultTheme: 'minimal',
    themes: {
      minimal: {
        dark: false,
        colors: {
          background: '#FAFAFA',
          surface: '#FFFFFF',
          primary: '#3B82F6',
          secondary: '#64748B',
          error: '#EF4444',
          success: '#22C55E',
          warning: '#F59E0B'
        }
      }
    }
  },
  defaults: {
    VCard: { elevation: 0, rounded: 'lg', class: 'pa-2' },
    VBtn: { elevation: 0, rounded: 'lg' },
    VAppBar: { elevation: 0 }
  }
})
```

- [ ] **Step 6: Create `frontend/src/api/client.js`**

```javascript
import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
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

- [ ] **Step 7: Create a placeholder `frontend/src/views/UploadView.vue`** (filled in fully in Task 11)

```vue
<template>
  <v-container class="py-10" style="max-width: 480px">
    <h1 class="text-h5 font-weight-medium mb-4">Upload</h1>
  </v-container>
</template>

<script setup></script>
```

- [ ] **Step 8: Create `frontend/src/router/index.js`**

```javascript
import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '../views/UploadView.vue'

const routes = [
  { path: '/', redirect: '/upload' },
  { path: '/upload', name: 'upload', component: UploadView }
]

export default createRouter({
  history: createWebHistory(),
  routes
})
```

- [ ] **Step 9: Create `frontend/src/App.vue`**

```vue
<template>
  <v-app>
    <v-app-bar color="background" flat>
      <v-container class="d-flex align-center" style="max-width: 960px">
        <span class="text-subtitle-1 font-weight-medium">Sheet Email Sender</span>
        <v-spacer />
        <v-btn variant="text" :to="{ name: 'upload' }">Upload</v-btn>
      </v-container>
    </v-app-bar>
    <v-main>
      <router-view />
    </v-main>
  </v-app>
</template>

<script setup></script>
```

- [ ] **Step 10: Create `frontend/src/main.js`**

```javascript
import { createApp } from 'vue'
import App from './App.vue'
import vuetify from './plugins/vuetify'
import router from './router'

createApp(App).use(vuetify).use(router).mount('#app')
```

- [ ] **Step 11: Install dependencies and verify the dev server runs**

Run:
```bash
cd frontend
npm install
npm run dev
```
Open the printed localhost URL in a browser. Expected: a minimal app bar reading "Sheet Email Sender" with an "Upload" link, and an empty "Upload" heading below it. No console errors.

- [ ] **Step 12: Commit**

```bash
git add frontend/package.json frontend/vite.config.js frontend/index.html frontend/.env.example frontend/src
git commit -m "feat: scaffold Vue 3 + Vuetify frontend with minimal theme and router"
```

---

### Task 11: Upload and Preview views

**Files:**
- Modify: `frontend/src/views/UploadView.vue` (full implementation)
- Create: `frontend/src/views/PreviewView.vue`
- Modify: `frontend/src/router/index.js` (add `preview` route)

**Interfaces:**
- Consumes: `uploadSheet`, `getBatch`, `confirmBatch` from `src/api/client.js` (Task 10).
- Produces: route `preview` taking a `batchId` prop, navigated to from `UploadView` after a successful upload; navigates to `status` on confirm (wired fully in Task 12, where the `status` route is added).

- [ ] **Step 1: Implement `frontend/src/views/UploadView.vue`**

```vue
<template>
  <v-container class="py-10" style="max-width: 480px">
    <h1 class="text-h5 font-weight-medium mb-1">Upload a sheet</h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      Columns: To, From, Subject, Email Content, CC, Attachment, Date, Time.
    </p>

    <v-card class="pa-6">
      <v-file-input
        v-model="sheetFile"
        label="Sheet (.xlsx or .csv)"
        accept=".xlsx,.csv"
        density="comfortable"
        variant="outlined"
      />
      <v-file-input
        v-model="attachmentFiles"
        label="Attachments (optional)"
        multiple
        density="comfortable"
        variant="outlined"
      />

      <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
        {{ errorMessage }}
      </v-alert>

      <v-btn
        color="primary"
        block
        :loading="loading"
        :disabled="!sheetFile"
        @click="submit"
      >
        Upload
      </v-btn>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { uploadSheet } from '../api/client'

const router = useRouter()
const sheetFile = ref(null)
const attachmentFiles = ref([])
const loading = ref(false)
const errorMessage = ref('')

async function submit() {
  loading.value = true
  errorMessage.value = ''
  try {
    const file = Array.isArray(sheetFile.value) ? sheetFile.value[0] : sheetFile.value
    const result = await uploadSheet(file, attachmentFiles.value || [])
    router.push({ name: 'preview', params: { batchId: result.batch_id } })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Upload failed. Check your sheet and try again.'
  } finally {
    loading.value = false
  }
}
</script>
```

- [ ] **Step 2: Create `frontend/src/views/PreviewView.vue`**

```vue
<template>
  <v-container class="py-10" style="max-width: 960px">
    <h1 class="text-h5 font-weight-medium mb-1">Preview</h1>
    <p class="text-body-2 text-medium-emphasis mb-6">
      Review the parsed rows below. To fix a mistake, re-upload the sheet instead of editing here.
    </p>

    <v-card class="pa-4">
      <v-data-table :headers="headers" :items="rows" :loading="loading" density="comfortable">
        <template #item.content="{ item }">
          {{ truncate(item.content) }}
        </template>
      </v-data-table>

      <v-alert v-if="errorMessage" type="error" density="compact" class="mt-4">
        {{ errorMessage }}
      </v-alert>

      <div class="d-flex justify-end mt-4">
        <v-btn color="primary" :loading="confirming" :disabled="rows.length === 0" @click="confirm">
          Confirm & Queue
        </v-btn>
      </div>
    </v-card>
  </v-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { confirmBatch, getBatch } from '../api/client'

const props = defineProps({ batchId: { type: String, required: true } })
const router = useRouter()

const rows = ref([])
const loading = ref(true)
const confirming = ref(false)
const errorMessage = ref('')

const headers = [
  { title: 'To', key: 'to_email' },
  { title: 'Subject', key: 'subject' },
  { title: 'Content', key: 'content' },
  { title: 'Date', key: 'send_date' },
  { title: 'Time', key: 'send_time' },
  { title: 'Attachment', key: 'attachment_filename' }
]

function truncate(text) {
  if (!text) return ''
  return text.length > 60 ? `${text.slice(0, 60)}…` : text
}

async function load() {
  loading.value = true
  const data = await getBatch(props.batchId)
  rows.value = data.rows
  loading.value = false
}

async function confirm() {
  confirming.value = true
  errorMessage.value = ''
  try {
    await confirmBatch(props.batchId)
    router.push({ name: 'status' })
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Could not confirm this batch.'
  } finally {
    confirming.value = false
  }
}

onMounted(load)
</script>
```

- [ ] **Step 3: Add the `preview` route to `frontend/src/router/index.js`**

```javascript
import PreviewView from '../views/PreviewView.vue'
```
Add to the `routes` array:
```javascript
{ path: '/preview/:batchId', name: 'preview', component: PreviewView, props: true }
```

- [ ] **Step 4: Verify the upload-to-preview flow manually**

With the backend running (`uvicorn app.main:app --reload` from `backend/`) and the frontend dev server running:
1. On the Upload screen, pick a small `.csv` file with the required columns and click Upload.
2. Confirm you land on `/preview/<batch-id>` and see the parsed rows in the table.
3. Click "Confirm & Queue" — expect no error alert (navigation to `/status` will 404 until Task 12 adds that route; that's expected at this point).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/UploadView.vue frontend/src/views/PreviewView.vue frontend/src/router/index.js
git commit -m "feat: add upload and preview views with confirm action"
```

---

### Task 12: Status/Track view

**Files:**
- Create: `frontend/src/views/StatusView.vue`
- Modify: `frontend/src/router/index.js` (add `status` route)
- Modify: `frontend/src/App.vue` (add Status nav link)

**Interfaces:**
- Consumes: `listJobs` from `src/api/client.js` (Task 10).
- Produces: route `status`, the confirm navigation target from Task 11.

- [ ] **Step 1: Create `frontend/src/views/StatusView.vue`**

```vue
<template>
  <v-container class="py-10" style="max-width: 960px">
    <div class="d-flex align-center mb-1">
      <h1 class="text-h5 font-weight-medium">Status</h1>
      <v-spacer />
      <v-btn variant="text" :loading="loading" @click="load">Refresh</v-btn>
    </div>
    <p class="text-body-2 text-medium-emphasis mb-6">Tracks every uploaded row across all batches.</p>

    <v-card class="pa-4">
      <v-data-table :headers="headers" :items="jobs" :loading="loading" density="comfortable">
        <template #item.status="{ item }">
          <v-chip :color="statusColor(item.status)" size="small" variant="flat">
            {{ item.status }}
          </v-chip>
        </template>
        <template #item.error_message="{ item }">
          <span v-if="item.error_message" class="text-error text-body-2">{{ item.error_message }}</span>
        </template>
      </v-data-table>
    </v-card>
  </v-container>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { listJobs } from '../api/client'

const jobs = ref([])
const loading = ref(true)

const headers = [
  { title: 'To', key: 'to_email' },
  { title: 'Subject', key: 'subject' },
  { title: 'Status', key: 'status' },
  { title: 'Sent at', key: 'sent_at' },
  { title: 'Error', key: 'error_message' }
]

const statusColors = {
  pending_review: 'secondary',
  scheduled: 'warning',
  queued: 'warning',
  sent: 'success',
  failed: 'error'
}

function statusColor(status) {
  return statusColors[status] || 'secondary'
}

async function load() {
  loading.value = true
  const data = await listJobs()
  jobs.value = data.jobs
  loading.value = false
}

onMounted(load)
</script>
```

- [ ] **Step 2: Add the `status` route to `frontend/src/router/index.js`**

```javascript
import StatusView from '../views/StatusView.vue'
```
Add to the `routes` array:
```javascript
{ path: '/status', name: 'status', component: StatusView }
```

- [ ] **Step 3: Add a Status nav link in `frontend/src/App.vue`**

In the app bar, after the Upload button:
```vue
<v-btn variant="text" :to="{ name: 'status' }">Status</v-btn>
```

- [ ] **Step 4: Verify the full flow manually end to end**

With backend and frontend dev servers running:
1. Upload a sheet with at least one row with a blank Date/Time and one with a future Date/Time.
2. Preview shows both rows correctly.
3. Click Confirm & Queue — should land on `/status`.
4. Within ~60 seconds, the blank-date row should flip to `sent` (check your inbox) or `failed` (check `error_message`). The future-dated row should show `scheduled` until its time arrives.
5. Click Refresh and confirm the table updates without a full page reload.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/views/StatusView.vue frontend/src/router/index.js frontend/src/App.vue
git commit -m "feat: add status view for tracking job states"
```

---

## Self-Review Notes

- **Spec coverage:** Upload→Preview→Confirm→Send/Schedule→Track covered by Tasks 4/11, 5/11, 6/11, 9, 7/12 respectively. Attachment soft-fail behavior implemented in Task 9 (`process_job`). SMTP config via env vars (Task 1). Minimal Vuetify styling addressed in Task 10's theme. No auth, no retries, no in-place editing — none implemented, matching "out of scope."
- **Placeholder scan:** no TBD/TODO; all steps contain full code.
- **Type consistency:** `email_jobs` column names in Task 2's schema match the dict keys used in `sheet_parser.py` (Task 3), `upload.py` (Task 4), `scheduler.py` (Task 9), and the Vuetify table headers (Tasks 11–12) — `to_email`, `from_email`, `cc`, `subject`, `content`, `attachment_filename`, `send_date`, `send_time`, `status`, `error_message`, `sent_at`, `batch_id`.
