"""Deterministic reference scenario actions and oracles."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from preflight.models import AuthContext, EventEnvelope

if TYPE_CHECKING:
    from preflight.config import CoreConfig
    from preflight.reference import ReferenceTarget


def evaluate_reference_scenario(
    source: "ReferenceTarget", config: "CoreConfig", test_id: str, defective: bool
) -> tuple[bool, str]:
    target = deepcopy(source)
    prefix, number_text = test_id.split("-")
    number = int(number_text)
    evaluators = {
        "TEN": _tenant,
        "RBAC": _rbac,
        "BILL": _billing,
        "WEB": _webhook,
        "ENT": _entitlement,
        "USG": _usage,
    }
    evaluator = evaluators.get(prefix)
    if evaluator is None:
        raise ValueError("unsupported reference scenario")
    passed, detail = evaluator(target, config, number, defective)
    return passed, detail if not passed else "reference oracle satisfied"


def _tenant(target, _config, number: int, defective: bool) -> tuple[bool, str]:
    if number == 1:
        observed = target.resources["b1"] if defective else target.read_resource("AM", "b1")
        return observed is None, "cross-tenant resource was visible"
    if number == 2:
        observed = target.list_resources("AM") + (["b1"] if defective else [])
        return "b1" not in observed, "cross-tenant ID leaked from list"
    if number == 3:
        target.create_resource("AM", "created", "TB")
        if defective:
            target.resources["created"] = ("TB", "AM")
        return target.resources["created"] == ("TA", "AM"), "client tenant was trusted"
    if number == 4:
        before = target.resources["a1"]
        if defective:
            target.resources["a1"] = ("TB", before[1])
        return target.resources["a1"] == before, "resource tenant was reassigned"
    if number == 5:
        before = target.resources["b1"]
        changed = target.mutate_resource("AM", "b1", delete=defective)
        if defective:
            target.resources.pop("b1", None)
        return not changed and target.resources.get("b1") == before, "foreign resource changed"
    if number == 6:
        switched = target.switch_tenant("MA", "TB")
        if defective:
            target.active_tenants["MA"] = "TA"
        return switched and target.list_resources("MA") == ["b1"], "stale tenant context remained"
    if number == 7:
        target.remove_membership("AM", "TA")
        if defective:
            target.roles[("AM", "TA")] = "member"
        return target.read_resource("AM", "a1") is None, "revoked membership retained access"
    raise ValueError("unsupported tenant scenario")


def _rbac(target, config, number: int, defective: bool) -> tuple[bool, str]:
    permissions = config.role_permissions
    if number == 1:
        denied = not target.permitted("AM", permissions, "member_management")
        allowed = target.permitted("AO", permissions, "member_management")
        return denied and allowed and not defective, "member obtained an admin operation"
    if number == 2:
        allowed = target.permitted("AM", permissions, "billing_settings")
        if allowed or defective:
            target.bind_account("TA", "unauthorized")
        return not allowed and target.get_binding(
            "TA"
        ) is None, "unauthorized billing action occurred"
    if number == 3:
        initially_allowed = target.permitted("MA", permissions, "billing_settings")
        target.set_role("MA", "TA", "member" if not defective else "admin")
        later_denied = not target.permitted("MA", permissions, "billing_settings")
        return initially_allowed and later_denied, "role downgrade did not revoke permission"
    if number == 4:
        unchanged = ("NEW", "TA") not in target.roles
        if defective:
            target.roles[("NEW", "TA")] = "member"
        return unchanged and ("NEW", "TA") not in target.roles, "unauthorized membership changed"
    if number == 5:
        allowed_a = target.permitted("MA", permissions, "billing_settings")
        target.switch_tenant("MA", "TB")
        denied_b = not target.permitted("MA", permissions, "billing_settings")
        if defective:
            denied_b = False
        return allowed_a and denied_b, "role leaked between tenant contexts"
    raise ValueError("unsupported RBAC scenario")


def _plans(config) -> tuple[str, str]:
    names = list(config.plans)
    return names[0], names[-1]


def _billing(target, config, number: int, defective: bool) -> tuple[bool, str]:
    low, high = _plans(config)
    if number == 1:
        target.bind_account("TA", "acct_a" if not defective else "acct_wrong")
        projection = target.create_subscription("TA", high)
        return (
            target.get_binding("TA") == "acct_a"
            and projection.status == "active"
            and projection.plan == high
        ), "binding or active subscription projection differed"
    if number == 2:
        projection = target.create_subscription("TA", config.billing_policy.trial_plan, 14)
        if defective:
            projection.status = "active"
        return projection.status == "trialing", "trial did not remain trialing"
    if number == 3:
        expected = config.billing_policy.trial_end_behavior
        actual = expected if not defective else "unexpected"
        return actual == expected, "trial boundary behavior differed"
    if number == 4:
        target.create_subscription("TA", low)
        expected_before = high if config.billing_policy.upgrade_effective == "immediate" else low
        expected_after = high
        actual = (low, low) if defective else (expected_before, expected_after)
        return actual == (expected_before, expected_after), "upgrade entitlement boundary differed"
    if number == 5:
        target.create_subscription("TA", high)
        expected_before = high if config.billing_policy.downgrade_effective == "period_end" else low
        actual_before = low if defective and expected_before == high else expected_before
        return actual_before == expected_before, "downgrade boundary differed"
    if number == 6:
        target.create_subscription("TA", high)
        projection = target.transition("TA", "cancel")
        expected_deferred = config.billing_policy.cancel_behavior == "end_of_period"
        projection.cancel_at_period_end = not expected_deferred if defective else expected_deferred
        return (
            projection.cancel_at_period_end == expected_deferred,
            "cancellation boundary differed",
        )
    if number == 7:
        expected = config.billing_policy.past_due_behavior
        actual = expected if not defective else "unexpected"
        return actual == expected, "past-due access policy differed"
    if number == 8:
        target.create_subscription("TA", high)
        target.transition("TA", "past_due")
        recovered = target.transition("TA", "recover")
        effects = 2 if defective else 1
        return recovered.status == "active" and effects == 1, "recovery was not exactly once"
    if number == 9:
        target.create_subscription("TA", high)
        target.transition("TA", "cancel")
        expected = config.billing_policy.reactivation_behavior
        expected_status = "active" if expected == "restore_selected_plan" else "inactive"
        actual_status = (
            ("inactive" if expected_status == "active" else "active")
            if defective
            else expected_status
        )
        return actual_status == expected_status, "reactivation policy differed"
    if number == 10:
        target.bind_account("TA", "acct_a")
        target.bind_account("TB", "acct_b")
        observed = target.get_binding("TB" if not defective else "TA")
        return observed == "acct_b", "active tenant used another billing binding"
    if number == 11:
        active, pending = 3, 2
        expected = max(config.seat_policy.minimum_quantity, active)
        if config.seat_policy.pending_invitations_count:
            expected = max(config.seat_policy.minimum_quantity, active + pending)
        actual = expected + 1 if defective else expected
        return actual == expected, "seat quantity formula differed"
    if number == 12:
        fallback = set(config.billing_policy.unknown_plan_entitlements)
        observed = fallback | ({"invented"} if defective else set())
        return observed <= fallback, "unknown plan granted undeclared entitlement"
    raise ValueError("unsupported billing scenario")


def _event(event_id: str, version: int, event_type: str = "subscription.updated") -> EventEnvelope:
    return EventEnvelope(
        eventId=event_id,
        eventType=event_type,
        objectId="sub_reference",
        objectVersion=version,
        occurredAt=datetime(2026, 1, 1, tzinfo=UTC),
        state={"tenantId": "TA", "counter": "billing"},
    )


def _webhook(target, _config, number: int, defective: bool) -> tuple[bool, str]:
    valid = AuthContext(mode="signed_event", credentialHandle="reference:event")
    if number == 1:
        target.deliver(_event("evt_1", 1), valid)
        target.deliver(_event("evt_2" if defective else "evt_1", 2 if defective else 1), valid)
        return target.side_effect_count("TA", "billing") == 1, "duplicate event changed state twice"
    if number == 2:
        target.deliver(_event("evt_1", 1), valid)
        target.deliver(_event("evt_2", 2 if defective else 1), valid)
        return target.side_effect_count(
            "TA", "billing"
        ) == 1, "equivalent event changed state twice"
    if number == 3:
        target.deliver(_event("evt_new", 2), valid)
        target.deliver(_event("evt_old", 1), valid)
        if defective:
            target.versions["sub_reference"] = 1
        return target.versions["sub_reference"] == 2, "stale event replaced newer state"
    if number == 4:
        if not defective:
            target.deliver(_event("evt_retry", 1), valid)
        else:
            target.side_effects[("TA", "billing")] = 2
        return target.side_effect_count("TA", "billing") == 1, "retry did not converge exactly once"
    if number == 5:
        auth = valid if defective else AuthContext(mode="signed_event", credentialHandle="invalid")
        receipt = target.deliver(_event("evt_invalid", 1), auth)
        return (
            receipt.outcome == "rejected" and not receipt.state_changed,
            "invalid signature changed state",
        )
    if number == 6:
        event_type = "subscription.updated" if defective else "irrelevant"
        receipt = target.deliver(_event("evt_irrelevant", 1, event_type), valid)
        return (
            receipt.outcome == "ignored" and not receipt.state_changed,
            "irrelevant event mutated state",
        )
    if number == 7:
        event = _event("evt_restart", 1)
        target.deliver(event, valid)
        if defective:
            target.events.clear()
            target.versions.clear()
        target.deliver(event, valid)
        return target.side_effect_count("TA", "billing") == 1, "restart lost deduplication state"
    raise ValueError("unsupported webhook scenario")


def _capability_allowed(config, role: str, plan: str, capability_name: str) -> bool:
    capability = config.capabilities[capability_name]
    permissions = config.role_permissions[role]
    entitlements = config.plans[plan].entitlements
    return (
        capability.required_permission is None or capability.required_permission in permissions
    ) and (
        capability.required_entitlement is None or capability.required_entitlement in entitlements
    )


def _entitlement(_target, config, number: int, defective: bool) -> tuple[bool, str]:
    roles = list(config.roles)
    plans = list(config.plans)
    capabilities = list(config.capabilities)
    matrix = [
        _capability_allowed(config, role, plan, capability)
        for role in roles
        for plan in plans
        for capability in capabilities
    ]
    if number in {1, 2}:
        return bool(matrix) and not defective, "capability matrix differed from formula"
    if number == 3:
        capability = next(
            (
                name
                for name, value in config.capabilities.items()
                if value.required_entitlement is not None
            ),
            None,
        )
        if capability is None:
            return not defective, "no entitlement-dependent capability available"
        low, high = _plans(config)
        expected = _capability_allowed(config, roles[0], low, capability)
        observed = not expected if defective else expected
        return observed == expected, "downgrade retained premium capability"
    if number == 4:
        known = {item for plan in config.plans.values() for item in plan.entitlements}
        reported = "invented" not in known
        return reported and not defective, "unknown entitlement was enabled or unreported"
    if number == 5:
        denied = any(
            not _capability_allowed(config, role, plan, capability)
            for role in roles
            for plan in plans
            for capability in capabilities
        )
        return denied and not defective, "unentitled direct operation succeeded"
    raise ValueError("unsupported entitlement scenario")


def _usage(target, config, number: int, defective: bool) -> tuple[bool, str]:
    meter = config.usage_policy.meter
    if number == 1:
        target.record_usage("TA", meter, Decimal(2), "a")
        target.record_usage("TB", meter, Decimal(3), "b")
        if defective:
            target.usage[("TA", meter)] += target.usage[("TB", meter)]
        return target.usage_projection("TA", meter).quantity == 2, "tenant usage was mixed"
    if number == 2:
        target.record_usage("TA", meter, Decimal(2), "same")
        target.record_usage("TA", meter, Decimal(2), "other" if defective else "same")
        return target.usage_projection("TA", meter).quantity == 2, "usage idempotency failed"
    if number == 3:
        plan = next(iter(config.plans))
        quota = Decimal(config.usage_policy.quotas_by_plan[plan])
        observed = quota + 1 if defective else quota
        allowed = observed <= quota
        return allowed, "usage above quota was accepted"
    if number == 4:
        target.record_usage("TA", meter, Decimal(2), "before-plan-change")
        if defective:
            target.usage[("TA", meter)] = Decimal(0)
        return target.usage_projection("TA", meter).quantity == 2, "plan change reset period usage"
    if number == 5:
        reversible = not defective
        return reversible, "stale usage projection caused irreversible decision"
    if number == 6:
        before = target.usage_projection("TB", meter).quantity
        if defective:
            target.record_usage("TB", meter, Decimal(1), "wrong-tenant")
        after = target.usage_projection("TB", meter).quantity
        return after == before, "usage was attributed to the wrong tenant"
    raise ValueError("unsupported usage scenario")
