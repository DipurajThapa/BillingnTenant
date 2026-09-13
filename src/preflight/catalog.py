"""Immutable Version 1.0 reference scenario catalog."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    id: str
    suite: str
    severity: str
    feature: str | None = None


def _items(prefix: str, count: int, suite: str, blockers: set[int] | None = None) -> list[Scenario]:
    blockers = blockers or set()
    return [
        Scenario(f"{prefix}-{i:03d}", suite, "blocker" if i in blockers else "high")
        for i in range(1, count + 1)
    ]


CATALOG = tuple(
    _items("TEN", 7, "tenant_reference", {1, 2, 3, 4, 5})
    + _items("RBAC", 5, "rbac_reference")
    + _items("BILL", 12, "billing_reference")
    + _items("WEB", 7, "webhook_reference", {1, 3})
    + _items("ENT", 5, "entitlement_reference")
    + [Scenario(f"USG-{i:03d}", "usage_reference", "high", "metered_usage") for i in range(1, 7)]
)

BY_ID = {item.id: item for item in CATALOG}


def selected(suites: list[str]) -> list[Scenario]:
    return [item for item in CATALOG if item.suite in suites]
