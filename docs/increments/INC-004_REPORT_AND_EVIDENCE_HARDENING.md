# INC-004: Report and evidence hardening

**Status:** Implementation complete; native-browser matrix blocked by execution environment

## Requirement coverage

EVD-001–004, RPT-001–009, OPS-001–005, UI-001–004 and AC-011–012.

## Delivered behavior

- Evidence retains only allowlisted fields, rejects nested secret-like keys and enforces the
  64 KiB per-scenario ceiling.
- Run artifacts are staged and committed as a directory; a write failure removes staging and
  leaves no partial run artifact.
- Reports remain standalone, escaped, reference-scoped, semantically structured and responsive
  by construction at the specified CSS breakpoints.

## Remaining validation dependency

The generated report passed structural, offline, escaping, keyboard-markup and responsive-CSS
tests. A native Chromium/Firefox viewport matrix could not be executed because this workspace
has no browser runtime and the connected cloud browser blocks local/data URLs. This is the only
remaining C6 validation item; it is not represented as passed.

