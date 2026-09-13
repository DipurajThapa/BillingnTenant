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
        "capabilities": {
            "export": {
                "requiredPermission": "export",
                "requiredEntitlement": None,
                "operation": "export",
            }
        },
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


@pytest.mark.parametrize(
    "change",
    [
        {"roles": ["owner", "owner"]},
        {"rolePermissions": {"owner": ["export", "export"]}},
        {
            "capabilities": {
                "export": {
                    "requiredPermission": "missing",
                    "requiredEntitlement": None,
                    "operation": "export",
                }
            }
        },
    ],
)
def test_identifiers_duplicates_and_capability_references_are_rejected(change) -> None:
    with pytest.raises(ValidationError):
        CoreConfig.model_validate({**minimal_config(), **change})


def test_metering_requires_complete_valid_quotas_and_explicit_suite() -> None:
    payload = minimal_config()
    payload["features"] = {"meteredUsage": True}
    payload["usagePolicy"] = {
        "meter": "api_calls",
        "quotasByPlan": {"free": "100"},
        "quotaBoundary": "deny_above",
        "planChangeTreatment": "preserve_period_usage",
    }
    with pytest.raises(ValidationError, match="usage_reference"):
        CoreConfig.model_validate(payload)
    payload["suites"] = {"enabled": ["reference_core", "usage_reference"]}
    assert CoreConfig.model_validate(payload).features.metered_usage
    payload["usagePolicy"]["quotasByPlan"] = {"free": "NaN"}
    with pytest.raises(ValidationError, match="finite non-negative"):
        CoreConfig.model_validate(payload)


@pytest.mark.parametrize("path", ["/tmp/results", "../results", ".", ""])
def test_artifact_directory_must_remain_inside_workspace(path: str) -> None:
    with pytest.raises(ValidationError, match="workspace-relative"):
        CoreConfig.model_validate({**minimal_config(), "artifactDirectory": path})
