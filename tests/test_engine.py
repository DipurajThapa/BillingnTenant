import json
from pathlib import Path

from preflight.catalog import CATALOG
from preflight.config import example_config
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
    assert "stripe" in result.unverified_scopes
    assert all(x.kind == "reference" for x in result.components)


def test_each_core_defect_is_detected_by_its_scenario() -> None:
    for scenario in CATALOG:
        if scenario.suite == "usage_reference":
            continue
        result = execute(example_config(), ReferenceTarget(defects={scenario.id}))
        failed = [x.test_id for x in result.results if x.status == "failed"]
        assert failed == [scenario.id]
        assert result.gate_status == "FAIL"


def test_artifacts_are_valid_offline_and_reference_only(tmp_path: Path) -> None:
    result = execute(example_config())
    location = write_artifacts(result, tmp_path)
    data = json.loads((location / "run.json").read_text())
    html = (location / "preflight-report.html").read_text()
    assert data["runId"] == result.run_id
    assert "Reference verification only" in html
    assert "http://" not in html and "https://" not in html
    assert (location / "journal.jsonl").exists()


def test_runtime_and_cleanup_failures_are_incomplete() -> None:
    runtime = execute(example_config(), ReferenceTarget(errors={"TEN-001"}))
    assert runtime.gate_status == "INCOMPLETE"
    assert runtime.verification_level == "integration_incomplete"
    assert runtime.summary.error == 1
    cleanup = execute(example_config(), ReferenceTarget(cleanup_error=True))
    assert cleanup.gate_status == "INCOMPLETE"
    assert cleanup.cleanup_status == "failed"


def test_fail_fast_preserves_missing_coverage() -> None:
    result = execute(example_config(), ReferenceTarget(errors={"TEN-001"}), fail_fast=True)
    assert result.gate_status == "INCOMPLETE"
    assert result.missing_coverage
