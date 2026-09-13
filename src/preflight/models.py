"""Strict provider-neutral C1 contracts."""

import json
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, PrivateAttr, model_validator


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


class TenantFixture(StrictModel):
    id: str
    alias: str
    resources: dict[str, ResourceRef] = Field(default_factory=dict)


class FixtureSet(StrictModel):
    run_id: str
    tenants: dict[str, TenantFixture]
    actors: dict[str, "ActorRef"]
    resources: list[ResourceRef]

    @model_validator(mode="after")
    def check_references(self) -> "FixtureSet":
        if any(key != value.alias for key, value in self.tenants.items()):
            raise ValueError("tenant key differs from alias")
        if any(key != value.alias for key, value in self.actors.items()):
            raise ValueError("actor key differs from alias")
        if any(value.run_id != self.run_id for value in self.resources):
            raise ValueError("resource run differs from fixture run")
        nested = [
            resource
            for tenant in self.tenants.values()
            for resource in tenant.resources.values()
        ]
        if any(value.run_id != self.run_id for value in nested):
            raise ValueError("nested resource run differs from fixture run")
        keys = [(value.kind, value.external_id) for value in self.resources]
        if len(keys) != len(set(keys)):
            raise ValueError("resource IDs duplicate within kind")
        if not {(value.kind, value.external_id) for value in nested} <= set(keys):
            raise ValueError("nested resource is absent from fixture resources")
        return self


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


class BillingProjection(StrictModel):
    tenant_id: str
    plan: str | None
    status: Literal["trialing", "active", "past_due", "canceled", "inactive", "unknown"]
    period_end: datetime | None = None
    cancel_at_period_end: bool = False


class EventEnvelope(StrictModel):
    event_id: str
    event_type: str
    object_id: str
    object_version: int = Field(ge=0)
    occurred_at: datetime
    state: dict[str, JsonValue] = Field(default_factory=dict)


class EventReceipt(StrictModel):
    event_id: str
    outcome: Literal["applied", "duplicate", "stale", "ignored", "rejected", "failed"]
    object_version: int | None = Field(default=None, ge=0)
    state_changed: bool
    error_code: str | None = None

    @model_validator(mode="after")
    def check_outcome(self) -> "EventReceipt":
        if (self.outcome == "applied") != self.state_changed:
            raise ValueError("state change conflicts with event outcome")
        if (self.outcome in {"rejected", "failed"}) != (self.error_code is not None):
            raise ValueError("error code conflicts with event outcome")
        return self


class SeatProjection(StrictModel):
    tenant_id: str
    active_memberships: int = Field(ge=0)
    pending_invitations: int = Field(ge=0)
    billable_quantity: int = Field(ge=0)


class Evidence(StrictModel):
    type: str
    source: str
    timestamp: datetime
    payload: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_sensitive_fields(self) -> "Evidence":
        sensitive = ("password", "secret", "token", "api_key", "apikey", "credential")

        def keys(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    yield str(key).lower()
                    yield from keys(item)
            elif isinstance(value, list):
                for item in value:
                    yield from keys(item)

        if any(part in key for key in keys(self.payload) for part in sensitive):
            raise ValueError("EVD_SENSITIVE_VALUE")
        return self


class Finding(StrictModel):
    id: str
    scenario_id: str
    severity: Literal["blocker", "high", "medium", "info"]
    impact: str
    expected: str
    observed: str
    reproduction_steps: list[str]
    remediation_hint: str
    evidence: list[Evidence] = Field(default_factory=list)


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
    evidence: list[Evidence] = Field(default_factory=list, max_length=50)
    finding_id: str | None = None

    @model_validator(mode="after")
    def check_status(self) -> "ScenarioResult":
        if (self.status == "skipped") != (self.skip_reason is not None):
            raise ValueError("skip reason conflicts with status")
        if (self.status == "error") != (self.error_code is not None):
            raise ValueError("error code conflicts with status")
        if (self.status == "failed") != (self.finding_id is not None):
            raise ValueError("finding conflicts with status")
        evidence_json = json.dumps(
            [item.model_dump(mode="json", by_alias=True) for item in self.evidence]
        )
        if len(evidence_json.encode()) > 64 * 1024:
            raise ValueError("EVD_FIELD_REJECTED: scenario evidence exceeds 64 KiB")
        return self


class RunSummary(StrictModel):
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    skipped: int = Field(ge=0)
    error: int = Field(ge=0)
    findings: int = Field(ge=0)


class ComponentProvenance(StrictModel):
    name: str
    version: str
    kind: Literal["reference", "external"]


class RunResult(StrictModel):
    _journal: object | None = PrivateAttr(default=None)
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    tool_version: str
    catalog_version: str
    execution_profile: Literal["reference", "external"]
    verification_level: Literal[
        "reference_verified", "integration_incomplete", "externally_verified"
    ]
    components: list[ComponentProvenance]
    verified_scopes: list[str]
    unverified_scopes: list[str]
    started_at: datetime
    finished_at: datetime | None
    config_hash: str
    git_sha: str | None = None
    selected_suites: list[str]
    execution_status: Literal["completed", "error", "interrupted"]
    assertion_gate_status: Literal["PASS", "WARN", "FAIL"]
    gate_status: Literal["PASS", "WARN", "FAIL", "INCOMPLETE"]
    cleanup_status: Literal["not_required", "completed", "partial", "failed"]
    summary: RunSummary
    results: list[ScenarioResult]
    findings: list[Finding]
    missing_coverage: list[str]
    diagnostics: list[str]

    @model_validator(mode="after")
    def check_run(self) -> "RunResult":
        if self.finished_at is not None and self.finished_at < self.started_at:
            raise ValueError("finishedAt precedes startedAt")
        if not self.components or any(
            not item.name or not item.version for item in self.components
        ):
            raise ValueError("component provenance is incomplete")
        if len(self.verified_scopes) != len(set(self.verified_scopes)) or len(
            self.unverified_scopes
        ) != len(set(self.unverified_scopes)):
            raise ValueError("verification scopes must be unique")
        if set(self.verified_scopes) & set(self.unverified_scopes):
            raise ValueError("verified and unverified scopes overlap")
        counts = {
            s: sum(x.status == s for x in self.results)
            for s in ("passed", "failed", "skipped", "error")
        }
        if any(getattr(self.summary, key) != value for key, value in counts.items()):
            raise ValueError("summary differs from results")
        if self.summary.findings != len(self.findings):
            raise ValueError("finding count differs from findings")
        if len({x.test_id for x in self.results}) != len(self.results):
            raise ValueError("duplicate scenario result")
        findings = {x.id: x for x in self.findings}
        if len(findings) != len(self.findings):
            raise ValueError("duplicate finding")
        linked_findings: set[str] = set()
        for row in self.results:
            if row.suite not in self.selected_suites:
                raise ValueError("result suite was not selected")
            if row.finding_id:
                finding = findings.get(row.finding_id)
                if (
                    not finding
                    or finding.scenario_id != row.test_id
                    or finding.severity != row.severity
                ):
                    raise ValueError("finding differs from failed scenario")
                linked_findings.add(row.finding_id)
        if linked_findings != set(findings):
            raise ValueError("orphan finding")
        serious_failure = any(
            row.status == "failed" and row.severity in {"blocker", "high"} for row in self.results
        )
        medium_failure = any(
            row.status == "failed" and row.severity == "medium" for row in self.results
        )
        if serious_failure and self.assertion_gate_status != "FAIL":
            raise ValueError("assertion gate differs from results")
        if not serious_failure and not medium_failure and self.assertion_gate_status != "PASS":
            raise ValueError("assertion gate differs from results")
        if medium_failure and self.assertion_gate_status not in {"WARN", "FAIL"}:
            raise ValueError("assertion gate differs from results")
        incomplete = (
            self.execution_status != "completed"
            or self.cleanup_status in {"partial", "failed"}
            or bool(self.missing_coverage)
            or any(row.status == "error" for row in self.results)
        )
        expected_final = "INCOMPLETE" if incomplete else self.assertion_gate_status
        if self.gate_status != expected_final:
            raise ValueError("final gate differs from execution state")
        if self.execution_profile == "reference":
            if any(x.kind != "reference" for x in self.components):
                raise ValueError("reference run contains external component")
            expected = "integration_incomplete" if incomplete else "reference_verified"
            if self.verification_level != expected:
                raise ValueError("invalid reference verification level")
        return self
