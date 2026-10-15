# Google OAuth Login & Per-User Gmail Sending — Design

## Goal
Replace the single shared SMTP sender account with a proper login system:
users sign up/log in with **"Sign in with Google"** only, and every email
they send goes out **as their own Gmail address** via the Gmail API. The
app becomes fully multi-tenant — each user only ever sees their own
uploaded batches and job status.

## Why this shape (decisions made during brainstorming)
- **Google-only auth** — login and "grant permission to send as me" are
  the same OAuth consent step. No password system to build or secure, no
  accounts that exist but can't send (which email/password + separate
  "connect Gmail" would allow).
- **Custom OAuth implementation** (not Supabase Auth) — explicit choice;
  we handle the Authorization Code flow ourselves using `authlib`
  (reduces risk of hand-rolled CSRF/state bugs vs. doing it raw).
- **Sheet's `From` column is dropped** — required columns become just
  `To, Subject, Email Content`. Sender is always the logged-in user.
- **Fully multi-tenant** — every table gets `user_id`, every endpoint
  filters by the authenticated user.
- **Refresh tokens stored as plain DB columns** (protected by Supabase's
  own access control + HTTPS in transit), not column-level-encrypted.
  Named explicitly as a tradeoff for staying simple, not an oversight.

## Google Cloud setup (already done)
- Project `sheet-email-sender`, Gmail API enabled.
- OAuth consent screen: External, scopes `openid`, `email`, `profile`,
  `https://www.googleapis.com/auth/gmail.send`. Test users added (scope
  is "sensitive" — only listed test users can log in until Google
  verification, which is out of scope for now).
- OAuth Client ID (Web application), redirect URIs registered for both
  `http://localhost:8000/auth/google/callback` (dev) and
  `https://sheet-email.whapps.site/auth/google/callback` (prod).
- Credentials live in `backend/.env` (gitignored): `GOOGLE_CLIENT_ID`,
  `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, `SESSION_SECRET`.

## Data model changes (Supabase)

New `users` table:
| column | type | notes |
|---|---|---|
| id | uuid (pk) | |
| google_sub | text, unique | Google's stable user id (`sub` claim) |
| email | text | |
| name | text, nullable | |
| refresh_token | text | Google OAuth refresh token, used to mint access tokens for sending |
| created_at | timestamptz | |

`email_jobs` gets one new column: `user_id uuid not null` (FK to
`users.id`). The `from_email` column stays in the schema (harmless) but
is no longer read from the sheet — it's set to the logged-in user's
email at upload time instead.

Existing rows in `email_jobs` (test data) have no `user_id`; since the
table was already cleared during earlier testing, no migration of old
data is needed — this is a clean cutover.

## Backend: auth endpoints (new `app/routers/auth.py`)

- `GET /auth/google/login` — builds the Google consent URL
  (`access_type=offline&prompt=consent` so a refresh token is always
  issued) with a CSRF `state` value, redirects the browser there.
- `GET /auth/google/callback` — receives `code` + `state`, verifies
  state, exchanges the code for tokens via `authlib`, decodes the
  `id_token` to get `sub`/`email`/`name`, upserts the `users` row
  (storing `refresh_token` — only present on first consent, so an
  upsert must not overwrite an existing refresh token with `null` on
  subsequent logins), issues our own signed session JWT (7-day expiry,
  claims: `user_id`, `email`), sets it as an httpOnly, secure,
  `SameSite=Lax` cookie, redirects to the frontend's `/upload`.
- `GET /auth/me` — reads the session cookie, returns `{id, email, name}`
  or `401` if missing/invalid/expired.
- `POST /auth/logout` — clears the session cookie.

New dependency `get_current_user(request) -> dict` (in `app/auth.py`):
reads the session cookie, verifies the JWT (via `PyJWT`, signed with
`SESSION_SECRET`), returns the user claims or raises `401`. Every
existing endpoint (`/upload`, `/batches/*`, `/jobs`) adds
`user=Depends(get_current_user)` and filters/writes using `user_id`.

## Backend: CORS change required

Cookie-based sessions require `allow_credentials=True` in
`CORSMiddleware`, which Starlette refuses to combine with
`allow_origins=["*"]`. `main.py`'s CORS config changes to an explicit
origin list (local dev + the Vercel frontend URL) via a new
`FRONTEND_URL` env var, instead of `*`.

## Backend: sending (rewritten `app/mailer.py`)

`smtplib` is removed entirely. New flow per job, inside
`scheduler.process_job`:
1. Look up the job's owning user (`users` table, by `job["user_id"]`)
   to get their `refresh_token`.
2. Exchange the refresh token for a fresh access token via Google's
   token endpoint (`POST https://oauth2.googleapis.com/token`,
   `grant_type=refresh_token`) — done on every send rather than caching
   access tokens, since the scheduler only runs every 60s and this
   keeps token-expiry bookkeeping out of scope.
3. Build the MIME message exactly as before (`build_message`, unchanged
   — `From` is now always the owning user's email).
4. Base64url-encode the raw MIME bytes and `POST` to
   `https://gmail.googleapis.com/gmail/v1/users/me/messages/send` with
   `Authorization: Bearer <access_token>`.
5. Same success/failure handling as today (`status: sent`/`failed`,
   `error_message` on exception).

No new SDK dependency — plain `httpx` calls (already a dependency) to
Google's REST endpoints, consistent with the existing codebase style.

## Frontend changes

- New `LoginView.vue`: centered card, "Sign in with Google" button
  (full-page redirect to `/auth/google/login` on the backend — not a JS
  popup, since offline access requires the server-side flow).
- Router navigation guard: any route other than `/login` checks
  `GET /auth/me` first; on `401`, redirect to `/login`.
- `api/client.js`: axios instance gets `withCredentials: true` so the
  session cookie is sent with every request.
- `App.vue` nav bar: shows the logged-in user's name/email and a
  "Log out" button (calls `POST /auth/logout`, redirects to `/login`).
- `UploadView.vue`: drop the implicit assumption that sender is
  sheet-provided — no UI change needed here since `From` was never a
  user-facing form field, only a sheet column; just the required-columns
  hint text updates to drop `From`.

## Error handling
- OAuth callback errors (user denies consent, invalid state) redirect
  to `/login?error=oauth_failed` with a visible error message.
- Expired/invalid session JWT → `401` from any protected endpoint →
  frontend's navigation guard redirects to `/login`.
- Gmail API send failure (e.g. revoked consent, expired refresh token)
  → job marked `failed` with the Gmail API's error message, same as
  today's SMTP failure handling — no new UI needed, existing Status
  page already surfaces `error_message`.

## Testing
- `authlib`'s OAuth client and Google's token endpoints are mocked in
  tests (`monkeypatch`), same pattern as the existing `send_message`
  mocking — no real OAuth flow or real Gmail API calls in CI.
- `FakeSupabase` test double extended with a `users` table (already
  generic enough to support this with zero changes).
- New tests: `get_current_user` with a valid/invalid/missing cookie,
  OAuth callback upsert logic (first login vs. returning user — refresh
  token not overwritten with null), `process_job`'s token-refresh +
  Gmail API send path (mocked).

## Explicitly out of scope (this spec)
- Email/password signup (decided against).
- Supporting non-Gmail senders (Outlook, etc.).
- Google app verification (stays in testing mode with a fixed test-user
  allowlist).
- Refresh-token encryption at rest (named tradeoff, not forgotten).
- Multi-device/concurrent session management beyond a single JWT cookie.
