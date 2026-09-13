"""Reference-only command line workflows."""

import json
import re
from pathlib import Path
from typing import Annotated

import typer
import yaml

from preflight import __version__
from preflight.catalog import CATALOG
from preflight.config import example_config, load_config
from preflight.engine import execute, render_html, write_artifacts
from preflight.models import RunResult

app = typer.Typer(no_args_is_help=True)


@app.callback()
def root() -> None:
    """Run deterministic SaaS preflight checks."""


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command()
def init(
    force: bool = False,
    non_interactive: bool = typer.Option(False, "--non-interactive"),
) -> None:
    """Create the deterministic reference configuration.

    ``--non-interactive`` makes the overwrite rule explicit for automation. The
    current initializer has no prompts, so new-project output is identical in
    either mode.
    """
    del non_interactive
    path = Path(".preflight/core.yml")
    if path.exists() and not force:
        typer.echo("CFG_INVALID: configuration exists; use --force", err=True)
        raise typer.Exit(2)
    path.parent.mkdir(parents=True, exist_ok=True)
    content = yaml.safe_dump(
        example_config().model_dump(mode="json", by_alias=True), sort_keys=False
    )
    temp = path.with_suffix(".tmp")
    temp.write_text(content, encoding="utf-8")
    load_config(temp)
    temp.replace(path)
    typer.echo(str(path))


@app.command()
def doctor(ci: bool = False) -> None:
    try:
        cfg = load_config(Path(".preflight/core.yml"))
        typer.echo(f"PASS CORE_CONFIG_VALID profile={cfg.profile}" if ci else "PASS configuration")
    except ValueError as exc:
        typer.echo(f"FAIL {exc}", err=True)
        raise typer.Exit(2) from None


@app.command("catalog")
def show_catalog(
    suite: str | None = None, json_output: bool = typer.Option(False, "--json")
) -> None:
    rows = [x for x in CATALOG if suite is None or x.suite == suite]
    if suite and not rows:
        raise typer.BadParameter("unknown suite")
    if json_output:
        typer.echo(json.dumps([x.__dict__ for x in rows], sort_keys=True))
    else:
        for item in rows:
            typer.echo(f"{item.id} {item.severity.upper()} {item.suite}")


@app.command()
def run(
    suite: Annotated[list[str] | None, typer.Option("--suite")] = None,
    fail_fast: bool = typer.Option(False, "--fail-fast"),
    ci: bool = typer.Option(False, "--ci"),
) -> None:
    try:
        cfg = load_config(Path(".preflight/core.yml"))
        result = execute(cfg, suites=suite or None, fail_fast=fail_fast)
        location = write_artifacts(result, Path(cfg.artifact_directory))
        for row in result.results:
            typer.echo(f"{row.status.upper()} {row.test_id} severity={row.severity}")
        typer.echo(
            "COUNTS "
            f"passed={result.summary.passed} failed={result.summary.failed} "
            f"skipped={result.summary.skipped} error={result.summary.error} "
            f"findings={result.summary.findings}"
        )
        typer.echo(
            f"DECISION assertion={result.assertion_gate_status} final={result.gate_status} "
            f"cleanup={result.cleanup_status}"
        )
        prefix = "PREFLIGHT_RESULT" if ci else result.gate_status
        typer.echo(
            f"{prefix} gate={result.gate_status} profile=reference "
            f"run_id={result.run_id} artifact={location}"
        )
        if result.gate_status == "INCOMPLETE":
            raise typer.Exit(2)
        raise typer.Exit(1 if result.gate_status == "FAIL" else 0)
    except ValueError as exc:
        typer.echo(f"INCOMPLETE {exc}", err=True)
        raise typer.Exit(2) from None


@app.command()
def report(run_json: Path) -> None:
    try:
        result = RunResult.model_validate_json(run_json.read_text(encoding="utf-8"))
        output = run_json.with_name("preflight-report.html")
        temp = output.with_suffix(".tmp")
        temp.write_text(render_html(result), encoding="utf-8")
        temp.replace(output)
    except Exception as exc:
        temp = run_json.with_name("preflight-report.tmp")
        if temp.exists():
            temp.unlink()
        typer.echo(f"RPT_SCHEMA_INVALID: {type(exc).__name__}", err=True)
        raise typer.Exit(2) from None


@app.command()
def clean(run_id: str) -> None:
    if not re.fullmatch(r"[0-9a-f]{32}", run_id):
        typer.echo("CLN_JOURNAL_INVALID", err=True)
        raise typer.Exit(2)
    journal = Path(".preflight/runs") / run_id / "journal.jsonl"
    if not journal.exists():
        typer.echo("CLN_JOURNAL_INVALID", err=True)
        raise typer.Exit(2)
    try:
        entries = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
        if not entries:
            raise ValueError
        for sequence, entry in enumerate(entries, start=1):
            if (
                entry.get("schemaVersion") != "1.0"
                or entry.get("runId") != run_id
                or entry.get("sequence") != sequence
                or entry.get("adapterKind") != "reference"
            ):
                raise ValueError
    except (OSError, ValueError, json.JSONDecodeError):
        typer.echo("CLN_JOURNAL_INVALID", err=True)
        raise typer.Exit(2) from None
    typer.echo("completed; reference fixtures already absent")


def main() -> None:
    app()
