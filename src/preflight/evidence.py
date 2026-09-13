"""Evidence allowlisting and baseline secret rejection."""

import json
from datetime import UTC, datetime

from preflight.models import Evidence

SENSITIVE_PARTS = ("password", "secret", "token", "api_key", "apikey", "credential")
MAX_EVIDENCE_BYTES = 64 * 1024


def sanitize_evidence(
    source: str,
    payload: dict[str, object],
    allowlist: set[str],
    *,
    timestamp: datetime | None = None,
) -> tuple[Evidence, list[str]]:
    safe: dict[str, object] = {}
    diagnostics: list[str] = []
    for key, value in payload.items():
        lowered = key.lower()
        if any(part in lowered for part in SENSITIVE_PARTS):
            diagnostics.append("EVD_SENSITIVE_VALUE")
            continue
        if key not in allowlist:
            diagnostics.append("EVD_FIELD_REJECTED")
            continue
        safe[key] = value
    if len(json.dumps(safe, default=str).encode()) > MAX_EVIDENCE_BYTES:
        raise ValueError("EVD_FIELD_REJECTED: evidence exceeds 64 KiB")
    evidence = Evidence(
        type="normalized_observation",
        source=source,
        timestamp=timestamp or datetime.now(UTC),
        payload=safe,
    )
    return evidence, list(dict.fromkeys(diagnostics))
