# WCAG 2.2 AA human validation protocol

This protocol applies only to the generated standalone HTML report. Use the exact report artifact
whose SHA-256 digest is recorded in the evidence file. Any report markup or CSS change invalidates
the human evidence and requires this protocol to be repeated.

## Required environments

1. Windows 11, current Chrome and current stable NVDA.
2. Windows 11, current Edge and Windows Narrator.

Record exact OS, browser and screen-reader versions. Use
`docs/validation/a11y-manual-evidence.template.yml` as the evidence record.

## Test procedure

Run every check in both environments:

| ID | Action | Pass condition |
| --- | --- | --- |
| A11Y-MAN-001 | Open the report and read from the top | Title, one main heading and reference-verification warning are announced in logical order |
| A11Y-MAN-002 | List/navigate landmarks and headings | Header, main, footer and ordered section headings are identifiable without duplicated or missing levels |
| A11Y-MAN-003 | Press Tab from the top and activate the skip link | Focus is visible; activation moves reading/focus position to main results |
| A11Y-MAN-004 | Navigate the decision summary | Labels and values are announced as associated pairs; gate meaning does not depend on color |
| A11Y-MAN-005 | Navigate the scenario table by rows and columns | Caption and row/column headers are announced with each applicable cell |
| A11Y-MAN-006 | Review passed, failed, skipped and error report samples | Every state and severity is available as text and each finding remains understandable |
| A11Y-MAN-007 | Review an INCOMPLETE and cleanup-failure sample | Cause, cleanup warning and exact recovery command are announced before ordinary coverage detail |
| A11Y-MAN-008 | Use browser zoom at 200% and 400% | Content remains readable and operable without loss, overlap or two-dimensional page scrolling at 1280 CSS-pixel baseline |
| A11Y-MAN-009 | Enable Windows high contrast/forced colors | Text, focus, borders and status meanings remain perceivable |
| A11Y-MAN-010 | Apply WCAG text-spacing overrides | No content or functionality is clipped, overlapped or lost |

Use `pass` only when the complete pass condition is observed. Use `fail` for any defect and explain
it in `notes`; use `not_run` when not executed. Any `fail` or `not_run` blocks formal conformance.

## Evidence validation

After completing both environments, run:

```bash
python scripts/validate_a11y_evidence.py \
  docs/validation/a11y-manual-evidence.yml \
  --report /absolute/path/to/preflight-report.html
```

The command must print `A11Y_MANUAL_EVIDENCE_PASS`. Commit the completed evidence record only if it
contains no personal information beyond the reviewer's approved display name.
