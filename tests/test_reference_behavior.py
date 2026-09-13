from datetime import UTC, datetime
from decimal import Decimal

import pytest

from preflight.config import example_config
from preflight.models import AuthContext, EventEnvelope
from preflight.reference import ReferenceTarget


def test_reference_tenant_isolation_and_membership_revocation() -> None:
    target = ReferenceTarget()
    assert target.read_resource("AM", "a1") == ("TA", "A")
    assert target.read_resource("AM", "b1") is None
    assert target.list_resources("AM") == ["a1"]
    assert target.create_resource("AM", "new", "TB")
    assert target.resources["new"] == ("TA", "AM")
    assert not target.mutate_resource("AM", "b1", delete=True)
    assert "b1" in target.resources
    target.remove_membership("AM", "TA")
    assert target.read_resource("AM", "a1") is None


def test_reference_role_and_active_tenant_permissions() -> None:
    target = ReferenceTarget()
    permissions = example_config().role_permissions
    assert target.permitted("AO", permissions, "billing_settings")
    assert not target.permitted("AM", permissions, "billing_settings")
    assert target.switch_tenant("MA", "TB")
    assert not target.permitted("MA", permissions, "billing_settings")
    assert not target.switch_tenant("AM", "TB")


def test_reference_billing_bindings_and_transitions_are_tenant_scoped() -> None:
    target = ReferenceTarget()
    target.bind_account("TA", "acct_a")
    target.bind_account("TB", "acct_b")
    assert target.get_binding("TA") == "acct_a"
    assert target.get_binding("TB") == "acct_b"
    assert target.create_subscription("TA", "pro", trial_days=14).status == "trialing"
    assert target.transition("TA", "past_due").status == "past_due"
    assert target.transition("TA", "recover").status == "active"
    assert target.transition("TA", "cancel").status == "canceled"
    with pytest.raises(ValueError):
        target.transition("TA", "invented")


def test_reference_event_delivery_rejects_invalid_deduplicates_and_orders() -> None:
    target = ReferenceTarget()
    event = EventEnvelope(
        eventId="evt_1",
        eventType="subscription.updated",
        objectId="sub_1",
        objectVersion=2,
        occurredAt=datetime(2026, 1, 1, tzinfo=UTC),
        state={"tenantId": "TA", "counter": "billing"},
    )
    invalid = AuthContext(mode="signed_event", credentialHandle="wrong")
    assert target.deliver(event, invalid).outcome == "rejected"
    assert target.side_effect_count("TA", "billing") == 0

    valid = AuthContext(mode="signed_event", credentialHandle="reference:event")
    assert target.deliver(event, valid).outcome == "applied"
    assert target.deliver(event, valid).outcome == "duplicate"
    stale = event.model_copy(update={"event_id": "evt_2", "object_version": 1})
    assert target.deliver(stale, valid).outcome == "stale"
    assert target.side_effect_count("TA", "billing") == 1


def test_reference_usage_is_tenant_scoped_idempotent_and_nonnegative() -> None:
    target = ReferenceTarget()
    target.record_usage("TA", "calls", Decimal("2.5"), "key-1")
    target.record_usage("TA", "calls", Decimal("2.5"), "key-1")
    target.record_usage("TB", "calls", Decimal("1"), "key-1")
    assert target.usage_projection("TA", "calls").quantity == Decimal("2.5")
    assert target.usage_projection("TB", "calls").quantity == Decimal("1")
    with pytest.raises(ValueError):
        target.record_usage("TA", "calls", Decimal("-1"), "key-2")


def test_scenario_oracle_observes_runtime_behavior_not_only_seeded_flags() -> None:
    target = ReferenceTarget()
    target.read_resource = lambda _actor, _resource: ("TB", "B")  # type: ignore[method-assign]
    passed, observed = target.evaluate("TEN-001", example_config())
    assert not passed
    assert observed == "cross-tenant resource was visible"
