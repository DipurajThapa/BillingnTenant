"""Run-bound fixture journal and deterministic reference lifecycle helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from preflight.models import ResourceRef, StrictModel


class JournalEntry(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    run_id: str
    sequence: int = Field(ge=1)
    event: Literal[
        "run_created",
        "fixture_registered",
        "cleanup_attempted",
        "fixture_cleaned",
        "cleanup_failed",
    ]
    adapter_kind: Literal["reference"] = "reference"
    fixture_kind: str | None = None
    fixture_id: str | None = None
    fixture_alias: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    code: str | None = None

    @model_validator(mode="after")
    def validate_fixture_fields(self) -> JournalEntry:
        fixture_event = self.event != "run_created"
        present = bool(self.fixture_kind and self.fixture_id and self.fixture_alias)
        if fixture_event != present:
            raise ValueError("fixture journal fields conflict with event")
        if (self.event == "cleanup_failed") != (self.code is not None):
            raise ValueError("journal code conflicts with event")
        return self


@dataclass
class FixtureJournal:
    run_id: str
    entries: list[JournalEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.entries:
            self._append("run_created")

    def _append(
        self, event: str, resource: ResourceRef | None = None, code: str | None = None
    ) -> None:
        self.entries.append(
            JournalEntry(
                runId=self.run_id,
                sequence=len(self.entries) + 1,
                event=event,
                fixtureKind=resource.kind if resource else None,
                fixtureId=resource.external_id if resource else None,
                fixtureAlias=resource.metadata.get("alias") if resource else None,
                code=code,
            )
        )

    def register(self, resource: ResourceRef) -> None:
        if resource.run_id != self.run_id:
            raise ValueError("PORT_WRONG_RUN")
        key = (resource.kind, resource.external_id)
        existing = [
            entry
            for entry in self.entries
            if entry.event == "fixture_registered"
            and (entry.fixture_kind, entry.fixture_id) == key
        ]
        if existing:
            if existing[0].fixture_alias == resource.metadata.get("alias"):
                return
            raise ValueError("CLN_JOURNAL_INVALID")
        self._append("fixture_registered", resource)

    def cleanup_attempted(self, resource: ResourceRef) -> None:
        self._append("cleanup_attempted", resource)

    def cleaned(self, resource: ResourceRef) -> None:
        self._append("fixture_cleaned", resource)

    def cleanup_failed(self, resource: ResourceRef) -> None:
        self._append("cleanup_failed", resource, "CLN_PARTIAL")

    def registered(self) -> list[ResourceRef]:
        return [
            ResourceRef(
                kind=entry.fixture_kind,
                externalId=entry.fixture_id,
                runId=self.run_id,
                createdAt=entry.timestamp,
                metadata={"alias": entry.fixture_alias},
            )
            for entry in self.entries
            if entry.event == "fixture_registered"
        ]

    def write(self, path: Path) -> None:
        path.write_text(
            "".join(entry.model_dump_json(by_alias=True) + "\n" for entry in self.entries),
            encoding="utf-8",
        )


def validate_journal(path: Path, run_id: str) -> list[JournalEntry]:
    try:
        rows = [JournalEntry.model_validate_json(line) for line in path.read_text().splitlines()]
    except Exception as exc:
        raise ValueError("CLN_JOURNAL_INVALID") from exc
    if not rows or any(row.run_id != run_id or row.sequence != i for i, row in enumerate(rows, 1)):
        raise ValueError("CLN_JOURNAL_INVALID")
    registered = {(x.fixture_kind, x.fixture_id) for x in rows if x.event == "fixture_registered"}
    cleaned = {(x.fixture_kind, x.fixture_id) for x in rows if x.event == "fixture_cleaned"}
    attempted = {(x.fixture_kind, x.fixture_id) for x in rows if x.event == "cleanup_attempted"}
    if not cleaned <= attempted <= registered:
        raise ValueError("CLN_JOURNAL_INVALID")
    return rows
