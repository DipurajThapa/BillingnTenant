import httpx
import pytest
from pydantic import ValidationError

from preflight.external_http import HttpSafetyError, RemoteHttpConfig, RemoteHttpTransport
from preflight.models import AuthContext, ProbeRequest


def config(**updates) -> RemoteHttpConfig:
    values = {
        "baseUrl": "https://api.example.com/",
        "allowedHosts": ["api.example.com"],
        "operationPaths": {"get_item": "/v1/item", "create_item": "/v1/item"},
        "methods": ["GET", "POST"],
    }
    values.update(updates)
    return RemoteHttpConfig.model_validate(values)


def transport(handler, **updates) -> RemoteHttpTransport:
    return RemoteHttpTransport(
        config(**updates),
        lambda _: "secret",
        resolver=lambda _h, _p: {"93.184.216.34"},
        transport=httpx.MockTransport(handler),
    )


def test_rejects_non_https_credentials_fragments_private_and_unlisted_hosts() -> None:
    for url, code in [
        ("http://api.example.com", "HTTP_URL_BLOCKED"),
        ("https://x:y@api.example.com", "HTTP_URL_BLOCKED"),
        ("https://api.example.com/#x", "HTTP_URL_BLOCKED"),
        ("https://other.example.com", "HTTP_HOST_NOT_ALLOWED"),
    ]:
        with pytest.raises(HttpSafetyError, match=code):
            RemoteHttpTransport(
                config(baseUrl=url), lambda _: None, resolver=lambda _h, _p: {"93.184.216.34"}
            )
    with pytest.raises(HttpSafetyError, match="HTTP_ADDRESS_BLOCKED"):
        RemoteHttpTransport(config(), lambda _: None, resolver=lambda _h, _p: {"127.0.0.1"})


def test_rejects_unsafe_paths_and_unknown_operations() -> None:
    with pytest.raises(ValidationError):
        config(operationPaths={"x": "//metadata"})
    client = transport(lambda request: httpx.Response(200, json={}))
    with pytest.raises(HttpSafetyError, match="HTTP_OPERATION_BLOCKED"):
        client.execute(AuthContext(mode="public"), ProbeRequest(operation="unknown"))


def test_success_uses_allowlisted_mapping_and_secret_is_not_returned() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/item"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200, json={"outcome": "success", "changed": False, "state": {"id": "safe"}}
        )

    result = transport(handler).execute(
        AuthContext(mode="actor_session", actorId="a1", credentialHandle="handle"),
        ProbeRequest(operation="get_item"),
    )
    assert result.state == {"id": "safe"}
    assert "secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    "status,code", [(302, "HTTP_REDIRECT_BLOCKED"), (503, "HTTP_UPSTREAM_UNAVAILABLE")]
)
def test_redirects_and_upstream_failures_are_typed(status: int, code: str) -> None:
    client = transport(
        lambda request: httpx.Response(
            status, headers={"location": "https://api.example.com/other"}
        )
    )
    with pytest.raises(HttpSafetyError, match=code):
        client.execute(AuthContext(mode="public"), ProbeRequest(operation="get_item"))


def test_enforces_content_type_schema_and_response_limit() -> None:
    cases = [
        (httpx.Response(200, text="not json"), "HTTP_CONTENT_TYPE_INVALID"),
        (
            httpx.Response(200, headers={"content-type": "application/json"}, content=b"[]"),
            "HTTP_RESPONSE_INVALID",
        ),
        (
            httpx.Response(
                200, headers={"content-type": "application/json"}, content=b"{" + b"x" * 2048
            ),
            "HTTP_RESPONSE_TOO_LARGE",
        ),
    ]
    for response, code in cases:
        client = transport(lambda request, response=response: response, maxResponseBytes=1024)
        with pytest.raises(HttpSafetyError, match=code):
            client.execute(AuthContext(mode="public"), ProbeRequest(operation="get_item"))


def test_environment_proxy_is_disabled_and_credentials_fail_closed() -> None:
    client = RemoteHttpTransport(
        config(),
        lambda _: None,
        resolver=lambda _h, _p: {"93.184.216.34"},
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
    )
    with pytest.raises(HttpSafetyError, match="HTTP_CREDENTIAL_UNAVAILABLE"):
        client.execute(
            AuthContext(mode="signed_event", credentialHandle="missing"),
            ProbeRequest(operation="create_item"),
        )


@pytest.mark.parametrize(
    "headers",
    [
        {"x-unapproved": "value"},
        {"apikey": ""},
        {"apikey": "value\r\ninjected: true"},
    ],
)
def test_static_headers_are_narrow_and_injection_safe(headers: dict[str, str]) -> None:
    client = RemoteHttpTransport(
        config(),
        lambda _: None,
        static_header_provider=lambda: headers,
        resolver=lambda _h, _p: {"93.184.216.34"},
        transport=httpx.MockTransport(lambda request: pytest.fail("network called")),
    )
    with pytest.raises(HttpSafetyError, match="HTTP_HEADER_BLOCKED"):
        client.execute(AuthContext(mode="public"), ProbeRequest(operation="get_item"))
