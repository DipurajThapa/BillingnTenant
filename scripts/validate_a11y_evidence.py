"""Validate completed human accessibility evidence against its report."""

import argparse
from pathlib import Path

from preflight.accessibility import validate_manual_evidence


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    arguments = parser.parse_args()
    evidence = validate_manual_evidence(arguments.evidence, arguments.report)
    print(
        "A11Y_MANUAL_EVIDENCE_PASS "
        f"report_sha256={evidence.report_sha256} environments={len(evidence.environments)}"
    )


if __name__ == "__main__":
    main()
