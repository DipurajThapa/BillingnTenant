# DASH-001: Local-first, hosted-ready dashboard

**Status:** Approved and implemented as a local reference dashboard
**Scope:** Post-baseline operator interface; does not change C1–C7 engine behavior

## User and outcome

The initial user is a technical founder or engineer running Preflight on an authorized local
workspace. The dashboard reduces CLI friction by allowing that user to start reference verification,
review prior decisions and open the exact evidence report without changing assertion logic.

## Architecture decision

Use a Python modular-monolith boundary. `DashboardService` owns application operations and depends
only on the existing configuration, engine and artifact models. The standard-library HTTP shell owns
local presentation and transport. It binds exclusively to `127.0.0.1`; it is not a hosted control
plane and has no authentication, organization model or remote-provider authority.

This separation is the hosted-ready boundary: a later authenticated web shell may call equivalent
application-service operations, but it must not reuse the unauthenticated local HTTP handler or
silently broaden reference verification claims.

## Requirements

- `DASH-REQ-001`: `preflight dashboard` starts on `127.0.0.1` only, with configurable unprivileged
  port 1024–65535, and prints the exact local URL.
- `DASH-REQ-002`: the home screen shows configuration availability, an explicit reference-run
  action and validated run history ordered newest first.
- `DASH-REQ-003`: a run uses the existing configuration and engine without recalculating or
  reinterpreting assertions, gates, provenance or artifacts.
- `DASH-REQ-004`: run detail shows gate, verification level, unverified scopes, scenario outcomes
  and a link to the exact standalone report.
- `DASH-REQ-005`: invalid run IDs, corrupt artifacts, invalid suites, missing configuration,
  concurrent execution and missing reports fail visibly without path traversal or false success.
- `DASH-REQ-006`: state-changing requests require an unguessable form token, reject foreign Origin
  values and oversized bodies, and all responses set no-store, nosniff, frame-denial, referrer and
  restrictive content-security headers.
- `DASH-REQ-007`: the UI uses semantic headings, forms and tables, visible focus, textual states,
  local CSS and usable reflow at 320–1440 CSS pixels without remote assets or client JavaScript.
- `DASH-REQ-008`: local dashboard results remain `reference_verified` or
  `integration_incomplete`; the UI cannot claim customer, production, Stripe or other external
  verification.

## Scope exclusions

- No login, accounts, organizations, shared database or public network binding.
- No configuration editor, fixture-clean action or external-provider execution in this increment.
- No background job queue, WebSocket, Node build, telemetry or remote asset.
- Stripe and cPanel remain deferred.

## Tests and acceptance

Tests `DASH-TST-001` through `DASH-TST-005` cover service execution/history, the HTTP journey,
invalid request and path boundaries, configuration/suite failures, responsive markup and security
headers.

- `DASH-AC-001`: from a valid initialized workspace, the operator can start the dashboard, execute
  a configured reference run and reach its detail page.
- `DASH-AC-002`: history, detail and standalone report agree with the validated `run.json`, and all
  external scopes remain visibly unverified.
- `DASH-AC-003`: non-local binding is not exposed; invalid or cross-origin mutations do not execute;
  missing/corrupt state produces an observable non-success response.
- `DASH-AC-004`: targeted functional, negative, security, responsive and existing CLI/report
  regression tests pass on Python 3.11.

## Revisit trigger

Before any hosted or shared deployment, define authentication, authorization, organization/data
ownership, persistent job state, audit events, concurrency, deployment, recovery and production
security as a separate activated increment. The local handler must never be exposed publicly.
