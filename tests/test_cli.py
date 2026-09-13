import json
from pathlib import Path

from typer.testing import CliRunner

from preflight.cli import app

runner = CliRunner()


def test_end_to_end_cli_workflow(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "--non-interactive"]).exit_code == 0
    assert Path(".preflight/reference.yml").exists()
    assert runner.invoke(app, ["init", "--non-interactive"]).exit_code == 2
    assert runner.invoke(app, ["doctor", "--ci"]).exit_code == 0
    doctor = runner.invoke(app, ["doctor", "--ci"])
    assert "PASS CORE_PORTS_VALID ports=7" in doctor.stdout
    catalog = runner.invoke(app, ["catalog", "--json"])
    catalog_rows = json.loads(catalog.stdout)
    assert len(catalog_rows) == 42
    assert all(row["title"] and row["port_dependencies"] for row in catalog_rows)
    run = runner.invoke(app, ["run", "--ci"])
    assert run.exit_code == 0
    assert "PREFLIGHT_RESULT gate=PASS profile=reference" in run.stdout
    assert "COUNTS passed=" in run.stdout
    assert "DECISION assertion=PASS final=PASS cleanup=completed" in run.stdout
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
    assert not Path("preflight-report.html").exists()


def test_cli_suite_override_deduplicates_and_fail_fast_option_is_supported(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "--non-interactive"]).exit_code == 0
    result = runner.invoke(
        app,
        [
            "run",
            "--suite",
            "tenant_reference",
            "--suite",
            "tenant_reference",
            "--fail-fast",
        ],
    )
    assert result.exit_code == 0
    run_file = next(Path(".preflight/runs").glob("*/run.json"))
    payload = json.loads(run_file.read_text())
    assert payload["selectedSuites"] == ["tenant_reference"]


def test_clean_rejects_invalid_external_and_wrong_run_journals(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    valid_run = "a" * 32
    run_dir = Path(".preflight/runs") / valid_run
    run_dir.mkdir(parents=True)
    journal = run_dir / "journal.jsonl"

    journal.write_text("not-json\n")
    assert runner.invoke(app, ["clean", valid_run]).exit_code == 2

    journal.write_text(
        json.dumps(
            {
                "schemaVersion": "1.0",
                "runId": valid_run,
                "sequence": 1,
                "event": "run_created",
                "adapterKind": "external",
            }
        )
        + "\n"
    )
    assert runner.invoke(app, ["clean", valid_run]).exit_code == 2

    assert runner.invoke(app, ["clean", "../escape"]).exit_code == 2


def test_interactive_decline_preserves_both_configuration_files(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "--non-interactive"]).exit_code == 0
    before = {path: path.read_bytes() for path in Path(".preflight").glob("*.yml")}
    result = runner.invoke(app, ["init"], input="n\n")
    assert result.exit_code == 0
    assert "cancelled; no files changed" in result.stdout
    assert {path: path.read_bytes() for path in Path(".preflight").glob("*.yml")} == before


def test_force_initialization_rolls_back_both_files_if_commit_fails(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert runner.invoke(app, ["init", "--non-interactive"]).exit_code == 0
    core = Path(".preflight/core.yml")
    reference = Path(".preflight/reference.yml")
    core.write_text("original-core")
    reference.write_text("original-reference")
    original_replace = Path.replace

    def fail_second_replace(self, target):
        if Path(target).name == "reference.yml":
            raise OSError("simulated commit failure")
        return original_replace(self, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)
    result = runner.invoke(app, ["init", "--force", "--non-interactive"])
    assert result.exit_code == 2
    assert core.read_text() == "original-core"
    assert reference.read_text() == "original-reference"
    assert not list(Path(".preflight").glob("*.tmp"))
