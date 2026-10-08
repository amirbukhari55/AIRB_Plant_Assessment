-- Run in a dedicated Supabase project. The service role key stays in server secrets.
create table if not exists public.plant_assessment (
 id text primary key,
 revision bigint not null default 0,
 payload jsonb
);
alter table public.plant_assessment enable row level security;
revoke all on public.plant_assessment from anon, authenticated;
grant select, insert, update on public.plant_assessment to service_role;
insert into public.plant_assessment(id) values('airb-stage1') on conflict(id) do nothing;
