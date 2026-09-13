"""Provider-neutral contracts; core imports no concrete external adapter."""

from datetime import datetime
from decimal import Decimal
from typing import Protocol

from preflight.models import (
    ActorRef,
    AuthContext,
    BillingProjection,
    EventEnvelope,
    EventReceipt,
    FixtureSet,
    Observation,
    ProbeRequest,
    UsageProjection,
)


class FixturePort(Protocol):
    contract_version: str

    def provision(self, run_id: str, requirements: list[str]) -> FixtureSet: ...
    def cleanup(self, run_id: str, fixtures: FixtureSet) -> None: ...


class IdentityTenantPort(Protocol):
    def auth_context(self, actor: ActorRef) -> AuthContext: ...
    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation: ...


class BillingStatePort(Protocol):
    def projection(self, tenant_id: str) -> BillingProjection: ...
    def entitlements(self, tenant_id: str) -> list[str]: ...


class EventDeliveryPort(Protocol):
    def deliver(self, event: EventEnvelope, auth: AuthContext) -> EventReceipt: ...


class UsagePort(Protocol):
    def record(
        self, tenant_id: str, meter: str, quantity: Decimal, idempotency_key: str
    ) -> None: ...
    def projection(self, tenant_id: str, meter: str) -> UsageProjection: ...


class ProbeTransport(Protocol):
    name: str
    version: str
    kind: str

    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...
    def tick(self, count: int = 1) -> datetime: ...
