"""Allowlisted remote HTTP transport with fail-closed SSRF controls."""

import ipaddress
import json
import socket
from collections.abc import Callable
from typing import Literal
from urllib.parse import urljoin, urlsplit

import httpx
from pydantic import Field, HttpUrl, field_validator

from preflight.models import AuthContext, Observation, ProbeRequest, StrictModel


class HttpSafetyError(RuntimeError):
    """Typed transport refusal with a safe diagnostic code."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class RemoteHttpConfig(StrictModel):
    base_url: HttpUrl
    allowed_hosts: frozenset[str] = Field(min_length=1, max_length=20)
    operation_paths: dict[str, str] = Field(min_length=1, max_length=100)
    timeout_seconds: float = Field(default=10.0, ge=0.25, le=30.0)
    max_response_bytes: int = Field(default=1_048_576, ge=1_024, le=4_194_304)
    methods: frozenset[Literal["GET", "POST"]] = frozenset({"POST"})

    @field_validator("operation_paths")
    @classmethod
    def paths_are_relative(cls, value: dict[str, str]) -> dict[str, str]:
        if any(
            not path.startswith("/") or path.startswith("//") or "?" in path
            for path in value.values()
        ):
            raise ValueError("operation paths must be absolute paths without query strings")
        return value


def default_resolver(host: str, port: int) -> set[str]:
    try:
        return {item[4][0] for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror:
        raise HttpSafetyError("HTTP_DNS_FAILED") from None


def validate_public_addresses(addresses: set[str]) -> None:
    if not addresses:
        raise HttpSafetyError("HTTP_DNS_FAILED")
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise HttpSafetyError("HTTP_ADDRESS_BLOCKED")


class RemoteHttpTransport:
    name = "safe-httpx"
    version = "1.0"
    kind = "external"

    def __init__(
        self,
        config: RemoteHttpConfig,
        credential_provider: Callable[[str], str | None],
        resolver: Callable[[str, int], set[str]] = default_resolver,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self.credential_provider = credential_provider
        self.resolver = resolver
        self.transport = transport
        self._validate_destination(str(config.base_url))

    def _validate_destination(self, url: str) -> None:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment:
            raise HttpSafetyError("HTTP_URL_BLOCKED")
        if host not in {item.lower().rstrip(".") for item in self.config.allowed_hosts}:
            raise HttpSafetyError("HTTP_HOST_NOT_ALLOWED")
        port = parsed.port or 443
        if port != 443:
            raise HttpSafetyError("HTTP_PORT_BLOCKED")
        try:
            literal = ipaddress.ip_address(host.strip("[]"))
        except ValueError:
            validate_public_addresses(self.resolver(host, port))
        else:
            validate_public_addresses({str(literal)})

    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation:
        path = self.config.operation_paths.get(request.operation)
        if path is None:
            raise HttpSafetyError("HTTP_OPERATION_BLOCKED")
        url = urljoin(str(self.config.base_url), path)
        self._validate_destination(url)
        method = "GET" if request.operation.startswith("get_") else "POST"
        if method not in self.config.methods:
            raise HttpSafetyError("HTTP_METHOD_BLOCKED")
        headers = {"Accept": "application/json", "User-Agent": "saas-preflight/1"}
        if auth.credential_handle:
            credential = self.credential_provider(auth.credential_handle)
            if not credential:
                raise HttpSafetyError("HTTP_CREDENTIAL_UNAVAILABLE")
            headers["Authorization"] = f"Bearer {credential}"
        timeout = httpx.Timeout(self.config.timeout_seconds)
        try:
            with httpx.Client(
                verify=True,
                follow_redirects=False,
                trust_env=False,
                timeout=timeout,
                transport=self.transport,
            ) as client:
                with client.stream(
                    method, url, headers=headers, json=request.input or None
                ) as response:
                    if 300 <= response.status_code < 400:
                        raise HttpSafetyError("HTTP_REDIRECT_BLOCKED")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > self.config.max_response_bytes:
                            raise HttpSafetyError("HTTP_RESPONSE_TOO_LARGE")
                    if response.status_code >= 500:
                        raise HttpSafetyError("HTTP_UPSTREAM_UNAVAILABLE")
                    if response.status_code >= 400:
                        return Observation(
                            outcome="denied", changed=False, state={"status": response.status_code}
                        )
                    if "application/json" not in response.headers.get("content-type", "").lower():
                        raise HttpSafetyError("HTTP_CONTENT_TYPE_INVALID")
                    data = json.loads(body)
        except HttpSafetyError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError):
            raise HttpSafetyError("HTTP_TRANSPORT_FAILED") from None
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise HttpSafetyError("HTTP_RESPONSE_INVALID") from None
        if not isinstance(data, dict):
            raise HttpSafetyError("HTTP_RESPONSE_INVALID")
        return Observation.model_validate(data)
