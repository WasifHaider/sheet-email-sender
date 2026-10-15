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

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Copy `frontend/.env.example` to `frontend/.env` if the backend isn't at `http://localhost:8000`.

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
### Task 5 — Batch listing endpoint ✅ (2026-10-15)
- Created `backend/app/routers/batches.py` (`GET /batches/{batch_id}`), registered in `main.py`.
- Test: `backend/tests/test_batches.py` — passed. Full suite: 6 passed.
### Task 6 — Confirm endpoint ✅ (2026-10-15)
- Added `POST /batches/{batch_id}/confirm` to `backend/app/routers/batches.py`: flips rows to `queued` (no date / due now) or `scheduled` (future date).
- Tests added to `backend/tests/test_batches.py`. Full suite: 8 passed.
### Task 7 — Jobs listing endpoint ✅ (2026-10-15)
- Created `backend/app/routers/jobs.py` (`GET /jobs?status=&batch_id=`), registered in `main.py`.
- Test: `backend/tests/test_jobs.py` — passed. Full suite: 9 passed.
### Task 8 — Mailer module ✅ (2026-10-15)
- Created `backend/app/mailer.py` (`build_message()`, `send_message()`), SMTP calls mocked in tests.
- Tests: `backend/tests/test_mailer.py` — 3 passed. Full suite: 12 passed.
### Task 9 — Scheduler ✅ (2026-10-15)
- Created `backend/app/scheduler.py` (`due_jobs()`, `process_job()`, `scheduler_loop()`), polls every 60s.
- Wired into `main.py` startup event (`asyncio.create_task(scheduler_loop())`).
- Tests: `backend/tests/test_scheduler.py` — 3 passed. Full backend suite: 15 passed.
- **Backend is functionally complete** (all 4 endpoints + scheduler + mailer).
### Task 10 — Frontend scaffold ✅ (2026-10-15)
- Created Vite + Vue 3 + Vuetify app in `frontend/`: `src/main.js`, `App.vue`, `plugins/vuetify.js` (minimal theme: muted blue primary, flat cards/buttons), `router/index.js`, `api/client.js` (`uploadSheet`, `getBatch`, `confirmBatch`, `listJobs`), placeholder `UploadView.vue`.
- Added `.claude/launch.json` so `preview_start` can run `npm --prefix frontend run dev` for browser testing.
- Verified in browser: dev server runs, `/` redirects to `/upload`, app bar + heading render, no console errors.
### Task 11 — Upload and Preview views ✅ (2026-10-15)
- Full `UploadView.vue` (file inputs, upload + navigate to preview) and `PreviewView.vue` (data table, Confirm & Queue button) implemented. Added `preview` route.
- Fixed a gap found during manual verification: `PreviewView`'s `load()` had no error handling — a failed fetch left the table stuck on "Loading items..." forever. Added try/catch/finally matching the pattern already used in `confirm()`.
- Verified in browser (no real Supabase credentials available yet, so DB calls fail by design — used that to test error paths): Upload screen renders correctly; Preview screen on a failed fetch now shows a dismissable error instead of hanging, Confirm button correctly disabled with 0 rows.
- **Still needed before this app can actually send/store anything for real:** real Supabase URL + key and SMTP credentials in `backend/.env` (not committed, `.env.example` has the shape).
### Task 12 — Status/Track view — not started

## Notes / decisions
- Working directly on `master`, no feature branches (solo, simple project).
- Deploy target undecided — running locally for now (per user).
- Git identity for this repo (personal project): `WasifHaider <mwasifhaider1@gmail.com>`, set locally via `git config user.name/user.email` in this repo — overrides the machine's global work identity.
