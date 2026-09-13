# Project Status

**Baseline:** Version 1.5 Core Development Baseline  
**Overall state:** Version 1.5 Core Development Baseline complete
**Verification claim:** Core/reference verification and the named Supabase test integration are verified. No Stripe, customer target, production deployment, cPanel environment, or formal accessibility conformance has been verified.

## Phase gates

| Phase | State | Evidence |
| --- | --- | --- |
| C1 | Complete | strict models/config, exact owned diagnostic paths and clean-wheel package validation pass |
| C2 | Complete | all seven bundled provider-neutral ports, catalog metadata, sync/async normalization and no-egress checks pass |
| C3 | Complete | provisioning, atomic journal registration, interruption, partial failure, reverse cleanup and gates pass |
| C4 | Complete | stateful tenant/RBAC/entitlement scenarios, applicability and isolated defect variants pass |
| C5 | Complete | stateful billing/event/usage scenarios, policy variants and isolated defect variants pass |
| C6 | Complete | evidence, artifacts and offline HTML pass; native Chromium matrix passes at 320/375/768/1440 px with retained evidence |
| C7 | Complete | AC-001–014, bidirectional traceability, clean-wheel journey and final CI gates pass |

## Final validation evidence

- CPython: 3.11.16.
- Automated tests: 92 passed, no skips or expected failures.
- Ruff formatting/linting: passed.
- Isolated wheel build: passed.
- Clean environment wheel installation: passed.
- Installed CLI version and help smoke: passed.
- Clean-wheel functional journey: init, doctor, filtered catalog, tenant suite, report regeneration and cleanup passed.
- INC-001 clean-wheel journey: default reference_core, report regeneration and cleanup passed.
- Reference core: 36 applicable scenarios; usage adds 6 when enabled.
- Defect corpus: each selected reference defect is caught by its matching scenario.
- Failure paths: invalid configuration/report, runtime error, fail-fast missing coverage, and cleanup failure validated.
- Provenance: reference-only banner and all six deferred scopes explicitly unverified.
- External provider/network dependencies: absent from core imports.
- Native Chromium report matrix: 320, 375, 768 and 1440 px passed in GitHub Actions run
  `34776323065`; JSON measurements and screenshots retained in artifact
  `preflight-browser-matrix-34776323065`.

## Deferred, non-blocking work

Stripe and cPanel-specific deployment remain governed by the Version 1.5 deferred-integration backlog. Supabase has moved from deferred design into a verified test integration.

Supabase activation is complete through `SUP-001` for dedicated test project alias
`rsrztmgozovtjmbstlje`. The provider-neutral adapter, reproducible shared-schema and RPC migrations,
strict RLS/grants, contract tests, real Auth identities, and authenticated Data API allow/deny/create/
cleanup probes are implemented. GitHub Actions run `34759024714`, attempt 4, completed successfully
on 2026-09-13. This evidence verifies only the named Supabase test integration; it does not verify a
production project, customer environment, general Supabase availability, or unrelated providers.

GitHub Actions has been activated through decision `GHA-001`. Its passing workflow verifies only repository build evidence and cannot change reference or external verification provenance.

Activation evidence: workflow run `34750679159` completed successfully on Python 3.11, including lint, 28 tests, wheel build, clean-wheel installation, CLI smoke, and artifact publication.

Remote HTTP safety has been implemented through decision `HTTP-001` as an optional external transport. Its security controls are covered by the current 50-test repository suite. Supabase exercises this transport against its named test project; other real targets remain unverified until their hostname, operation map, authorization and credentials are approved.

Accessibility implementation has been activated through `A11Y-001` with WCAG 2.2 AA as the target. Structural acceptance is included in the current 50-test repository suite. A formal conformance claim remains pending manual browser, keyboard, zoom, forced-color and screen-reader validation of the final artifact.

## Release boundary

This status accepts the Version 1.5 Core Development Baseline and the named Supabase test integration. It does not claim an Integrated Foundational MVP, production deployment, Stripe/customer-system verification, penetration test, compliance certification, or formal accessibility conformance.
