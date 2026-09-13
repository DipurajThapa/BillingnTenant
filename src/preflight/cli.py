"""Reference-only command line workflows."""

import json
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
def init(force: bool = False) -> None:
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
def run(suite: Annotated[list[str] | None, typer.Option("--suite")] = None) -> None:
    try:
        cfg = load_config(Path(".preflight/core.yml"))
        result = execute(cfg, suites=suite or None)
        location = write_artifacts(result, Path(cfg.artifact_directory))
        typer.echo(f"{result.gate_status} reference {result.run_id} {location}")
        raise typer.Exit(1 if result.gate_status == "FAIL" else 0)
    except ValueError as exc:
        typer.echo(f"INCOMPLETE {exc}", err=True)
        raise typer.Exit(2) from None


@app.command()
def report(run_json: Path) -> None:
    try:
        result = RunResult.model_validate_json(run_json.read_text(encoding="utf-8"))
        run_json.with_name("preflight-report.html").write_text(
            render_html(result), encoding="utf-8"
        )
    except Exception as exc:
        typer.echo(f"RPT_SCHEMA_INVALID: {type(exc).__name__}", err=True)
        raise typer.Exit(2) from None


@app.command()
def clean(run_id: str) -> None:
    journal = Path(".preflight/runs") / run_id / "journal.jsonl"
    if not journal.exists():
        typer.echo("CLN_JOURNAL_INVALID", err=True)
        raise typer.Exit(2)
    typer.echo("completed; reference fixtures already absent")


def main() -> None:
    app()
