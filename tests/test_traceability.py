import re
from pathlib import Path

import yaml

from preflight.catalog import CATALOG

RANGE = re.compile(r"^(.+)-(\d{3})-(\d{3})$")
ID = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d{3}$")


def expand(value: str, *, tests: bool = False) -> set[str]:
    scenarios = {row.id for row in CATALOG}
    if value == "SCN-ALL":
        return scenarios
    if value == "DEF-ALL":
        return {f"DEF-{item}" for item in scenarios}
    match = RANGE.fullmatch(value)
    if not match:
        return {value}
    prefix, start, end = match.groups()
    expanded = {f"{prefix}-{number:03d}" for number in range(int(start), int(end) + 1)}
    return expanded


def identifiers(path: Path) -> set[str]:
    return set(
        re.findall(
            r"(?<![A-Z0-9_-])([A-Z][A-Z0-9]*(?:-[A-Z][A-Z0-9]*)*-\d{3})(?![A-Z0-9_-])",
            path.read_text(),
        )
    )


def test_traceability_resolves_bidirectionally_against_authoritative_sources() -> None:
    data = yaml.safe_load(Path("tests/traceability.yml").read_text())
    assert data["schemaVersion"] == "1.0"
    entries = data["entries"]
    raw_requirements = [entry["requirementId"] for entry in entries]
    assert len(raw_requirements) == len(set(raw_requirements))
    assert all(entry["testIds"] and entry["acceptanceIds"] for entry in entries)

    traced_requirements = set().union(*(expand(value) for value in raw_requirements))
    traced_tests = set().union(
        *(expand(value, tests=True) for entry in entries for value in entry["testIds"])
    )
    traced_acceptance = {value for entry in entries for value in entry["acceptanceIds"]}

    primary = Path("docs/spec/00_PRIMARY_PRODUCT_SPEC.md")
    contracts = Path("docs/spec/01_CORE_CONTRACTS_AND_SCENARIOS.md")
    verification = Path("docs/spec/02_CORE_VERIFICATION_AND_TRACEABILITY.md")
    supabase = Path("docs/decisions/SUP-001.md")
    accessibility = Path("docs/decisions/A11Y-001.md")
    dashboard = Path("docs/decisions/DASH-001.md")
    for source in (primary, contracts, verification, supabase, accessibility, dashboard):
        assert source.exists()

    material_requirements = {
        value
        for value in identifiers(primary)
        if value.startswith(
            (
                "PRD-",
                "VER-",
                "WF-",
                "ARC-",
                "STA-",
                "SEC-CORE-",
                "ERR-",
                "UI-",
                "OPS-",
            )
        )
    }
    material_requirements |= {
        value
        for value in identifiers(contracts)
        if value.startswith(("DATA-", "CFG-", "PORT-", "EVD-", "JRN-"))
        and not (
            (value.startswith("CFG-") and int(value.rsplit("-", 1)[1]) > 3)
            or (value.startswith("PORT-") and int(value.rsplit("-", 1)[1]) > 7)
        )
    }
    material_requirements |= {
        value
        for value in identifiers(verification)
        if value.startswith(("TST-", "LIM-"))
        and not (value.startswith("TST-") and int(value.rsplit("-", 1)[1]) > 6)
    }
    material_requirements |= {
        f"SCN-{prefix}" for prefix in ("TEN", "RBAC", "BILL", "WEB", "ENT", "USG")
    }
    material_requirements |= {
        value for value in identifiers(supabase) if re.fullmatch(r"SUP-\d{3}", value)
    }
    material_requirements |= expand("A11Y-REQ-001-004")
    material_requirements |= expand("DASH-REQ-001-008")
    assert traced_requirements == material_requirements

    specified_tests = {
        value
        for value in identifiers(verification)
        if value.startswith(
            (
                "DAT-",
                "PROV-",
                "CFG-",
                "CLI-",
                "RUN-",
                "PORT-",
                "ARCH-",
                "GATE-",
                "COV-",
                "DIA-",
                "EVD-",
                "ERR-",
                "CLN-",
                "RPT-",
                "OPS-",
                "PKG-",
                "LIM-",
                "SCOPE-",
                "SEC-",
            )
        )
        and not value.startswith("SEC-CORE-")
    }
    specified_tests |= {row.id for row in CATALOG}
    specified_tests |= {f"DEF-{row.id}" for row in CATALOG}
    specified_tests.add("TRACE-001")
    specified_tests |= expand("SUP-CONTRACT-001-005")
    specified_tests |= expand("SUP-LIVE-001-007")
    specified_tests |= expand("A11Y-AUTO-001-004")
    specified_tests |= expand("A11Y-EVD-001-003")
    specified_tests |= expand("A11Y-MAN-001-010")
    specified_tests |= expand("DASH-TST-001-005")
    assert traced_tests == specified_tests

    specified_acceptance = {value for value in identifiers(verification) if value.startswith("AC-")}
    specified_acceptance |= {
        value for value in identifiers(supabase) if value.startswith("SUP-AC-")
    }
    specified_acceptance |= {
        value for value in identifiers(accessibility) if value.startswith("A11Y-AC-")
    }
    specified_acceptance |= {
        value for value in identifiers(dashboard) if value.startswith("DASH-AC-")
    }
    assert traced_acceptance == specified_acceptance
