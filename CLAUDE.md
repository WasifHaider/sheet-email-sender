# Sheet-Based Email Sender

Upload Excel/CSV sheet → preview parsed emails → confirm → send/schedule via SMTP → track status.

- Spec: [docs/superpowers/specs/2026-10-15-sheet-email-sender-design.md](docs/superpowers/specs/2026-10-15-sheet-email-sender-design.md)
- Plan: [docs/superpowers/plans/2026-10-15-sheet-email-sender.md](docs/superpowers/plans/2026-10-15-sheet-email-sender.md)
- Execution mode: inline, one task at a time, discuss after each task, working directly on `master`.

## Stack
FastAPI + Supabase (Postgres) + SMTP (`smtplib`) backend; Vue 3 (Vite) frontend with Vuetify installed but mostly unused — UI is hand-styled to match an approved design (Mono theme, light/dark mode, see `frontend/src/theme/mono.js`). No auth in v1.

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
### Visual redesign — Modern SaaS ✅ (2026-10-15)
User felt the original minimal/flat design looked too basic. Used the `superdesign` skill to explore a "Modern SaaS" direction (Linear/Stripe dashboard feel) on Superdesign's canvas, user approved it, then it was hand-ported into real Vuetify code:
- New theme in `frontend/src/plugins/vuetify.js`: indigo/violet (`#6366F1`) primary, `#F8FAFC` background, elevated rounded-xl cards instead of flat.
- `frontend/src/assets/main.css` (new): Plus Jakarta Sans font, `.gradient-btn` (indigo→violet gradient primary actions), `.elevated-card`/`.app-bar-shadow` shadows, `.status-chip-*` color classes.
- `App.vue`: icon + bold title, active-route nav highlighting, Upload/Status links.
- `UploadView.vue` / `PreviewView.vue`: redesigned with dropzone icon card, mdi icons throughout, gradient buttons, row-count chip, info/hint cards.
- Superdesign project artifacts kept in `.superdesign/` (`init/` repo analysis, `design-system.md`) for any future iteration — not needed for the app to run.
- Commits: redesign + Status view.

### Task 12 — Status/Track view ✅ (2026-10-15, built as part of the redesign above)
- Created `frontend/src/views/StatusView.vue`: stat cards (Sent/Scheduled/Failed/Pending review counts, computed client-side from `listJobs()`), data table with color-coded status chips (`mdi-check-circle`/`mdi-clock-outline`/`mdi-alert-circle`/`mdi-file-document-outline`), Refresh button, error handling on load.
- Added `/status` route to `router/index.js`.
- **All 12 plan tasks complete.** App has upload→preview→confirm→send/schedule→track fully wired, but still needs real Supabase + SMTP credentials in `backend/.env` before anything actually works end-to-end — see Task 11 note above (`.env.example` has the shape).

### Visual redesign v2 — Mono theme (light/dark) ✅ (2026-10-15)
User brought an updated design made externally with Claude Design (claude.ai/design prototype, `.dc.html` format using a custom templating engine) — superseded the Modern SaaS redesign above. Downloaded from `C:\Users\whaid\Downloads\Sheet Email Sender Design\`, source copied into `design/claude-design-prototype/` for reference. Hand-ported into real Vue/Vuetify code (the prototype used its own template engine, not Vue):
- Picked **Mono theme only** (monochrome, pill-shaped controls, `br:999px`) with a **light/dark mode toggle** instead of the prototype's 3-way Indigo/Mono/Night switcher — user's explicit choice.
- New font: Geist / Geist Mono (replaces Plus Jakarta Sans from v1 redesign).
- `frontend/src/theme/mono.js` (new): `LIGHT`/`DARK` token objects, status `ICON` SVG path data, style-builder helpers (`chipStyle`, `primaryStyle`, `navLinkStyle`, etc.).
- `frontend/src/composables/useTheme.js` (new): reactive light/dark mode, persisted to `localStorage` (`ses-mode`).
- `App.vue`: rewritten to match prototype nav exactly (logo, theme toggle sun/moon icon, Upload/Status links) plus a step breadcrumb ("1 Upload — 2 Preview — 3 Status") reflecting the active route.
- `UploadView.vue` / `PreviewView.vue` / `StatusView.vue`: rewritten as hand-styled markup (CSS grid "tables", inline SVG icons) bound to the theme tokens — **mostly bypasses Vuetify's own component styling now** (Vuetify kept installed/wired in `main.js` for potential future use, but no `v-card`/`v-btn`/`v-data-table` in the redesigned views).
- `frontend/src/plugins/vuetify.js` simplified back to defaults (old gradient/elevated-card theme removed); `frontend/src/assets/main.css` trimmed to just font + spin keyframe.
- `frontend/index.html`: Google Fonts link swapped to Geist/Geist Mono.
- Verified in browser: Upload and Status screens render correctly in both light and dark mode, dark mode persists across navigation, error handling (from the Task 11 fix) still works correctly in the new markup.
- Commit: `feat: implement Mono theme redesign from Claude Design prototype`.

### Real credentials wired and verified end-to-end ✅ (2026-10-15)
`backend/.env` (gitignored, not committed) now has real Supabase project credentials and a working Gmail SMTP app password. Verified with a real upload→confirm→send round trip against the actual Supabase project and Gmail: row inserted, scheduler picked it up within 60s, email sent successfully (`status: "sent"` with a real `sent_at` timestamp) — check mwasifhaider1@gmail.com inbox for "Test send" to confirm delivery. A couple of test rows exist in the real `email_jobs` Supabase table from this verification; harmless, but can be cleared from the Supabase dashboard if desired.
- First password the user gave wasn't an app password (Gmail rejected it, `"Connection unexpectedly closed"`). App Passwords were initially unavailable on the account until 2-Step Verification was enabled; after that, a real app password worked.
- Along the way, a stale backend process from an earlier test session kept holding port 8000 silently, so a server restart appeared to apply a new password but was actually still serving requests from the old process with the old password — second send attempt also "failed" for that reason until the stale process was found and killed. Lesson: after editing `.env`, verify the *new* process actually bound the port (watch for `[Errno 10048]`/`only one usage of each socket address` in the log) before trusting a test result.

### Deployment ✅ (2026-10-15)
Live infrastructure, deployed under the **hireflow AWS account** (`487916111463`, `ap-south-1`) — the original "fresh free-tier" account turned out to be a member account under a third-party AWS Organization ("Escape Velocity") with an SCP blocking EC2 entirely, so we switched to the existing hireflow/highlyte account per user's call.
- **EC2:** instance `i-0f23e0f3f05c518ba` (`sheet-email-sender-server`, t3.micro, Ubuntu 22.04), Elastic IP `3.109.50.148`, security group `sg-049dbc148c3890ee4` (SSH open to `0.0.0.0/0`, key-auth only), key pair `sheet-email-sender-key` (private key at `~/.ssh/sheet-email-sender-key.pem` / `C:\Users\whaid\.ssh\sheet-email-sender-key.pem`, **not in git**).
- **Backend runs as a Docker container** on the instance (`sheet-email-sender-backend`), image pulled from a private **ECR** repo (`487916111463.dkr.ecr.ap-south-1.amazonaws.com/sheet-email-sender-backend`). The instance has an IAM instance profile (`sheet-email-sender-ec2-profile` / role `sheet-email-sender-ec2-role`, ECR-read-only) so it pulls images without any stored AWS credentials.
- **Public URL:** `https://sheet-email.whapps.site` → Cloudflare Tunnel (`cloudflared` running as a systemd service on the instance) → `localhost:8000`. No inbound ports needed for HTTP/HTTPS at all (tunnel is outbound-only); Cloudflare terminates SSL.
- **CI/CD:** GitHub Actions, single workflow `.github/workflows/backend.yml` — `test` job (pytest) always runs on push/PR to `backend/**`; `deploy` job runs only on push to `master` after tests pass: builds the image, pushes to ECR, SSHes into the instance and redeploys (`docker pull` + stop/remove/run). Deploy uses a separate, narrowly-scoped IAM user `sheet-email-sender-ci` (ECR push only, this one repo) — its keys and the instance's SSH private key live in **GitHub repo secrets** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `EC2_HOST`, `EC2_SSH_KEY`), not in `.env`.
- **Repo:** `git@github-personal:WasifHaider/sheet-email-sender.git` (private).
- **Frontend:** to be deployed on Vercel (root dir `frontend`, build `npm run build`, output `dist`, env var `VITE_API_BASE_URL=https://sheet-email.whapps.site`) — user handles Vercel's GitHub import themselves; not yet confirmed done as of this note.
- Local `backend/Dockerfile` + `docker-compose.yml` exist for local Docker use too, though the deployed instance currently runs via plain `docker run` (CI's deploy script), not compose.

### Google OAuth login & per-user Gmail sending — IN PROGRESS (started 2026-10-15)
Client requirement: proper login/signup, and the sender email must be whichever Google account the user logged in with (not the shared SMTP account). Brainstormed → architectural spec → implementation plan, both committed:
- Spec: [docs/superpowers/specs/2026-10-15-google-oauth-login-design.md](docs/superpowers/specs/2026-10-15-google-oauth-login-design.md)
- Plan: [docs/superpowers/plans/2026-10-15-google-oauth-login.md](docs/superpowers/plans/2026-10-15-google-oauth-login.md)
- Key decisions: **Google-only** sign-in (no email/password), **custom OAuth** via `authlib` (not Supabase Auth — explicit user choice), sheet's `From` column **dropped** (sender is always the logged-in user), **fully multi-tenant** (every table/endpoint scoped to `user_id`), refresh tokens stored as plain DB columns (named tradeoff, not encrypted).
- Google Cloud project `sheet-email-sender` created, Gmail API enabled, OAuth consent screen configured (External, test users only — `gmail.send` is a sensitive scope, unverified app). OAuth Client ID/Secret issued, redirect URIs registered for both `http://localhost:8000/auth/google/callback` and `https://sheet-email.whapps.site/auth/google/callback`. Credentials + a generated `SESSION_SECRET` are in `backend/.env` (gitignored) and documented (without real values) in `.env.example`.
- **Task 1 — Session JWT helpers ✅ (2026-10-15):** `backend/app/auth.py` (`create_session_token`, `decode_session_token`, `get_current_user`), added `authlib`/`pyjwt`/`itsdangerous` to `requirements.txt`. Tests: `backend/tests/test_auth.py` — 5 passed.
- **Task 2 — Supabase schema migration ✅ (2026-10-15):** `backend/db/migration_002_users_and_ownership.sql` (`users` table + `email_jobs.user_id`), run by user in Supabase SQL editor.
- **Remaining tasks 3-9** (not started): Supabase `users` table migration, OAuth login/callback endpoints, `/auth/me`+`/auth/logout`, scoping every existing endpoint to `user_id` + dropping sheet's From column, Gmail-API mailer rewrite (replaces SMTP), scheduler per-user token lookup, frontend login screen + router guard + nav updates.
- **Once this feature ships, remember to also update `backend/.env` on the EC2 instance** (new OAuth/session vars) and the CI secrets stay the same — no new GitHub secrets needed for this feature since nothing new talks to AWS.

## Notes / decisions
- Working directly on `master`, no feature branches (solo, simple project).
- Deployed — see Deployment section above (was "undecided", now live).
- Git identity for this repo (personal project): `WasifHaider <mwasifhaider1@gmail.com>`, set locally via `git config user.name/user.email` in this repo — overrides the machine's global work identity.
- `backend/.env` has real working Supabase + Gmail SMTP credentials (not committed). The app is fully functional end-to-end as of 2026-10-15.
- `.claude/launch.json` config name is `frontend`, runs `npm --prefix frontend run dev` for browser-pane testing via `preview_start`.
