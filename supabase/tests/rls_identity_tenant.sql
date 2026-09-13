-- Transactional live test. Run only as the project database owner in the dedicated test project.
-- Fixed UUIDs are synthetic; session_replication_role bypasses auth.users FKs only inside rollback.

begin;

insert into public.organizations (id, name) values
    ('10000000-0000-0000-0000-000000000001', 'Preflight Tenant A'),
    ('20000000-0000-0000-0000-000000000002', 'Preflight Tenant B');

set local session_replication_role = replica;
insert into public.memberships (organization_id, user_id, role, active) values
    ('10000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'member', true),
    ('20000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'member', true);
insert into public.tenant_resources (id, organization_id, owner_user_id, name) values
    ('11000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'A resource'),
    ('22000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'B resource');
set local session_replication_role = origin;

set local role authenticated;
select set_config('request.jwt.claim.sub', 'a0000000-0000-0000-0000-000000000001', true);

do $$
begin
    if (public.preflight_read_resource('11000000-0000-0000-0000-000000000001')->>'outcome') <> 'allowed' then
        raise exception 'SUP-LIVE-001 own-tenant read failed';
    end if;
    if (public.preflight_read_resource('22000000-0000-0000-0000-000000000002')->>'outcome') <> 'not_found' then
        raise exception 'SUP-LIVE-002 cross-tenant read was visible';
    end if;
    if (public.preflight_update_resource(
        '22000000-0000-0000-0000-000000000002', 'intrusion', '{}'::jsonb
    )->>'outcome') <> 'not_found' then
        raise exception 'SUP-LIVE-003 cross-tenant update was allowed';
    end if;
    if (public.preflight_delete_resource('22000000-0000-0000-0000-000000000002')->>'outcome') <> 'not_found' then
        raise exception 'SUP-LIVE-004 cross-tenant delete was allowed';
    end if;
    if (select count(*) from public.organizations) <> 1 then
        raise exception 'SUP-LIVE-005 organization visibility escaped tenant';
    end if;
end;
$$;

reset role;
delete from public.memberships
where organization_id = '10000000-0000-0000-0000-000000000001'
  and user_id = 'a0000000-0000-0000-0000-000000000001';
set local role authenticated;
select set_config('request.jwt.claim.sub', 'a0000000-0000-0000-0000-000000000001', true);

do $$
begin
    if (public.preflight_read_resource('11000000-0000-0000-0000-000000000001')->>'outcome') <> 'not_found' then
        raise exception 'SUP-LIVE-006 revoked member retained access';
    end if;
end;
$$;

reset role;
do $$
begin
    if has_function_privilege('anon', 'public.preflight_read_resource(uuid)', 'EXECUTE') then
        raise exception 'SUP-LIVE-007 anon can execute tenant RPC';
    end if;
end;
$$;

rollback;
