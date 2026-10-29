-- ---------------------------------------------------------------------------
-- Schema for the Supabase project backing the Travel Itinerary Planner.
--
-- Apply this in Supabase Studio -> SQL Editor (or `supabase db push`).
-- ---------------------------------------------------------------------------

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- trips: one row per saved itinerary.
-- ---------------------------------------------------------------------------
create table if not exists public.trips (
    id                uuid primary key default gen_random_uuid(),
    user_id           uuid references auth.users (id) on delete cascade,
    title             text        not null default '',
    destination       text        not null,
    start_date        date        not null,
    end_date          date        not null,
    travelers         integer     not null default 1,
    budget            numeric(12, 2) not null default 0,
    currency          text        not null default 'USD',
    total_estimated_cost numeric(12, 2) not null default 0,
    status            text        not null default 'upcoming',
    interests         text[]      not null default '{}',
    travel_style      text,
    accommodation     text,
    transportation    text,
    notes             text,
    preferences       jsonb       not null default '{}'::jsonb,
    itinerary         jsonb       not null default '{}'::jsonb,
    created_at        timestamptz not null default now(),
    updated_at        timestamptz not null default now()
);

create index if not exists trips_user_id_created_at_idx
    on public.trips (user_id, created_at desc);

-- Keep updated_at fresh.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trips_set_updated_at on public.trips;
create trigger trips_set_updated_at
    before update on public.trips
    for each row execute function public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Row level security: users may only ever touch their own trips.
-- The backend talks to Supabase with the service-role key, but the
-- policies below also protect direct client access.
-- ---------------------------------------------------------------------------
alter table public.trips enable row level security;

drop policy if exists "Users can read own trips" on public.trips;
create policy "Users can read own trips"
    on public.trips for select
    using (auth.uid() = user_id);

drop policy if exists "Users can insert own trips" on public.trips;
create policy "Users can insert own trips"
    on public.trips for insert
    with check (auth.uid() = user_id);

drop policy if exists "Users can update own trips" on public.trips;
create policy "Users can update own trips"
    on public.trips for update
    using (auth.uid() = user_id)
    with check (auth.uid() = user_id);

drop policy if exists "Users can delete own trips" on public.trips;
create policy "Users can delete own trips"
    on public.trips for delete
    using (auth.uid() = user_id);
