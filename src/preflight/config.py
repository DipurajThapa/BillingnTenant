"""Strict core configuration and suite resolution."""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, ValidationError, model_validator

from preflight.models import StrictModel

SUITES = (
    "tenant_reference",
    "rbac_reference",
    "billing_reference",
    "webhook_reference",
    "entitlement_reference",
    "usage_reference",
)


class Features(StrictModel):
    multi_org_users: bool = True
    membership_management: bool = True
    seat_billing: bool = False
    metered_usage: bool = False


class Execution(StrictModel):
    max_concurrency: int = Field(default=4, ge=1, le=4)
    interrupt_grace_seconds: int = Field(default=10, ge=1, le=60)


class Suites(StrictModel):
    enabled: list[str] = Field(default_factory=lambda: ["reference_core"])


class Policy(StrictModel):
    fail_medium: bool = False


class BillingPolicy(StrictModel):
    trial_plan: str
    trial_days: int = Field(ge=1, le=365)
    trial_end_behavior: Literal["inactive", "free", "active_selected_plan"] = "inactive"
    past_due_behavior: Literal["immediate_suspend", "grace_period", "retain_access"] = (
        "grace_period"
    )
    grace_period_seconds: int = Field(default=259200, ge=0, le=2592000)
    upgrade_effective: Literal["immediate", "period_end"] = "immediate"
    downgrade_effective: Literal["immediate", "period_end"] = "period_end"
    cancel_behavior: Literal["immediate", "end_of_period"] = "end_of_period"
    reactivation_behavior: Literal["restore_selected_plan", "require_new_subscription"] = (
        "restore_selected_plan"
    )
    unknown_plan_entitlements: list[str] = Field(default_factory=list)


class Consistency(StrictModel):
    authorization_propagation_ticks: int = Field(default=1, ge=0, le=100)
    billing_convergence_ticks: int = Field(default=3, ge=0, le=100)


class UsagePolicy(StrictModel):
    meter: str
    quotas_by_plan: dict[str, str]
    quota_boundary: Literal["deny_above"] = "deny_above"
    plan_change_treatment: Literal["preserve_period_usage"] = "preserve_period_usage"


class SeatPolicy(StrictModel):
    minimum_quantity: int = Field(default=1, ge=0)
    pending_invitations_count: bool = False


class CoreConfig(StrictModel):
    schema_version: Literal["1.0"]
    profile: Literal["reference"]
    project_label: str = Field(pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{2,63}$")
    artifact_directory: str = ".preflight/runs"
    features: Features = Field(default_factory=Features)
    roles: list[str] = Field(min_length=1, max_length=20)
    role_permissions: dict[str, list[str]]
    plans: dict[str, dict[str, list[str]]] = Field(max_length=20)
    capabilities: dict[str, dict[str, str | None]] = Field(max_length=100)
    billing_policy: BillingPolicy
    consistency: Consistency = Field(default_factory=Consistency)
    usage_policy: UsagePolicy | None = None
    seat_policy: SeatPolicy | None = None
    suites: Suites = Field(default_factory=Suites)
    execution: Execution = Field(default_factory=Execution)
    policy: Policy = Field(default_factory=Policy)

    @model_validator(mode="after")
    def cross_references(self) -> "CoreConfig":
        if set(self.role_permissions) != set(self.roles):
            raise ValueError("rolePermissions keys must exactly match roles")
        if self.billing_policy.trial_plan not in self.plans:
            raise ValueError("trial plan must exist")
        if self.billing_policy.trial_end_behavior == "free" and "free" not in self.plans:
            raise ValueError("free trial end requires free plan")
        if self.features.metered_usage != (self.usage_policy is not None):
            raise ValueError("meteredUsage and usagePolicy must be enabled together")
        if self.features.seat_billing != (self.seat_policy is not None):
            raise ValueError("seatBilling and seatPolicy must be enabled together")
        resolve_suites(self.suites.enabled, self.features.metered_usage)
        return self


def resolve_suites(values: list[str], metered_usage: bool = False) -> list[str]:
    expanded: list[str] = []
    for value in values:
        names = SUITES[:5] if value == "reference_core" else (value,)
        for name in names:
            if name not in SUITES:
                raise ValueError("CORE_EXTERNAL_NOT_ENABLED")
            if name == "usage_reference" and not metered_usage:
                raise ValueError("usage_reference requires meteredUsage")
            if name not in expanded:
                expanded.append(name)
    return sorted(expanded, key=SUITES.index)


def load_config(path: Path) -> CoreConfig:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError("root must be a mapping")
        return CoreConfig.model_validate(raw)
    except (OSError, yaml.YAMLError, ValidationError, ValueError) as exc:
        raise ValueError(f"CFG_INVALID: {exc}") from None


def example_config() -> CoreConfig:
    return CoreConfig(
        schemaVersion="1.0",
        profile="reference",
        projectLabel="sample-saas",
        roles=["owner", "admin", "member"],
        rolePermissions={
            "owner": ["billing_settings", "member_management", "export"],
            "admin": ["billing_settings", "member_management", "export"],
            "member": ["export"],
        },
        plans={
            "free": {"entitlements": ["dashboard"]},
            "pro": {"entitlements": ["dashboard", "export", "generation"]},
        },
        capabilities={
            "export": {"requiredPermission": "export", "requiredEntitlement": "export"},
            "billing_settings": {
                "requiredPermission": "billing_settings",
                "requiredEntitlement": None,
            },
        },
        billingPolicy={"trialPlan": "pro", "trialDays": 14},
    )
