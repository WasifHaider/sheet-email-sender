# Sheet-Based Email Sender — Design

## Goal
Upload Excel/CSV sheet → preview parsed emails → confirm → send now or
schedule → track status. Small scale, single-user/internal use, no
auth required in v1. Built to be extendable later (Vue frontend chosen
for that reason).

## Stack
- **Backend:** Python + FastAPI (REST API only, no server-rendered pages)
- **Database:** Supabase (hosted Postgres, free tier)
- **Email sending:** SMTP via `smtplib`, one sender account configured
  through environment variables (host, port, user, app password)
- **Frontend:** Vue 3 + Vuetify (Vite build), separate app, calls
  backend over REST/JSON
- **Scheduler:** `asyncio` background task inside the FastAPI process,
  polls every 60s for due emails
- **Deployment:** none yet — runs locally for now; both backend and
  frontend are plain enough to deploy later to any host (Render,
  Railway, Fly.io, etc.) without rework

## Data model (Supabase table: `email_jobs`)
| column | type | notes |
|---|---|---|
| id | uuid (pk) | |
| batch_id | uuid | groups rows from one upload |
| to_email | text | required |
| from_email | text | required, must match configured SMTP account |
| cc | text | optional, comma-separated |
| subject | text | |
| content | text | plain text or HTML as given in sheet |
| attachment_filename | text, nullable | matched against uploaded attachment files |
| send_date | date, nullable | blank = send immediately on confirm |
| send_time | time, nullable | |
| status | text | `pending_review` \| `scheduled` \| `queued` \| `sent` \| `failed` |
| error_message | text, nullable | set when status = failed |
| created_at | timestamptz | |
| sent_at | timestamptz, nullable | |

## API endpoints
- `POST /upload` — multipart: sheet file (+ optional attachment files).
  Parses rows with `pandas`/`openpyxl`, inserts as `pending_review`
  rows under a new `batch_id`. Returns batch_id + parsed rows for preview.
- `GET /batches/{batch_id}` — list rows in a batch (for preview/status view).
- `POST /batches/{batch_id}/confirm` — flips rows to `scheduled` if
  send_date/time is in the future, else `queued` (sent on next
  scheduler tick).
- `GET /jobs` — list all jobs with status, for the tracking view
  (filter by batch_id or status optional).

## Frontend (Vue + Vuetify) screens
1. **Upload** — file picker (sheet + optional attachments zip/multi-file), submit.
2. **Preview** — Vuetify `v-data-table` of parsed rows (To, Subject,
   Date/Time, content snippet, attachment name). Read-only in v1 — bad
   rows get fixed in the sheet and re-uploaded.
3. **Confirm** — button on the preview screen; calls confirm endpoint,
   navigates to status view.
4. **Status/Track** — `v-data-table` of all jobs with status chips
   (pending/scheduled/queued/sent/failed), error tooltip on failed rows,
   manual refresh button (no need for websockets at this scale).

## Attachment handling
Sheet's "Attachment" column holds a filename. User uploads matching
files alongside the sheet in the same upload call. Backend stores them
under `uploads/{batch_id}/` and matches by filename at send time. If a
row's attachment file is missing, email still sends without it and a
warning is recorded in `error_message` (not a hard failure).

## Sending logic (scheduler tick, every 60s)
1. Query jobs where `status IN ('queued','scheduled')` and
   (`status = 'queued'` OR `send_date+send_time <= now`).
2. For each: build `email.message.EmailMessage`, attach file if present,
   send via `smtplib.SMTP_SSL`/`starttls`, set status `sent` + `sent_at`,
   or `failed` + `error_message` on exception.
3. No automatic retries in v1 — a failed row stays failed; user can
   fix and re-upload that row via a new batch.

## Explicitly out of scope (v1)
- Auth / multi-user / multi-tenant isolation
- Editing parsed rows before send (fix in sheet, re-upload instead)
- Retry logic / dead-letter handling
- Rich HTML email composer (content column used as-is)
- Rate-limiting beyond relying on SMTP provider's own limits

## Testing approach
- Backend: unit tests for sheet parsing (good rows, missing columns,
  bad dates) and for the scheduler's due-row query logic. Mock
  `smtplib` for send tests — assert correct message built and status
  transitions, without real network sends.
- Frontend: manual testing of the 4-screen flow against the running
  local backend (small scale, no need for e2e framework in v1).
