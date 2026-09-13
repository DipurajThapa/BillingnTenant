-- SUP-002: narrow RPC surface consumed by SupabaseIdentityTenantAdapter.

create or replace function public.preflight_read_resource(p_resource_id uuid)
returns jsonb
language plpgsql
stable
security invoker
set search_path = ''
as $$
declare
    row_data public.tenant_resources%rowtype;
begin
    select * into row_data
    from public.tenant_resources
    where id = p_resource_id;
    if not found then
        return jsonb_build_object(
            'outcome', 'not_found', 'state', '{}'::jsonb, 'changed', false
        );
    end if;
    return jsonb_build_object(
        'outcome', 'allowed',
        'state', jsonb_build_object(
            'resourceId', row_data.id,
            'tenantId', row_data.organization_id,
            'ownerActorId', row_data.owner_user_id,
            'name', row_data.name,
            'payload', row_data.payload
        ),
        'changed', false
    );
end;
$$;

create or replace function public.preflight_create_resource(
    p_organization_id uuid,
    p_name text,
    p_payload jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    created_id uuid;
begin
    insert into public.tenant_resources (organization_id, owner_user_id, name, payload)
    values (p_organization_id, (select auth.uid()), p_name, p_payload)
    returning id into created_id;
    return jsonb_build_object(
        'outcome', 'success',
        'state', jsonb_build_object('resourceId', created_id, 'tenantId', p_organization_id),
        'changed', true
    );
exception
    when check_violation or not_null_violation or invalid_text_representation then
        return jsonb_build_object(
            'outcome', 'invalid', 'state', '{}'::jsonb, 'changed', false,
            'errorCode', 'SUPABASE_INPUT_INVALID'
        );
end;
$$;

create or replace function public.preflight_update_resource(
    p_resource_id uuid,
    p_name text,
    p_payload jsonb
)
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    affected integer;
begin
    update public.tenant_resources
    set name = p_name, payload = p_payload, updated_at = now()
    where id = p_resource_id;
    get diagnostics affected = row_count;
    if affected = 0 then
        return jsonb_build_object(
            'outcome', 'not_found', 'state', '{}'::jsonb, 'changed', false
        );
    end if;
    return jsonb_build_object(
        'outcome', 'success',
        'state', jsonb_build_object('resourceId', p_resource_id),
        'changed', true
    );
exception
    when check_violation or not_null_violation then
        return jsonb_build_object(
            'outcome', 'invalid', 'state', '{}'::jsonb, 'changed', false,
            'errorCode', 'SUPABASE_INPUT_INVALID'
        );
end;
$$;

create or replace function public.preflight_delete_resource(p_resource_id uuid)
returns jsonb
language plpgsql
volatile
security invoker
set search_path = ''
as $$
declare
    affected integer;
begin
    delete from public.tenant_resources where id = p_resource_id;
    get diagnostics affected = row_count;
    if affected = 0 then
        return jsonb_build_object(
            'outcome', 'not_found', 'state', '{}'::jsonb, 'changed', false
        );
    end if;
    return jsonb_build_object(
        'outcome', 'success',
        'state', jsonb_build_object('resourceId', p_resource_id),
        'changed', true
    );
end;
$$;

revoke all on function public.preflight_read_resource(uuid) from public, anon;
revoke all on function public.preflight_create_resource(uuid, text, jsonb) from public, anon;
revoke all on function public.preflight_update_resource(uuid, text, jsonb) from public, anon;
revoke all on function public.preflight_delete_resource(uuid) from public, anon;

grant execute on function public.preflight_read_resource(uuid) to authenticated;
grant execute on function public.preflight_create_resource(uuid, text, jsonb) to authenticated;
grant execute on function public.preflight_update_resource(uuid, text, jsonb) to authenticated;
grant execute on function public.preflight_delete_resource(uuid) to authenticated;
