# INC-002: Fixture lifecycle and recovery

**Status:** Complete

## Requirement coverage

WF-003, WF-004, STA-002, ERR-003, ERR-004, SEC-CORE-004, JRN-001, RUN-001–005,
ERR-004, ERR-006 and CLN-001–006.

## Delivered behavior

- Every selected scenario receives a run-bound synthetic fixture.
- Fixture creation and journal registration are one synchronous critical section.
- Journal sequence and run identity are validated before cleanup.
- Cleanup attempts exact registered resources in reverse order and continues after an
  independent failure.
- Partial provisioning and keyboard interruption stop scenario scheduling, retain missing
  coverage, attempt cleanup and produce an `INCOMPLETE` result.
- Artifact journals contain creation, cleanup-attempt, cleaned and cleanup-failure events.

## Evidence

`tests/test_lifecycle.py`, lifecycle cases in `tests/test_engine.py`, and the clean-wheel CLI
journey cover normal, partial, interrupted, repeated and invalid-journal paths.

