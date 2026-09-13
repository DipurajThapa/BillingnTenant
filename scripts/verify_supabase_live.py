"""Authenticated Supabase Data API verification; emits no credential material."""

import os
from contextlib import suppress
from urllib.parse import urlsplit

import httpx


def required(name: str) -> str:
    value = os.environ.get(name, "")
    if not value:
        raise RuntimeError(f"LIVE_CONFIG_MISSING:{name}")
    return value


def main() -> None:
    base_url = required("SUPABASE_TEST_URL").rstrip("/")
    key = required("SUPABASE_TEST_PUBLISHABLE_KEY")
    parsed = urlsplit(base_url)
    if parsed.scheme != "https" or not (parsed.hostname or "").endswith(".supabase.co"):
        raise RuntimeError("LIVE_URL_INVALID")

    headers = {"apikey": key, "content-type": "application/json"}
    timeout = httpx.Timeout(15.0)
    with httpx.Client(
        verify=True, follow_redirects=False, trust_env=False, timeout=timeout
    ) as client:
        settings_response = client.get(f"{base_url}/auth/v1/settings", headers=headers)
        if settings_response.status_code != 200:
            raise RuntimeError(f"LIVE_KEY_REJECTED:{settings_response.status_code}")

        actor_secrets = {
            "A": ("SUPABASE_TEST_ACTOR_A_EMAIL", "SUPABASE_TEST_ACTOR_A_PASSWORD"),
            "B": ("SUPABASE_TEST_ACTOR_B_EMAIL", "SUPABASE_TEST_ACTOR_B_PASSWORD"),
        }

        def login(alias: str) -> str:
            email_name, password_name = actor_secrets[alias]
            response = client.post(
                f"{base_url}/auth/v1/token?grant_type=password",
                headers=headers,
                json={
                    "email": required(email_name),
                    "password": required(password_name),
                },
            )
            if response.status_code != 200:
                error_code = "auth_rejected"
                with suppress(Exception):
                    candidate = response.json().get("error_code")
                    if isinstance(candidate, str) and candidate.replace("_", "").isalnum():
                        error_code = candidate
                raise RuntimeError(f"LIVE_AUTH_FAILED:{alias}:{response.status_code}:{error_code}")
            token = response.json().get("access_token")
            if not isinstance(token, str) or not token:
                raise RuntimeError(f"LIVE_AUTH_RESPONSE_INVALID:{alias}")
            return token

        def rpc(token: str, function: str, body: dict[str, object]) -> dict[str, object]:
            response = client.post(
                f"{base_url}/rest/v1/rpc/{function}",
                headers={**headers, "authorization": f"Bearer {token}"},
                json=body,
            )
            if response.status_code != 200:
                raise RuntimeError(f"LIVE_RPC_FAILED:{function}:{response.status_code}")
            result = response.json()
            if not isinstance(result, dict):
                raise RuntimeError(f"LIVE_RPC_RESPONSE_INVALID:{function}")
            return result

        token_a, token_b = login("A"), login("B")
        resource_a = "41000000-0000-0000-0000-000000000001"
        resource_b = "42000000-0000-0000-0000-000000000002"
        tenant_a = "31000000-0000-0000-0000-000000000001"

        assert (
            rpc(token_a, "preflight_read_resource", {"p_resource_id": resource_a})["outcome"]
            == "allowed"
        )
        assert (
            rpc(token_a, "preflight_read_resource", {"p_resource_id": resource_b})["outcome"]
            == "not_found"
        )
        assert (
            rpc(token_b, "preflight_read_resource", {"p_resource_id": resource_b})["outcome"]
            == "allowed"
        )
        assert (
            rpc(token_b, "preflight_read_resource", {"p_resource_id": resource_a})["outcome"]
            == "not_found"
        )

        created_id: str | None = None
        created = rpc(
            token_a,
            "preflight_create_resource",
            {"p_organization_id": tenant_a, "p_name": "Live verification", "p_payload": {}},
        )
        if created.get("outcome") != "success":
            raise RuntimeError("LIVE_CREATE_FAILED")
        state = created.get("state")
        if not isinstance(state, dict) or not isinstance(state.get("resourceId"), str):
            raise RuntimeError("LIVE_CREATE_RESPONSE_INVALID")
        created_id = state["resourceId"]
        try:
            assert (
                rpc(token_b, "preflight_read_resource", {"p_resource_id": created_id})["outcome"]
                == "not_found"
            )
        finally:
            if created_id:
                with suppress(Exception):
                    rpc(token_a, "preflight_delete_resource", {"p_resource_id": created_id})

    print("SUPABASE_LIVE_VERIFICATION_PASS")


if __name__ == "__main__":
    main()
