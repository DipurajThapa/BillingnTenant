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
