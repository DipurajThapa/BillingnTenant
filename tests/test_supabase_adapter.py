from pathlib import Path

import httpx
import pytest

from preflight.external_http import HttpSafetyError
from preflight.models import ActorRef, AuthContext, MembershipRef, ProbeRequest
from preflight.supabase_adapter import SupabaseAdapterConfig, SupabaseIdentityTenantAdapter


def config(**overrides: object) -> SupabaseAdapterConfig:
    data: dict[str, object] = {
        "projectUrl": "https://example.supabase.co",
        "publishableKeyHandle": "supabase:publishable",
        "operationFunctions": {"read_resource": "preflight_read_resource"},
    }
    data.update(overrides)
    return SupabaseAdapterConfig.model_validate(data)


def actor() -> ActorRef:
    return ActorRef(
        id="actor-a",
        alias="A",
        memberships=[MembershipRef(tenantId="tenant-a", role="member")],
        activeTenantId="tenant-a",
    )


def test_adapter_uses_fixed_rpc_and_opaque_credentials() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(url=str(request.url), auth=request.headers.get("authorization"))
        assert request.headers["apikey"] == "publishable-value"
        return httpx.Response(
            200,
            headers={"content-type": "application/json"},
            json={"outcome": "allowed", "state": {"tenant": "tenant-a"}, "changed": False},
        )

    secrets = {
        "supabase:publishable": "publishable-value",
        "supabase:actor:actor-a": "actor-jwt-value",
    }
    adapter = SupabaseIdentityTenantAdapter(
        config(),
        secrets.get,
        resolver=lambda _host, _port: {"8.8.8.8"},
        transport=httpx.MockTransport(handler),
    )
    auth = adapter.auth_context(actor())
    result = adapter.execute(auth, ProbeRequest(operation="read_resource"))

    assert result.outcome == "allowed"
    assert seen == {
        "url": "https://example.supabase.co/rest/v1/rpc/preflight_read_resource",
        "auth": "Bearer actor-jwt-value",
    }
    assert "actor-jwt-value" not in auth.model_dump_json()


def test_adapter_denies_non_actor_auth_without_network() -> None:
    adapter = SupabaseIdentityTenantAdapter(
        config(),
        lambda _handle: None,
        resolver=lambda _host, _port: {"8.8.8.8"},
        transport=httpx.MockTransport(lambda _request: pytest.fail("network called")),
    )
    result = adapter.execute(AuthContext(mode="public"), ProbeRequest(operation="read_resource"))
    assert result.outcome == "denied"


def test_adapter_fails_closed_for_missing_key_or_unknown_operation() -> None:
    adapter = SupabaseIdentityTenantAdapter(
        config(),
        lambda _handle: None,
        resolver=lambda _host, _port: {"8.8.8.8"},
        transport=httpx.MockTransport(lambda _request: pytest.fail("network called")),
    )
    with pytest.raises(HttpSafetyError, match="HTTP_OPERATION_BLOCKED"):
        adapter.execute(adapter.auth_context(actor()), ProbeRequest(operation="delete_everything"))
    with pytest.raises(HttpSafetyError, match="HTTP_HEADER_BLOCKED"):
        adapter.execute(adapter.auth_context(actor()), ProbeRequest(operation="read_resource"))


def test_adapter_rejects_non_supabase_hosts_and_unsafe_function_names() -> None:
    with pytest.raises(ValueError, match="Supabase HTTPS"):
        config(projectUrl="https://example.com")
    with pytest.raises(ValueError, match="preflight_ prefix"):
        config(operationFunctions={"read": "arbitrary_function"})


def test_migration_has_rls_grants_and_tenant_guards() -> None:
    sql = Path("supabase/migrations/202609130001_identity_tenant.sql").read_text()
    for table in ("organizations", "memberships", "tenant_resources"):
        assert f"alter table public.{table} enable row level security" in sql
        assert f"alter table public.{table} force row level security" in sql
        assert f"revoke all on public.{table} from anon, authenticated" in sql
    assert "security definer" in sql
    assert "set search_path = ''" in sql
    assert "owner_user_id = (select auth.uid())" in sql
    assert "private.is_active_member(organization_id)" in sql


def test_rpc_migration_exposes_only_fixed_authenticated_functions() -> None:
    sql = Path("supabase/migrations/202609130002_preflight_rpc.sql").read_text()
    functions = (
        "preflight_read_resource(uuid)",
        "preflight_create_resource(uuid, text, jsonb)",
        "preflight_update_resource(uuid, text, jsonb)",
        "preflight_delete_resource(uuid)",
    )
    for signature in functions:
        assert f"revoke all on function public.{signature} from public, anon" in sql
        assert f"grant execute on function public.{signature} to authenticated" in sql
    assert sql.count("security invoker") == 4
    assert sql.count("set search_path = ''") == 4


def test_live_rls_script_is_transactional_and_covers_negative_paths() -> None:
    sql = Path("supabase/tests/rls_identity_tenant.sql").read_text()
    assert sql.lstrip().startswith("-- Transactional live test")
    assert "begin;" in sql and sql.rstrip().endswith("rollback;")
    for test_id in range(1, 8):
        assert f"SUP-LIVE-{test_id:03d}" in sql
    assert "cross-tenant read was visible" in sql
    assert "revoked member retained access" in sql
    assert "has_function_privilege('anon'" in sql
