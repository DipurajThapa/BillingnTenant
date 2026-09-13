from pathlib import Path

from preflight import ports


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
