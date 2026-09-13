"""Validation contracts for human WCAG report evidence."""

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, model_validator

from preflight.models import StrictModel

REQUIRED_CHECKS = {f"A11Y-MAN-{number:03d}" for number in range(1, 11)}
REQUIRED_COMBINATIONS = {("NVDA", "Chrome"), ("Narrator", "Edge")}


class ManualCheck(StrictModel):
    id: str
    status: Literal["not_run", "pass", "fail"]
    notes: str = Field(default="", max_length=2000)


class AssistiveEnvironment(StrictModel):
    screen_reader: Literal["NVDA", "Narrator"]
    screen_reader_version: str = Field(min_length=1, max_length=100)
    browser: Literal["Chrome", "Edge"]
    browser_version: str = Field(min_length=1, max_length=100)
    operating_system: str = Field(min_length=1, max_length=100)
    checks: list[ManualCheck]

    @model_validator(mode="after")
    def complete_check_set(self) -> AssistiveEnvironment:
        ids = [check.id for check in self.checks]
        if len(ids) != len(set(ids)) or set(ids) != REQUIRED_CHECKS:
            raise ValueError("manual environment must contain each required check exactly once")
        return self


class AccessibilityEvidence(StrictModel):
    schema_version: Literal["1.0"]
    report_sha256: str
    tested_at: datetime
    reviewer: str = Field(min_length=1, max_length=200)
    environments: list[AssistiveEnvironment]

    @model_validator(mode="after")
    def complete_matrix(self) -> AccessibilityEvidence:
        if not re.fullmatch(r"[0-9a-f]{64}", self.report_sha256):
            raise ValueError("reportSha256 must be a lowercase SHA-256 digest")
        combinations = {(item.screen_reader, item.browser) for item in self.environments}
        if combinations != REQUIRED_COMBINATIONS or len(self.environments) != 2:
            raise ValueError("evidence requires NVDA/Chrome and Narrator/Edge exactly once")
        if any(check.status != "pass" for item in self.environments for check in item.checks):
            raise ValueError("formal accessibility evidence contains incomplete or failed checks")
        return self


def validate_manual_evidence(path: Path, report: Path | None = None) -> AccessibilityEvidence:
    try:
        evidence = AccessibilityEvidence.model_validate(yaml.safe_load(path.read_text()))
    except Exception as exc:
        raise ValueError(f"A11Y_EVIDENCE_INVALID: {exc}") from None
    if report is not None:
        digest = hashlib.sha256(report.read_bytes()).hexdigest()
        if digest != evidence.report_sha256:
            raise ValueError("A11Y_EVIDENCE_INVALID: report digest does not match evidence")
    return evidence


def contrast_ratio(foreground: str, background: str) -> float:
    def luminance(color: str) -> float:
        values = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            value / 12.92
            if value <= 0.04045
            else ((value + 0.055) / 1.055) ** 2.4
            for value in values
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    first, second = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (first + 0.05) / (second + 0.05)
