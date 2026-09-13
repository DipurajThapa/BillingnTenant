"""Lifecycle, deterministic assertions, findings, gates, and artifacts."""

import hashlib
import html as html_lib
import json
import os
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
    if any(x.severity in {"blocker", "high"} for x in failures) or (
        fail_medium and any(x.severity == "medium" for x in failures)
    ):
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
        if scenario.feature_guard and not getattr(config.features, scenario.feature_guard):
            rows.append(
                ScenarioResult(
                    testId=scenario.id,
                    suite=scenario.suite,
                    severity=scenario.severity,
                    applicability="conditional",
                    status="skipped",
                    durationMs=0,
                    expected="feature-gated reference oracle satisfied when enabled",
                    observed="feature disabled",
                    skipReason="feature_absent",
                )
            )
            continue
        try:
            passed, observed = target.evaluate(scenario.id)
        except Exception:
            rows.append(
                ScenarioResult(
                    testId=scenario.id,
                    suite=scenario.suite,
                    severity=scenario.severity,
                    applicability=scenario.coverage,
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
            applicability=scenario.coverage,
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
    assertion = calculate_gate(rows, config.policy.fail_medium)
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
        skipped=sum(x.status == "skipped" for x in rows),
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
    data = result.model_dump(mode="json", by_alias=True)
    serialized = json.dumps(data, indent=2, sort_keys=True)
    if len(serialized.encode("utf-8")) > 10 * 1024 * 1024:
        raise ValueError("RPT_RENDER_FAILED: JSON artifact exceeds 10 MiB")
    report = render_html(result)
    workspace = Path.cwd().resolve()
    resolved_root = root.resolve()
    if not resolved_root.is_relative_to(workspace):
        raise ValueError("RPT_RENDER_FAILED: artifact directory escapes workspace")
    run_dir = resolved_root / result.run_id
    run_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    run_json = run_dir / "run.json"
    html_report = run_dir / "preflight-report.html"
    journal = run_dir / "journal.jsonl"
    run_json.write_text(serialized, encoding="utf-8")
    html_report.write_text(report, encoding="utf-8")
    journal.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "runId": result.run_id,
                "sequence": 1,
                "event": "run_created",
                "adapterKind": "reference",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if os.name == "posix":
        for path in (run_json, html_report, journal):
            path.chmod(0o600)
    try:
        return run_dir.relative_to(workspace)
    except ValueError:
        return run_dir


def render_html(result: RunResult) -> str:
    rows = "".join(
        "<tr>"
        f"<th scope='row'><code>{html_lib.escape(x.test_id)}</code></th>"
        f"<td><span class='status status-{html_lib.escape(x.status)}'>"
        f"{html_lib.escape(x.status.upper())}</span></td>"
        f"<td>{html_lib.escape(x.severity.upper())}</td>"
        f"<td>{html_lib.escape(x.expected)}</td>"
        f"<td>{html_lib.escape(x.observed)}</td>"
        "</tr>"
        for x in result.results
    )
    findings = (
        "".join(
            "<article class='finding'>"
            f"<h3>{html_lib.escape(item.id)}: {html_lib.escape(item.severity.upper())}</h3>"
            f"<p><strong>Impact:</strong> {html_lib.escape(item.impact)}</p>"
            f"<p><strong>Expected:</strong> {html_lib.escape(item.expected)}</p>"
            f"<p><strong>Observed:</strong> {html_lib.escape(item.observed)}</p>"
            f"<p><strong>Remediation:</strong> {html_lib.escape(item.remediation_hint)}</p>"
            "</article>"
            for item in result.findings
        )
        or "<p>No findings.</p>"
    )
    incomplete_causes = sorted(
        set(result.missing_coverage)
        | {row.error_code for row in result.results if row.error_code}
        | set(result.diagnostics)
    )
    incomplete = (
        "<ul>"
        + "".join(f"<li><code>{html_lib.escape(value)}</code></li>" for value in incomplete_causes)
        + "</ul>"
        if incomplete_causes
        else "<p>None.</p>"
    )
    cleanup_notice = (
        "<p class='scope'><strong>Cleanup requires attention.</strong> "
        f"Run <code>preflight clean {html_lib.escape(result.run_id)}</code>.</p>"
        if result.cleanup_status in {"partial", "failed"}
        else "<p>Reference cleanup completed.</p>"
    )
    components = html_lib.escape(", ".join(f"{x.name} {x.version}" for x in result.components))
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
<dt>Cleanup</dt><dd>{html_lib.escape(result.cleanup_status)}</dd>
<dt>Suites</dt><dd>{html_lib.escape(", ".join(result.selected_suites))}</dd>
<dt>Components</dt><dd>{components}</dd>
</dl></section>
<section aria-labelledby="counts-heading"><h2 id="counts-heading">Decision summary</h2><dl>
<dt>Passed</dt><dd>{result.summary.passed}</dd><dt>Failed</dt><dd>{result.summary.failed}</dd>
<dt>Skipped</dt><dd>{result.summary.skipped}</dd><dt>Error</dt><dd>{result.summary.error}</dd>
<dt>Findings</dt><dd>{result.summary.findings}</dd></dl></section>
<section aria-labelledby="incomplete-heading"><h2 id="incomplete-heading">Incomplete causes</h2>
{incomplete}</section>
<section aria-labelledby="findings-heading"><h2 id="findings-heading">Findings</h2>
{findings}</section>
<section aria-labelledby="coverage-heading"><h2 id="coverage-heading">Scenario coverage</h2>
<div class="table-wrap" role="region" aria-labelledby="coverage-heading" tabindex="0">
<table><caption>Selected scenario results</caption><thead><tr>
<th scope="col">Scenario</th><th scope="col">Status</th><th scope="col">Severity</th>
<th scope="col">Expected</th><th scope="col">Observed</th>
</tr></thead><tbody>{rows}</tbody></table></div></section>
<section aria-labelledby="cleanup-heading"><h2 id="cleanup-heading">Fixture and cleanup</h2>
{cleanup_notice}</section>
<section aria-labelledby="limits-heading"><h2 id="limits-heading">Limitations</h2>
<p>Unverified scopes: {html_lib.escape(", ".join(result.unverified_scopes))}.</p>
<p>This result does not establish penetration-test, compliance, production-hosting,
or formal accessibility conformance.</p>
</section></main>
<footer><p>Generated by SaaS Preflight {html_lib.escape(result.tool_version)}.</p></footer>
</div></body></html>"""
    return html
