from pathlib import Path

from preflight.config import example_config
from preflight.engine import execute, write_artifacts
from preflight.lifecycle import FixtureJournal, validate_journal
from preflight.reference import ReferenceTarget
from preflight.reference_ports import ReferenceFixturePort


def test_fixture_creation_is_journaled_and_cleanup_is_reverse_order(tmp_path: Path) -> None:
    target = ReferenceTarget()
    journal = FixtureJournal("r" * 32)
    port = ReferenceFixturePort(target, journal)
    fixtures = port.provision(journal.run_id, ["TEN-001", "TEN-002"])
    assert len(target.created_fixture_ids) == 2
    assert [x.fixture_alias for x in journal.entries if x.event == "fixture_registered"] == [
        "TEN-001",
        "TEN-002",
    ]
    port.cleanup(journal.run_id, fixtures)
    assert not target.created_fixture_ids
    assert [x.fixture_alias for x in journal.entries if x.event == "fixture_cleaned"] == [
        "TEN-002",
        "TEN-001",
    ]
    path = tmp_path / "journal.jsonl"
    journal.write(path)
    assert len(validate_journal(path, journal.run_id)) == 7


def test_partial_provisioning_cleans_every_registered_fixture() -> None:
    target = ReferenceTarget(provision_error_at=3)
    result = execute(example_config(), target)
    assert result.execution_status == "error"
    assert result.gate_status == "INCOMPLETE"
    assert result.diagnostics == ["PORT_INVALID_RETURN"]
    assert not target.created_fixture_ids
    assert [x.event for x in result._journal.entries].count("fixture_registered") == 2
    assert [x.event for x in result._journal.entries].count("fixture_cleaned") == 2


def test_keyboard_interrupt_stops_execution_and_still_cleans() -> None:
    class InterruptedTarget(ReferenceTarget):
        def evaluate(self, test_id, config):
            if test_id == "TEN-002":
                raise KeyboardInterrupt
            return super().evaluate(test_id, config)

    target = InterruptedTarget()
    result = execute(example_config(), target, suites=["tenant_reference"])
    assert result.execution_status == "interrupted"
    assert result.gate_status == "INCOMPLETE"
    assert result.diagnostics == ["CORE_INTERRUPTED"]
    assert not target.created_fixture_ids
    assert result.missing_coverage


def test_partial_cleanup_continues_other_exact_deletions() -> None:
    target = ReferenceTarget()
    journal = FixtureJournal("r" * 32)
    port = ReferenceFixturePort(target, journal)
    fixtures = port.provision(journal.run_id, ["one", "two", "three"])
    failed_id = fixtures.resources[1].external_id
    target.cleanup_fixture_fail_ids.add(failed_id)
    try:
        port.cleanup(journal.run_id, fixtures)
    except RuntimeError as exc:
        assert str(exc) == "CLN_PARTIAL"
    else:
        raise AssertionError("partial cleanup must be reported")
    assert target.created_fixture_ids == {failed_id}
    assert [x.event for x in journal.entries].count("fixture_cleaned") == 2
    assert [x.event for x in journal.entries].count("cleanup_failed") == 1


def test_written_run_contains_full_lifecycle_journal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = execute(example_config(), suites=["tenant_reference"])
    run_dir = write_artifacts(result, Path("artifacts"))
    entries = validate_journal(run_dir / "journal.jsonl", result.run_id)
    assert entries[0].event == "run_created"
    assert sum(x.event == "fixture_registered" for x in entries) == 7
    assert sum(x.event == "fixture_cleaned" for x in entries) == 7
