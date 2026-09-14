# INC-009: Local dashboard vertical slice

**Status:** Implemented; repository CI evidence pending

## Objective and user outcome

Give a technical founder or engineer a local visual workflow to start reference verification,
review validated history and open the exact evidence report, without turning the core into a hosted
control plane or coupling it to a provider.

## Delivered scope

- `preflight dashboard --port <1024-65535>` with fixed `127.0.0.1` binding.
- Framework-neutral `DashboardService` for configuration, execution and validated artifact reads.
- Local HTML home, run-history, run-detail and standalone-report routes.
- Existing engine, gate, provenance and artifact contracts reused without duplicated logic.
- Visible configuration, invalid-suite, missing-run/report, busy-run and invalid-request failures.
- CSRF form token, Origin enforcement, bounded form bodies, safe run IDs and restrictive response
  headers.
- Semantic, keyboard-operable, responsive, offline UI with no JavaScript or remote assets.
- Native Chromium and Firefox browser journey at 320, 375, 768 and 1440 CSS pixels in CI.
- Local installation, operation, evidence and troubleshooting guide.

## Claim boundary

The dashboard starts only reference runs. It cannot emit or imply customer, production, Stripe,
cPanel or general external verification. The unauthenticated local HTTP handler must never be
published, proxied or reused as a hosted service.

## Validation gate

`DASH-REQ-001` through `DASH-REQ-008` map to `DASH-TST-001` through `DASH-TST-005` and
`DASH-AC-001` through `DASH-AC-004`. Completion requires the full Python 3.11 repository suite,
wheel checks, existing report browser matrix and new dashboard browser matrix to pass in GitHub
Actions.
