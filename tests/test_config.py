import pytest
from pydantic import ValidationError

from preflight.config import CoreConfig, resolve_suites


def minimal_config() -> dict[str, object]:
    return {
        "schemaVersion": "1.0",
        "profile": "reference",
        "projectLabel": "sample-saas",
        "roles": ["owner"],
        "rolePermissions": {"owner": ["export"]},
        "plans": {"free": {"entitlements": ["dashboard"]}},
        "capabilities": {"export": {"requiredPermission": "export", "requiredEntitlement": None}},
        "billingPolicy": {"trialPlan": "free", "trialDays": 14},
    }


def test_core_config_is_strict_and_exports_schema() -> None:
    model = CoreConfig.model_validate(minimal_config())
    assert model.profile == "reference"
    assert "properties" in CoreConfig.model_json_schema()
    with pytest.raises(ValidationError):
        CoreConfig.model_validate({**minimal_config(), "provider": {"name": "stripe"}})


def test_reference_core_expands_and_deduplicates() -> None:
    assert resolve_suites(["billing_reference", "reference_core"]) == [
        "tenant_reference",
        "rbac_reference",
        "billing_reference",
        "webhook_reference",
        "entitlement_reference",
    ]


def test_external_or_old_suite_is_rejected() -> None:
    with pytest.raises(ValueError, match="CORE_EXTERNAL_NOT_ENABLED"):
        resolve_suites(["billing"])
