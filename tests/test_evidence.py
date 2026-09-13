from datetime import UTC, datetime

import pytest

from preflight.evidence import sanitize_evidence


def test_evidence_keeps_only_allowlisted_nonsensitive_fields() -> None:
    evidence, diagnostics = sanitize_evidence(
        "TEN-001",
        {"tenantAlias": "TA", "rawBody": "discard", "apiToken": "never-store"},
        {"tenantAlias"},
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert evidence.payload == {"tenantAlias": "TA"}
    assert diagnostics == ["EVD_FIELD_REJECTED", "EVD_SENSITIVE_VALUE"]
    assert "never-store" not in evidence.model_dump_json()


def test_evidence_over_64_kib_is_rejected() -> None:
    with pytest.raises(ValueError, match="EVD_FIELD_REJECTED"):
        sanitize_evidence("TEN-001", {"value": "x" * 65536}, {"value"})
