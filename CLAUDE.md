# Sheet-Based Email Sender

Upload Excel/CSV sheet → preview parsed emails → confirm → send/schedule via SMTP → track status.

- Spec: [docs/superpowers/specs/2026-10-15-sheet-email-sender-design.md](docs/superpowers/specs/2026-10-15-sheet-email-sender-design.md)
- Plan: [docs/superpowers/plans/2026-10-15-sheet-email-sender.md](docs/superpowers/plans/2026-10-15-sheet-email-sender.md)
- Execution mode: inline, one task at a time, discuss after each task, working directly on `master`.

## Stack
FastAPI + Supabase (Postgres) + SMTP (`smtplib`) backend; Vue 3 + Vuetify (Vite) frontend, minimal/sleek theme. No auth in v1.

## Setup
Backend:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest
```
Copy `backend/.env.example` to `backend/.env` and fill in real Supabase + SMTP credentials before running the server for real.

## Progress

### Task 1 — Backend scaffold, config, Supabase client ✅ (2026-10-15)
- Created `backend/app/main.py` (FastAPI app, `/health`), `backend/app/db.py` (`get_supabase()` dependency), `backend/requirements.txt`, `backend/.env.example`.
- Added root `.gitignore` (venv, caches, uploads, node_modules, .env files).
- Test: `backend/tests/test_main.py::test_health` — PASSED.
- Verified: `pytest tests/test_main.py -v` → 1 passed.
- Commit: `ae13514`.

### Task 2 — Supabase schema ✅ (2026-10-15)
- Created `backend/db/schema.sql` (`email_jobs` table + batch_id/status indexes).
- User ran it in Supabase SQL Editor; `email_jobs` table confirmed created.
- Commit: `31be6d5`.
### Task 3 — Sheet parser ✅ (2026-10-15)
- Created `backend/app/sheet_parser.py` (`parse_sheet()`, `SheetParseError`).
- Tests: `backend/tests/test_sheet_parser.py` — 3 passed (happy path, blank optionals, missing required column).
- Commit: `0f74680`.
### Task 4 — Upload endpoint ✅ (2026-10-15)
- Created `backend/app/routers/upload.py` (`POST /upload`), registered in `main.py`.
- Created shared `FakeSupabase` test double in `backend/tests/conftest.py` (reused by later task tests).
- Test: `backend/tests/test_upload.py` — passed. Full suite: 5 passed.
- Commit: `56ca1ce`.
### Task 5 — Batch listing endpoint — not started
### Task 6 — Confirm endpoint — not started
### Task 7 — Jobs listing endpoint — not started
### Task 8 — Mailer module — not started
### Task 9 — Scheduler — not started
### Task 10 — Frontend scaffold — not started
### Task 11 — Upload and Preview views — not started
### Task 12 — Status/Track view — not started

## Notes / decisions
- Working directly on `master`, no feature branches (solo, simple project).
- Deploy target undecided — running locally for now (per user).
- Git identity for this repo (personal project): `WasifHaider <mwasifhaider1@gmail.com>`, set locally via `git config user.name/user.email` in this repo — overrides the machine's global work identity.
