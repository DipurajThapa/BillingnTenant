import asyncio
from pathlib import Path

import pytest

from preflight import ports
from preflight.lifecycle import FixtureJournal
from preflight.reference import ReferenceTarget
from preflight.reference_ports import build_reference_ports


def test_all_provider_neutral_ports_exist() -> None:
    names = {
        "FixturePort",
        "IdentityTenantPort",
        "BillingStatePort",
        "EventDeliveryPort",
        "UsagePort",
        "ProbeTransport",
        "ClockPort",
    }
    assert all(hasattr(ports, name) for name in names)


def test_ports_module_contains_no_provider_names() -> None:
    source = Path(ports.__file__).read_text(encoding="utf-8").lower()
    assert "stripe" not in source and "supabase" not in source


def test_port_methods_match_the_authoritative_contract() -> None:
    assert set(ports.IdentityTenantPort.__dict__) >= {
        "auth_context",
        "switch_tenant",
        "set_role",
        "remove_membership",
        "execute",
    }
    assert set(ports.BillingStatePort.__dict__) >= {
        "bind_account",
        "get_binding",
        "create_subscription",
        "transition",
        "projection",
        "entitlements",
    }
    assert set(ports.EventDeliveryPort.__dict__) >= {
        "deliver",
        "current_object_version",
        "side_effect_count",
        "fail_next_delivery",
        "restart",
    }


def test_all_bundled_reference_ports_implement_complete_contract() -> None:
    port_set = build_reference_ports(ReferenceTarget(), FixtureJournal("contract"))
    ports.validate_port_set(port_set)
    assert set(port_set) == set(ports.REQUIRED_METHODS)


def test_missing_method_and_external_transport_are_rejected() -> None:
    port_set = build_reference_ports(ReferenceTarget(), FixtureJournal("contract"))
    port_set["ClockPort"] = object()
    with pytest.raises(ValueError, match="PORT_MISSING: ClockPort"):
        ports.validate_port_set(port_set)
    port_set = build_reference_ports(ReferenceTarget(), FixtureJournal("contract"))
    port_set["ProbeTransport"].kind = "external"
    with pytest.raises(ValueError, match="CORE_EXTERNAL_NOT_ENABLED"):
        ports.validate_port_set(port_set)


def test_sync_and_async_port_results_are_normalized() -> None:
    async def asynchronous():
        return "async"

    assert asyncio.run(ports.normalize_port_result("sync")) == "sync"
    assert asyncio.run(ports.normalize_port_result(asynchronous())) == "async"
