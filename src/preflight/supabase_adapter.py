"""Supabase identity/tenant adapter over the fail-closed HTTP transport."""

from collections.abc import Callable

from pydantic import Field, HttpUrl, field_validator

from preflight.external_http import RemoteHttpConfig, RemoteHttpTransport
from preflight.models import ActorRef, AuthContext, Observation, ProbeRequest, StrictModel


class SupabaseAdapterConfig(StrictModel):
    project_url: HttpUrl
    publishable_key_handle: str = Field(min_length=1, max_length=200)
    operation_functions: dict[str, str] = Field(min_length=1, max_length=100)

    @field_validator("project_url")
    @classmethod
    def project_url_is_supabase_https(cls, value: HttpUrl) -> HttpUrl:
        host = (value.host or "").lower()
        if value.scheme != "https" or not host.endswith(".supabase.co"):
            raise ValueError("projectUrl must use a Supabase HTTPS project host")
        return value

    @field_validator("operation_functions")
    @classmethod
    def function_names_are_safe(cls, value: dict[str, str]) -> dict[str, str]:
        for name in value.values():
            if not name.startswith("preflight_") or not name.replace("_", "").isalnum():
                raise ValueError("operation function names must use the preflight_ prefix")
        return value


class SupabaseIdentityTenantAdapter:
    """Maps core probe operations to fixed PostgREST RPC endpoints.

    The credential provider resolves opaque handles only at request time. Actor JWTs and
    publishable keys are never stored in configuration, results, findings, or logs.
    """

    name = "supabase-identity-tenant"
    version = "1.0"
    kind = "external"

    def __init__(
        self,
        config: SupabaseAdapterConfig,
        credential_provider: Callable[[str], str | None],
        *,
        resolver: Callable[[str, int], set[str]] | None = None,
        transport: object | None = None,
    ) -> None:
        self.config = config
        self.credential_provider = credential_provider
        host = config.project_url.host
        assert host is not None
        http_config = RemoteHttpConfig(
            baseUrl=config.project_url,
            allowedHosts=[host],
            operationPaths={
                operation: f"/rest/v1/rpc/{function}"
                for operation, function in config.operation_functions.items()
            },
        )
        kwargs: dict[str, object] = {"transport": transport}
        if resolver is not None:
            kwargs["resolver"] = resolver
        self._transport = RemoteHttpTransport(
            http_config,
            credential_provider,
            static_header_provider=self._static_headers,
            **kwargs,
        )

    def _static_headers(self) -> dict[str, str]:
        key = self.credential_provider(self.config.publishable_key_handle)
        return {"apikey": key or ""}

    def auth_context(self, actor: ActorRef) -> AuthContext:
        return AuthContext(
            mode="actor_session",
            actorId=actor.id,
            credentialHandle=f"supabase:actor:{actor.id}",
        )

    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation:
        if auth.mode != "actor_session" or auth.actor_id is None:
            return Observation(outcome="denied", changed=False)
        return self._transport.execute(auth, request)
