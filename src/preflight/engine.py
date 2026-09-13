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
        "<tr>"
        f"<th scope='row'><code>{html_lib.escape(x.test_id)}</code></th>"
        f"<td><span class='status status-{html_lib.escape(x.status)}'>"
        f"{html_lib.escape(x.status.upper())}</span></td>"
        f"<td>{html_lib.escape(x.severity.upper())}</td>"
        "</tr>"
        for x in result.results
    )
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>SaaS Preflight result: {result.gate_status}</title>
<style>
:root{{color-scheme:light dark;--bg:#fff;--text:#172033;--muted:#475569;--border:#64748b;
--focus:#005fcc;--pass:#176b3a;--fail:#a51d2d;--warn:#7a4b00}}
*{{box-sizing:border-box}}html{{font-size:100%}}body{{background:var(--bg);color:var(--text);
font:1rem/1.6 system-ui,sans-serif;margin:0}}.page{{margin:auto;max-width:70rem;padding:1.25rem}}
.skip{{background:#fff;color:#000;left:.5rem;padding:.75rem;position:absolute;top:-5rem;z-index:2}}
.skip:focus{{top:.5rem}}
a:focus-visible,summary:focus-visible,.table-wrap:focus-visible{{
outline:.2rem solid var(--focus);
outline-offset:.2rem}}.scope{{border:.15rem solid var(--warn);padding:1rem}}
.decision{{font-size:1.5rem;font-weight:700}}dl{{display:grid;grid-template-columns:max-content 1fr;
gap:.35rem 1rem}}dt{{font-weight:700}}dd{{margin:0}}.table-wrap{{overflow-x:auto}}
table{{border-collapse:collapse;width:100%}}
caption{{font-weight:700;text-align:left;padding:.5rem 0}}
td,th{{border:.0625rem solid var(--border);padding:.65rem;text-align:left;vertical-align:top}}
.status{{font-weight:700}}.status-passed{{color:var(--pass)}}.status-failed,.status-error{{color:var(--fail)}}
.status-skipped{{color:var(--warn)}}code{{overflow-wrap:anywhere}}footer{{color:var(--muted);margin-top:2rem}}
@media(max-width:37.5rem){{.page{{padding:.75rem}}dl{{grid-template-columns:1fr;gap:.1rem}}
dd{{margin-bottom:.6rem}}.table-wrap{{border:.0625rem solid var(--border)}}}}
@media(prefers-contrast:more){{:root{{--border:currentColor}}}}
@media print{{.skip{{display:none}}.page{{max-width:none}}}}
</style></head><body><a class="skip" href="#main">Skip to results</a><div class="page">
<header><h1>SaaS Preflight result</h1><p class="decision">Final gate: {result.gate_status}</p>
<p class="scope"><strong>Reference verification only.</strong>
No external provider or customer environment was tested.</p></header>
<main id="main" tabindex="-1"><section aria-labelledby="provenance-heading">
<h2 id="provenance-heading">Run provenance</h2><dl>
<dt>Run ID</dt><dd><code>{html_lib.escape(result.run_id)}</code></dd>
<dt>Profile</dt><dd>{html_lib.escape(result.execution_profile)}</dd>
<dt>Verification</dt><dd>{html_lib.escape(result.verification_level)}</dd>
<dt>Assertion gate</dt><dd>{html_lib.escape(result.assertion_gate_status)}</dd>
<dt>Cleanup</dt><dd>{html_lib.escape(result.cleanup_status)}</dd></dl></section>
<section aria-labelledby="coverage-heading"><h2 id="coverage-heading">Scenario coverage</h2>
<div class="table-wrap" role="region" aria-labelledby="coverage-heading" tabindex="0">
<table><caption>Selected scenario results</caption><thead><tr>
<th scope="col">Scenario</th><th scope="col">Status</th><th scope="col">Severity</th>
</tr></thead><tbody>{rows}</tbody></table></div></section></main>
<footer><p>Generated by SaaS Preflight {html_lib.escape(result.tool_version)}.</p></footer>
</div></body></html>"""
    return html
