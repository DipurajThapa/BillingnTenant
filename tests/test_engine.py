import json
import os
from pathlib import Path

import pytest

from preflight.catalog import CATALOG
from preflight.config import CoreConfig, example_config
from preflight.engine import execute, write_artifacts
from preflight.reference import ReferenceTarget


def test_catalog_has_all_42_stable_scenarios() -> None:
    assert len(CATALOG) == 42
    assert len({x.id for x in CATALOG}) == 42


def test_reference_core_passes_with_explicit_provenance() -> None:
    result = execute(example_config())
    assert result.gate_status == "PASS"
    assert result.verification_level == "reference_verified"
    assert len(result.results) == 36
    assert result.summary.skipped == 1
    seat_result = next(x for x in result.results if x.test_id == "BILL-011")
    assert seat_result.skip_reason == "feature_absent"
    assert "stripe" in result.unverified_scopes
    assert all(x.kind == "reference" for x in result.components)


def all_features_config() -> CoreConfig:
    payload = example_config().model_dump(mode="json", by_alias=True)
    payload["features"]["seatBilling"] = True
    payload["features"]["meteredUsage"] = True
    payload["seatPolicy"] = {"minimumQuantity": 1, "pendingInvitationsCount": False}
    payload["usagePolicy"] = {
        "meter": "api_calls",
        "quotasByPlan": {plan: "100" for plan in payload["plans"]},
        "quotaBoundary": "deny_above",
        "planChangeTreatment": "preserve_period_usage",
    }
    payload["suites"]["enabled"] = ["reference_core", "usage_reference"]
    return CoreConfig.model_validate(payload)


def test_each_reference_defect_is_detected_only_by_its_scenario() -> None:
    config = all_features_config()
    correct = execute(config)
    assert len(correct.results) == 42
    assert correct.summary.skipped == 0
    assert correct.gate_status == "PASS"
    for scenario in CATALOG:
        result = execute(config, ReferenceTarget(defects={scenario.id}))
        failed = [x.test_id for x in result.results if x.status == "failed"]
        assert failed == [scenario.id]
        assert result.gate_status == ("WARN" if scenario.severity == "medium" else "FAIL")


def test_feature_gates_and_medium_promotion_follow_configuration() -> None:
    config = example_config()
    config.features.multi_org_users = False
    config.features.membership_management = False
    result = execute(config)
    skipped = {x.test_id for x in result.results if x.status == "skipped"}
    assert skipped == {"TEN-006", "TEN-007", "RBAC-004", "RBAC-005", "BILL-010", "BILL-011"}
    assert result.gate_status == "PASS"

    medium = execute(example_config(), ReferenceTarget(defects={"RBAC-004"}))
    assert medium.assertion_gate_status == "WARN"
    promoted_config = example_config()
    promoted_config.policy.fail_medium = True
    promoted = execute(promoted_config, ReferenceTarget(defects={"RBAC-004"}))
    assert promoted.assertion_gate_status == "FAIL"


def test_alternative_billing_policies_keep_reference_oracles_valid() -> None:
    payload = all_features_config().model_dump(mode="json", by_alias=True)
    payload["billingPolicy"].update(
        {
            "trialEndBehavior": "free",
            "pastDueBehavior": "immediate_suspend",
            "gracePeriodSeconds": 0,
            "upgradeEffective": "period_end",
            "downgradeEffective": "immediate",
            "cancelBehavior": "immediate",
            "reactivationBehavior": "require_new_subscription",
        }
    )
    result = execute(CoreConfig.model_validate(payload), suites=["billing_reference"])
    assert result.gate_status == "PASS"
    assert result.summary.passed == 12


def test_artifacts_are_valid_offline_and_reference_only(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = execute(example_config())
    location = write_artifacts(result, Path("artifacts"))
    data = json.loads((location / "run.json").read_text())
    html = (location / "preflight-report.html").read_text()
    assert data["runId"] == result.run_id
    assert "Reference verification only" in html
    assert "http://" not in html and "https://" not in html
    assert (location / "journal.jsonl").exists()
    if os.name == "posix":
        assert (location.stat().st_mode & 0o777) == 0o700
        assert (location / "run.json").stat().st_mode & 0o777 == 0o600


def test_runtime_and_cleanup_failures_are_incomplete() -> None:
    runtime = execute(example_config(), ReferenceTarget(errors={"TEN-001"}))
    assert runtime.gate_status == "INCOMPLETE"
    assert runtime.verification_level == "integration_incomplete"
    assert runtime.summary.error == 1
    cleanup = execute(example_config(), ReferenceTarget(cleanup_error=True))
    assert cleanup.gate_status == "INCOMPLETE"
    assert cleanup.cleanup_status == "failed"


def test_artifact_writer_rejects_symlink_escape(tmp_path: Path, monkeypatch) -> None:
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (workspace / "escape").symlink_to(outside, target_is_directory=True)
    monkeypatch.chdir(workspace)
    with pytest.raises(ValueError, match="escapes workspace"):
        write_artifacts(execute(example_config()), Path("escape"))


def test_fail_fast_preserves_missing_coverage() -> None:
    result = execute(example_config(), ReferenceTarget(errors={"TEN-001"}), fail_fast=True)
    assert result.gate_status == "INCOMPLETE"
    assert result.missing_coverage


def test_artifact_write_failure_leaves_no_partial_run(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = execute(example_config())
    original_write = Path.write_text

    def fail_html(self, *args, **kwargs):
        if self.name == "preflight-report.html":
            raise OSError("simulated reporter failure")
        return original_write(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_html)
    with pytest.raises(OSError, match="reporter failure"):
        write_artifacts(result, Path("artifacts"))
    assert not (Path("artifacts") / result.run_id).exists()
    assert not (Path("artifacts") / f".{result.run_id}.tmp").exists()
