-- 1. Create waitlist table
create table if not exists public.waitlist (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz default now()
);

-- 2. Enable Row Level Security (RLS)
alter table public.waitlist enable row level security;

-- 3. Ensure NO public policies exist so anonymous client keys cannot read or write directly.
-- Inserts and reads will only happen securely via backend API route handlers using the SUPABASE_SERVICE_ROLE_KEY.
