# INC-008: Formal accessibility validation gate

**Status:** Implementation complete; human execution pending

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

## Remaining release gate

Formal WCAG 2.2 AA conformance is not yet claimed. A human reviewer must run
`docs/validation/A11Y_WCAG_2_2_AA_MANUAL_PROTOCOL.md` against the unchanged final report using both
required Windows 11 assistive-technology environments. Any report HTML or CSS change invalidates
the evidence and requires both environments to be repeated.
