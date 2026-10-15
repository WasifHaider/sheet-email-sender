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
