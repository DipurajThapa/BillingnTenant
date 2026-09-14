# INC-008: Formal accessibility validation gate

**Status:** Complete

## Objective

Turn the selected WCAG 2.2 Level AA target into a repeatable, artifact-bound release gate without
claiming that automation substitutes for assistive-technology testing.

## Delivered

- The authoritative `A11Y-REQ-001` through `A11Y-REQ-004` requirements and observable
  `A11Y-AC-001` through `A11Y-AC-004` acceptance criteria.
- A ten-case protocol executed in both NVDA/Chrome and Narrator/Edge on Windows 11.
- A strict YAML evidence model that requires both environments and every manual case exactly once.
- Rejection of failed, unexecuted, duplicate or missing checks and incorrect environment pairings.
- SHA-256 binding between the reviewed report and its evidence record.
- Automated tests for evidence validity, invalid matrices, digest mismatch and report palette
  contrast.
- Requirement-to-test-to-acceptance traceability for automated, evidence and manual validation.

## Verification

- Ruff passes.
- All 95 automated tests pass with no skips or expected failures.
- The validator accepts only a complete passing matrix bound to the supplied report.

## Human release-gate evidence

Dipuraj Thapa completed both required Windows 11 assistive-technology environments on 2026-09-14.
All twenty manual environment/check results passed and the repository validator accepted the
SHA-256-bound evidence. This completes `A11Y-AC-001` through `A11Y-AC-004` for the recorded report
artifact. Any report HTML or CSS change invalidates this evidence and requires both environments to
be repeated.
