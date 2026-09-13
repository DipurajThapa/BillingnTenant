"""Immutable Version 1.0 reference scenario catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    suite: str
    severity: str
    coverage: str = "required"
    feature_guard: str | None = None
    fixture_dependencies: tuple[str, ...] = ()
    port_dependencies: tuple[str, ...] = ()
    scenario_dependencies: tuple[str, ...] = ()
    evidence_allowlist: tuple[str, ...] = (
        "fixture_alias",
        "operation",
        "status",
        "state",
        "version",
        "counter",
    )


def _items(
    prefix: str,
    count: int,
    suite: str,
    *,
    blockers: set[int] | None = None,
    medium: set[int] | None = None,
    features: dict[int, str] | None = None,
    ports: tuple[str, ...] = (),
) -> list[Scenario]:
    blockers = blockers or set()
    medium = medium or set()
    features = features or {}
    return [
        Scenario(
            id=f"{prefix}-{i:03d}",
            title=f"{prefix} reference scenario {i:03d}",
            suite=suite,
            severity="blocker" if i in blockers else ("medium" if i in medium else "high"),
            coverage="conditional" if i in features else "required",
            feature_guard=features.get(i),
            fixture_dependencies=("reference_fixtures",),
            port_dependencies=ports,
        )
        for i in range(1, count + 1)
    ]


CATALOG = tuple(
    _items(
        "TEN",
        7,
        "tenant_reference",
        blockers={1, 2, 3, 4, 5},
        features={6: "multi_org_users", 7: "membership_management"},
        ports=("fixture", "identity_tenant", "clock"),
    )
    + _items(
        "RBAC",
        5,
        "rbac_reference",
        medium={4},
        features={4: "membership_management", 5: "multi_org_users"},
        ports=("fixture", "identity_tenant", "billing_state", "clock"),
    )
    + _items(
        "BILL",
        12,
        "billing_reference",
        medium={11},
        features={10: "multi_org_users", 11: "seat_billing"},
        ports=("fixture", "billing_state", "identity_tenant", "clock"),
    )
    + _items(
        "WEB",
        7,
        "webhook_reference",
        blockers={1, 3},
        medium={6},
        ports=("fixture", "event_delivery", "clock"),
    )
    + _items(
        "ENT",
        5,
        "entitlement_reference",
        medium={4},
        ports=("fixture", "identity_tenant", "billing_state", "clock"),
    )
    + _items(
        "USG",
        6,
        "usage_reference",
        medium={5},
        features={i: "metered_usage" for i in range(1, 7)},
        ports=("fixture", "usage", "billing_state", "clock"),
    )
)

BY_ID = {item.id: item for item in CATALOG}


def selected(suites: list[str]) -> list[Scenario]:
    return [item for item in CATALOG if item.suite in suites]
