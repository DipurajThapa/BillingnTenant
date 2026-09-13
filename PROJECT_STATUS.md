# Project Status

**Baseline:** Version 1.5 Core Development Baseline  
**Overall state:** In development  
**Current phase:** C1 — package, core models, configuration and diagnostics  
**Verification claim:** None; development tests are not a release or external-verification claim

## Phase control

| Phase | State | Exit evidence |
| --- | --- | --- |
| C1 | In progress | DAT-001–012, CFG-001–014, DIA-001–004, PKG-001 |
| C2 | Not started | PORT-*, ARCH-*, SEC-001–008, SCOPE-001/002 |
| C3 | Not started | RUN-*, GATE-*, COV-*, ERR/CLN recovery tests |
| C4 | Not started | TEN/RBAC/ENT scenarios and defects |
| C5 | Not started | BILL/WEB/optional USG scenarios and defects |
| C6 | Not started | Evidence, console, JSON and HTML verification |
| C7 | Not started | AC-001–014 and bidirectional traceability |

## Current increment

Implemented the installable package skeleton, strict base/domain contracts, authentication-mode rules, initial core configuration and suite resolver, centralized diagnostics, CLI version entry point, pinned verification constraints and focused tests.

Remaining before C1 acceptance: complete every canonical model and cross-model invariant; implement the full billing/usage/seat configuration schema and exact diagnostic-path mapping; create executable traceability; run clean-wheel verification and the complete C1 test inventory.

## Latest verification evidence

- Unit/contract tests: 14 passed.
- Ruff format/lint: passed.
- Wheel build: passed in an isolated build environment.
- Installed CLI smoke: `preflight version` returned `0.1.0`.
- Environment limitation: the available runner is Python 3.12.14. Python 3.11 clean-environment acceptance remains pending and C1 is therefore not yet accepted.

## Decisions and assumptions

- Resolved: PyYAML is the minimal parser required by the approved `.preflight/core.yml` contract.
- No product-owner decision currently blocks C1.
- Stripe, Supabase, remote HTTP, GitHub Actions, formal accessibility and cPanel remain deferred.
