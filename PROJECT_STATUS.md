# Project Status

**Baseline:** Version 1.5 Core Development Baseline  
**Overall state:** Core baseline complete and validated  
**Verification claim:** Reference verification only; no external system has been verified

## Phase gates

| Phase | State | Evidence |
| --- | --- | --- |
| C1 | Complete | strict models/config/diagnostics; Python 3.11 clean-wheel smoke |
| C2 | Complete | provider-neutral ports, immutable catalog, local reference implementation, no external imports |
| C3 | Complete | lifecycle, deterministic gates, typed runtime failure, fail-fast coverage, cleanup outcome |
| C4 | Complete | tenant/RBAC/entitlement catalog and correct/defective reference validation |
| C5 | Complete | billing/event/usage catalog and correct/defective reference validation |
| C6 | Complete | console, canonical JSON, journal, sanitized responsive offline HTML and regeneration |
| C7 | Complete | executable traceability, scope isolation, acceptance and clean-package validation |

## Final validation evidence

- CPython: 3.11.16.
- Automated tests: 28 passed, no skips or expected failures.
- Ruff formatting/linting: passed.
- Isolated wheel build: passed.
- Clean environment wheel installation: passed.
- Installed CLI version and help smoke: passed.
- Reference core: 36 applicable scenarios; usage adds 6 when enabled.
- Defect corpus: each selected reference defect is caught by its matching scenario.
- Failure paths: invalid configuration/report, runtime error, fail-fast missing coverage, and cleanup failure validated.
- Provenance: reference-only banner and all six deferred scopes explicitly unverified.
- External provider/network dependencies: absent from core imports.

## Deferred, non-blocking work

Stripe, Supabase, and cPanel-specific deployment remain governed by `docs/spec/03_DEFERRED_INTEGRATIONS_BACKLOG.md`.

Supabase activation is in progress through `SUP-001`. The provider-neutral adapter, reproducible
shared-schema and RPC migrations, strict RLS/grants, and contract tests are implemented. Both
migrations are applied to dedicated test project `rsrztmgozovtjmbstlje`; live rollback-only database
tests validate own-tenant visibility, cross-tenant denial, revoked membership denial and anonymous
denial. Real Auth identities and authenticated Data API adapter probes remain required, so no
Supabase provider verification claim is permitted yet.

GitHub Actions has been activated through decision `GHA-001`. Its passing workflow verifies only repository build evidence and cannot change reference or external verification provenance.

Activation evidence: workflow run `34750679159` completed successfully on Python 3.11, including lint, 28 tests, wheel build, clean-wheel installation, CLI smoke, and artifact publication.

Remote HTTP safety has been implemented through decision `HTTP-001` as an optional external transport. Its 7 additional security tests bring the suite to 35 passing tests. Real-target verification remains pending until an approved hostname, operation map, authorization and credentials are supplied.

Accessibility implementation has been activated through `A11Y-001` with WCAG 2.2 AA as the target. Four structural acceptance tests bring the suite to 39 passing tests. A formal conformance claim remains pending manual browser, keyboard, zoom, forced-color and screen-reader validation of the final artifact.

## Release boundary

This status accepts the Version 1.5 Core Development Baseline. It does not claim an Integrated Foundational MVP, production deployment, provider verification, penetration test, compliance certification, or formal accessibility conformance.
