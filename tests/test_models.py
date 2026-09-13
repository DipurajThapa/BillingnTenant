from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from preflight.config import example_config
from preflight.engine import execute
from preflight.models import (
    ActorRef,
    AuthContext,
    Evidence,
    FixtureSet,
    MembershipRef,
    ResourceRef,
    RunResult,
    ScenarioResult,
    TenantFixture,
    UsageProjection,
)


def test_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        MembershipRef(tenantId="t1", role="owner", surprise=True)


def test_actor_requires_active_membership() -> None:
    with pytest.raises(ValidationError):
        ActorRef(id="a1", alias="AO", memberships=[], activeTenantId="t1")


@pytest.mark.parametrize(
    ("payload", "valid"),
    [
        ({"mode": "actor_session", "actorId": "a1", "credentialHandle": "secret"}, True),
        ({"mode": "actor_session", "actorId": "a1"}, False),
        ({"mode": "public"}, True),
        ({"mode": "public", "actorId": "a1"}, False),
        ({"mode": "signed_event", "credentialHandle": "secret"}, True),
    ],
)
def test_auth_mode_combinations(payload: dict[str, object], valid: bool) -> None:
    if valid:
        model = AuthContext.model_validate(payload)
        assert "credentialHandle" not in model.model_dump(by_alias=True)
    else:
        with pytest.raises(ValidationError):
            AuthContext.model_validate(payload)


def test_usage_is_finite_nonnegative_with_valid_period() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    end = datetime(2026, 2, 1, tzinfo=UTC)
    value = UsageProjection(
        tenantId="t1", meter="calls", quantity=Decimal("1.5"), periodStart=start, periodEnd=end
    )
    assert value.model_dump(mode="json", by_alias=True)["quantity"] == "1.5"
    with pytest.raises(ValidationError):
        UsageProjection(
            tenantId="t1", meter="calls", quantity=Decimal("NaN"), periodStart=start, periodEnd=end
        )


def test_scenario_status_requires_matching_detail() -> None:
    base = dict(
        testId="TEN-001",
        suite="tenant_reference",
        severity="blocker",
        applicability="required",
        durationMs=1,
        expected="denied",
        observed="denied",
    )
    assert ScenarioResult(status="passed", **base).status == "passed"
    with pytest.raises(ValidationError):
        ScenarioResult(status="failed", **base)


def test_run_result_rejects_gate_scope_and_finding_inconsistency() -> None:
    result = execute(example_config())
    payload = result.model_dump(mode="json", by_alias=True)
    payload["gateStatus"] = "FAIL"
    with pytest.raises(ValidationError, match="final gate"):
        RunResult.model_validate(payload)

    payload = result.model_dump(mode="json", by_alias=True)
    payload["unverifiedScopes"].append(payload["verifiedScopes"][0])
    with pytest.raises(ValidationError, match="overlap"):
        RunResult.model_validate(payload)

    payload = result.model_dump(mode="json", by_alias=True)
    payload["components"] = []
    with pytest.raises(ValidationError, match="provenance"):
        RunResult.model_validate(payload)


def test_fixture_set_rejects_unregistered_nested_resource() -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    nested = ResourceRef(kind="record", externalId="one", runId="run", createdAt=created)
    tenant = TenantFixture(id="t1", alias="TA", resources={"one": nested})
    with pytest.raises(ValidationError, match="absent"):
        FixtureSet(runId="run", tenants={"TA": tenant}, actors={}, resources=[])


def test_evidence_model_rejects_nested_sensitive_field() -> None:
    with pytest.raises(ValidationError, match="EVD_SENSITIVE_VALUE"):
        Evidence(
            type="observation",
            source="TEN-001",
            timestamp=datetime(2026, 1, 1, tzinfo=UTC),
            payload={"nested": {"accessToken": "secret"}},
        )
