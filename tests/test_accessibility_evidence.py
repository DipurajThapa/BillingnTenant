import hashlib
from pathlib import Path

import pytest
import yaml

from preflight.accessibility import contrast_ratio, validate_manual_evidence


def valid_evidence(report: Path) -> dict[str, object]:
    checks = [
        {"id": f"A11Y-MAN-{number:03d}", "status": "pass", "notes": "verified"}
        for number in range(1, 11)
    ]
    return {
        "schemaVersion": "1.0",
        "reportSha256": hashlib.sha256(report.read_bytes()).hexdigest(),
        "testedAt": "2026-09-13T20:00:00Z",
        "reviewer": "Test Reviewer",
        "environments": [
            {
                "screenReader": "NVDA",
                "screenReaderVersion": "test",
                "browser": "Chrome",
                "browserVersion": "test",
                "operatingSystem": "Windows 11 test",
                "checks": checks,
            },
            {
                "screenReader": "Narrator",
                "screenReaderVersion": "test",
                "browser": "Edge",
                "browserVersion": "test",
                "operatingSystem": "Windows 11 test",
                "checks": checks,
            },
        ],
    }


def test_complete_human_evidence_validates_and_is_bound_to_report(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text("<h1>Report</h1>")
    evidence_path = tmp_path / "evidence.yml"
    evidence_path.write_text(yaml.safe_dump(valid_evidence(report)))
    evidence = validate_manual_evidence(evidence_path, report)
    assert len(evidence.environments) == 2

    report.write_text("changed")
    with pytest.raises(ValueError, match="digest does not match"):
        validate_manual_evidence(evidence_path, report)


def test_incomplete_failed_duplicate_or_missing_matrix_is_rejected(tmp_path: Path) -> None:
    report = tmp_path / "report.html"
    report.write_text("report")
    payload = valid_evidence(report)
    payload["environments"][0]["checks"][0]["status"] = "not_run"
    path = tmp_path / "evidence.yml"
    path.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValueError, match="incomplete or failed"):
        validate_manual_evidence(path, report)

    payload = valid_evidence(report)
    payload["environments"][1]["browser"] = "Chrome"
    path.write_text(yaml.safe_dump(payload))
    with pytest.raises(ValueError, match="Narrator/Edge"):
        validate_manual_evidence(path, report)


def test_report_palette_meets_normal_text_contrast_threshold() -> None:
    for color in ("#172033", "#475569", "#176b3a", "#a51d2d", "#7a4b00", "#005fcc"):
        assert contrast_ratio(color, "#ffffff") >= 4.5
