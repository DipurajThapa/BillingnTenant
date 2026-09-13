import json
from pathlib import Path

from typer.testing import CliRunner

from preflight.cli import app

runner = CliRunner()


def test_end_to_end_cli_workflow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init"]).exit_code == 0
    assert runner.invoke(app, ["init"]).exit_code == 2
    assert runner.invoke(app, ["doctor", "--ci"]).exit_code == 0
    catalog = runner.invoke(app, ["catalog", "--json"])
    assert len(json.loads(catalog.stdout)) == 42
    run = runner.invoke(app, ["run"])
    assert run.exit_code == 0
    run_files = list(Path(".preflight/runs").glob("*/run.json"))
    assert len(run_files) == 1
    assert runner.invoke(app, ["report", str(run_files[0])]).exit_code == 0
    run_id = run_files[0].parent.name
    assert runner.invoke(app, ["clean", run_id]).exit_code == 0


def test_doctor_invalid_and_report_invalid_are_nonzero(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    Path(".preflight").mkdir()
    Path(".preflight/core.yml").write_text("profile: external\n")
    assert runner.invoke(app, ["doctor"]).exit_code == 2
    Path("bad.json").write_text("{}")
    assert runner.invoke(app, ["report", "bad.json"]).exit_code == 2
