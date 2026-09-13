-- SUP-001: shared-schema tenant identity boundary for the Supabase adapter.
-- Runtime clients use only authenticated JWTs; service-role access is not used by probes.

create schema if not exists private;

create table if not exists public.organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null check (char_length(name) between 1 and 100),
    created_at timestamptz not null default now()
);

create table if not exists public.memberships (
    organization_id uuid not null references public.organizations(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('owner', 'admin', 'member')),
    active boolean not null default true,
    created_at timestamptz not null default now(),
    primary key (organization_id, user_id)
);

create index if not exists memberships_user_active_idx
    on public.memberships (user_id, organization_id) where active;

create table if not exists public.tenant_resources (
    id uuid primary key default gen_random_uuid(),
    organization_id uuid not null references public.organizations(id) on delete cascade,
    owner_user_id uuid not null references auth.users(id) on delete restrict,
    name text not null check (char_length(name) between 1 and 100),
    payload jsonb not null default '{}'::jsonb check (jsonb_typeof(payload) = 'object'),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists tenant_resources_org_idx
    on public.tenant_resources (organization_id, id);

create or replace function private.is_active_member(target_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.memberships m
        where m.organization_id = target_organization_id
          and m.user_id = (select auth.uid())
          and m.active
    );
$$;

create or replace function private.has_org_role(
    target_organization_id uuid,
    allowed_roles text[]
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
    select exists (
        select 1
        from public.memberships m
        where m.organization_id = target_organization_id
          and m.user_id = (select auth.uid())
          and m.active
          and m.role = any(allowed_roles)
    );
$$;

revoke all on schema private from public, anon;
grant usage on schema private to authenticated;
revoke all on function private.is_active_member(uuid) from public, anon;
revoke all on function private.has_org_role(uuid, text[]) from public, anon;
grant execute on function private.is_active_member(uuid) to authenticated;
grant execute on function private.has_org_role(uuid, text[]) to authenticated;

alter table public.organizations enable row level security;
alter table public.organizations force row level security;
alter table public.memberships enable row level security;
alter table public.memberships force row level security;
alter table public.tenant_resources enable row level security;
alter table public.tenant_resources force row level security;

revoke all on public.organizations from anon, authenticated;
revoke all on public.memberships from anon, authenticated;
revoke all on public.tenant_resources from anon, authenticated;

grant select, update on public.organizations to authenticated;
grant select, insert, update, delete on public.memberships to authenticated;
grant select, insert, update, delete on public.tenant_resources to authenticated;

drop policy if exists organizations_select_member on public.organizations;
create policy organizations_select_member on public.organizations
for select to authenticated
using ((select private.is_active_member(id)));

drop policy if exists organizations_update_admin on public.organizations;
create policy organizations_update_admin on public.organizations
for update to authenticated
using ((select private.has_org_role(id, array['owner', 'admin'])))
with check ((select private.has_org_role(id, array['owner', 'admin'])));

drop policy if exists memberships_select_member on public.memberships;
create policy memberships_select_member on public.memberships
for select to authenticated
using ((select private.is_active_member(organization_id)));

drop policy if exists memberships_insert_owner on public.memberships;
create policy memberships_insert_owner on public.memberships
for insert to authenticated
with check ((select private.has_org_role(organization_id, array['owner'])));

drop policy if exists memberships_update_owner on public.memberships;
create policy memberships_update_owner on public.memberships
for update to authenticated
using ((select private.has_org_role(organization_id, array['owner'])))
with check ((select private.has_org_role(organization_id, array['owner'])));

drop policy if exists memberships_delete_owner on public.memberships;
create policy memberships_delete_owner on public.memberships
for delete to authenticated
using (
    (select private.has_org_role(organization_id, array['owner']))
    and not (user_id = (select auth.uid()) and role = 'owner')
);

drop policy if exists tenant_resources_select_member on public.tenant_resources;
create policy tenant_resources_select_member on public.tenant_resources
for select to authenticated
using ((select private.is_active_member(organization_id)));

drop policy if exists tenant_resources_insert_member on public.tenant_resources;
create policy tenant_resources_insert_member on public.tenant_resources
for insert to authenticated
with check (
    owner_user_id = (select auth.uid())
    and (select private.is_active_member(organization_id))
);

drop policy if exists tenant_resources_update_owner_admin on public.tenant_resources;
create policy tenant_resources_update_owner_admin on public.tenant_resources
for update to authenticated
using (
    owner_user_id = (select auth.uid())
    or (select private.has_org_role(organization_id, array['owner', 'admin']))
)
with check (
    (owner_user_id = (select auth.uid())
     or (select private.has_org_role(organization_id, array['owner', 'admin'])))
    and (select private.is_active_member(organization_id))
);

drop policy if exists tenant_resources_delete_owner_admin on public.tenant_resources;
create policy tenant_resources_delete_owner_admin on public.tenant_resources
for delete to authenticated
using (
    owner_user_id = (select auth.uid())
    or (select private.has_org_role(organization_id, array['owner', 'admin']))
);
