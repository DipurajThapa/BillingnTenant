from pathlib import Path

import yaml


def test_traceability_is_unique_and_nonempty() -> None:
    data = yaml.safe_load(Path("tests/traceability.yml").read_text())
    assert data["schemaVersion"] == "1.0"
    entries = data["entries"]
    ids = [x["requirementId"] for x in entries]
    assert len(ids) == len(set(ids))
    assert all(x["testIds"] and x["acceptanceIds"] for x in entries)
