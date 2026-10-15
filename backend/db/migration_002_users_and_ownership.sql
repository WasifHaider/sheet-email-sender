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
