"""Lifecycle, deterministic assertions, findings, gates, and artifacts."""

import hashlib
import html as html_lib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

from preflight import __version__
from preflight.catalog import selected
from preflight.config import CoreConfig, resolve_suites
from preflight.models import ComponentProvenance, Finding, RunResult, RunSummary, ScenarioResult
from preflight.reference import ReferenceTarget

UNVERIFIED = [
    "stripe",
    "supabase",
    "remote_http",
    "github_actions",
    "formal_accessibility",
    "cpanel",
]


def calculate_gate(results: list[ScenarioResult], fail_medium: bool = False) -> str:
    failures = [x for x in results if x.status == "failed"]
    if any(x.severity in {"blocker", "high"} for x in failures) or (fail_medium and failures):
        return "FAIL"
    return "WARN" if failures else "PASS"


def execute(
    config: CoreConfig,
    target: ReferenceTarget | None = None,
    suites: list[str] | None = None,
    fail_fast: bool = False,
) -> RunResult:
    target = target or ReferenceTarget()
    chosen = resolve_suites(suites or config.suites.enabled, config.features.metered_usage)
    started = datetime.now(UTC)
    rows: list[ScenarioResult] = []
    findings: list[Finding] = []
    for scenario in selected(chosen):
        try:
            passed, observed = target.evaluate(scenario.id)
        except Exception:
            rows.append(
                ScenarioResult(
                    testId=scenario.id,
                    suite=scenario.suite,
                    severity=scenario.severity,
                    applicability="required",
                    status="error",
                    durationMs=0,
                    expected="reference oracle satisfied",
                    observed="observation unavailable",
                    errorCode="SCN_UNEXPECTED",
                )
            )
            if fail_fast:
                break
            continue
        finding_id = None if passed else f"F-{scenario.id}"
        row = ScenarioResult(
            testId=scenario.id,
            suite=scenario.suite,
            severity=scenario.severity,
            applicability="required",
            status="passed" if passed else "failed",
            durationMs=0,
            expected="reference oracle satisfied",
            observed=observed,
            findingId=finding_id,
        )
        rows.append(row)
        if finding_id:
            findings.append(
                Finding(
                    id=finding_id,
                    scenarioId=scenario.id,
                    severity=scenario.severity,
                    impact="Reference defect detected",
                    expected=row.expected,
                    observed=observed,
                    reproductionSteps=[f"run {scenario.id} against reference target"],
                    remediationHint="Correct the behavior represented by the defect toggle",
                )
            )
    assertion = calculate_gate(rows)
    missing = [x.id for x in selected(chosen) if x.id not in {row.test_id for row in rows}]
    cleanup_status = "completed"
    try:
        target.cleanup()
    except Exception:
        cleanup_status = "failed"
    incomplete = bool(
        missing or any(x.status == "error" for x in rows) or cleanup_status == "failed"
    )
    summary = RunSummary(
        passed=sum(x.status == "passed" for x in rows),
        failed=sum(x.status == "failed" for x in rows),
        skipped=0,
        error=sum(x.status == "error" for x in rows),
        findings=len(findings),
    )
    config_json = json.dumps(config.model_dump(mode="json", by_alias=True), sort_keys=True)
    return RunResult(
        runId=uuid.uuid4().hex,
        toolVersion=__version__,
        catalogVersion="1.0",
        executionProfile="reference",
        verificationLevel="integration_incomplete" if incomplete else "reference_verified",
        components=[ComponentProvenance(name="bundled-reference", version="1.0", kind="reference")],
        verifiedScopes=chosen,
        unverifiedScopes=UNVERIFIED,
        startedAt=started,
        finishedAt=datetime.now(UTC),
        configHash=hashlib.sha256(config_json.encode()).hexdigest(),
        selectedSuites=chosen,
        executionStatus="error" if incomplete else "completed",
        assertionGateStatus=assertion,
        gateStatus="INCOMPLETE" if incomplete else assertion,
        cleanupStatus=cleanup_status,
        summary=summary,
        results=rows,
        findings=findings,
        missingCoverage=missing,
        diagnostics=["SCN_UNEXPECTED"]
        if any(x.status == "error" for x in rows)
        else (["CLN_FAILED"] if cleanup_status == "failed" else []),
    )


def write_artifacts(result: RunResult, root: Path) -> Path:
    run_dir = root / result.run_id
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    data = result.model_dump(mode="json", by_alias=True)
    (run_dir / "run.json").write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    report = render_html(result)
    (run_dir / "preflight-report.html").write_text(report, encoding="utf-8")
    (run_dir / "journal.jsonl").write_text(
        json.dumps(
            {"schemaVersion": "1.0", "runId": result.run_id, "sequence": 1, "event": "run_created"}
        )
        + "\n",
        encoding="utf-8",
    )
    return run_dir


def render_html(result: RunResult) -> str:
    rows = "".join(
        f"<tr><td>{html_lib.escape(x.test_id)}</td><td>{html_lib.escape(x.status.upper())}</td></tr>"
        for x in result.results
    )
    html = f"""<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width"><title>Preflight {result.gate_status}</title>
<style>body{{font:16px system-ui;margin:auto;max-width:1120px;padding:1rem}}
table{{width:100%;border-collapse:collapse}}td,th{{padding:.5rem;border:1px solid #bbb}}
@media(max-width:600px){{body{{font-size:14px}}table{{display:block;overflow:auto}}}}</style>
<body><header><h1>SaaS Preflight: {result.gate_status}</h1>
<strong>Reference verification only. No external provider or customer environment
was tested.</strong>
</header><main><h2>Provenance</h2><p>Profile: reference</p><h2>Coverage</h2>
<table><thead><tr><th>Scenario</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
</main></body></html>"""
    return html
