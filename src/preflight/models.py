"""Strict provider-neutral C1 contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


def _camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(x.capitalize() for x in tail)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, alias_generator=_camel)


class ResourceRef(StrictModel):
    kind: str
    external_id: str
    tenant_id: str | None = None
    owner_actor_id: str | None = None
    run_id: str
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)


class MembershipRef(StrictModel):
    tenant_id: str
    role: str
    active: bool = True


class ActorRef(StrictModel):
    id: str
    alias: str
    memberships: list[MembershipRef]
    active_tenant_id: str

    @model_validator(mode="after")
    def check_active_tenant(self) -> "ActorRef":
        if not any(x.active and x.tenant_id == self.active_tenant_id for x in self.memberships):
            raise ValueError("active tenant must be an active membership")
        return self


class AuthContext(StrictModel):
    mode: Literal["actor_session", "public", "signed_event"]
    actor_id: str | None = None
    credential_handle: str | None = Field(default=None, exclude=True)
    privileged: bool = False

    @model_validator(mode="after")
    def check_mode(self) -> "AuthContext":
        if self.mode == "actor_session":
            valid = bool(self.actor_id and self.credential_handle and not self.privileged)
        elif self.mode == "public":
            valid = self.actor_id is None and self.credential_handle is None and not self.privileged
        else:
            valid = self.actor_id is None and bool(self.credential_handle) and not self.privileged
        if not valid:
            raise ValueError("invalid authentication mode fields")
        return self


class ProbeRequest(StrictModel):
    operation: str
    resource_kind: str | None = None
    resource_id: str | None = None
    input: dict[str, JsonValue] = Field(default_factory=dict)


class Observation(StrictModel):
    outcome: Literal["allowed", "denied", "success", "not_found", "invalid", "conflict"]
    state: dict[str, JsonValue] = Field(default_factory=dict)
    changed: bool
    error_code: str | None = None

    @model_validator(mode="after")
    def check_error(self) -> "Observation":
        if (self.outcome in {"invalid", "conflict"}) != (self.error_code is not None):
            raise ValueError("error code conflicts with outcome")
        return self


class UsageProjection(StrictModel):
    tenant_id: str
    meter: str
    quantity: Decimal = Field(ge=0, allow_inf_nan=False)
    period_start: datetime
    period_end: datetime

    @model_validator(mode="after")
    def check_period(self) -> "UsageProjection":
        if self.period_end <= self.period_start:
            raise ValueError("period end must follow start")
        return self


class ScenarioResult(StrictModel):
    test_id: str
    suite: str
    severity: Literal["blocker", "high", "medium", "info"]
    applicability: Literal["required", "conditional", "optional", "not_applicable"]
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: int = Field(ge=0)
    expected: str
    observed: str
    skip_reason: str | None = None
    error_code: str | None = None
    finding_id: str | None = None

    @model_validator(mode="after")
    def check_status(self) -> "ScenarioResult":
        if (self.status == "skipped") != (self.skip_reason is not None):
            raise ValueError("skip reason conflicts with status")
        if (self.status == "error") != (self.error_code is not None):
            raise ValueError("error code conflicts with status")
        if (self.status == "failed") != (self.finding_id is not None):
            raise ValueError("finding conflicts with status")
        return self
