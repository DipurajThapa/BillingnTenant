# SaaS Billing & Tenant Preflight

## Version 1.5 Authoritative Product Development Specification

**Status:** Core Development Baseline approved for implementation  
**Runtime:** CPython 3.12
**Current verification level:** reference only  
**External integrations:** separately activated and claimed only at their recorded evidence level

## 1. Document map

All four documents form the specification:

| Document | Sole source of truth |
| --- | --- |
| [00_PRIMARY_PRODUCT_SPEC.md](00_PRIMARY_PRODUCT_SPEC.md) | Product, releases, workflows, architecture, states, UX and governance |
| [01_CORE_CONTRACTS_AND_SCENARIOS.md](01_CORE_CONTRACTS_AND_SCENARIOS.md) | Core models, interfaces, configuration, scenario definitions and diagnostics |
| [02_CORE_VERIFICATION_AND_TRACEABILITY.md](02_CORE_VERIFICATION_AND_TRACEABILITY.md) | Core tests, traceability, acceptance criteria and definition of done |
| [03_DEFERRED_INTEGRATIONS_BACKLOG.md](03_DEFERRED_INTEGRATIONS_BACKLOG.md) | Deferred Stripe, Supabase, remote HTTP, GitHub Actions, accessibility and cPanel work |

Rules:

- Requirements are maintained once and referenced by stable IDs.
- An implementation task loads this document and the relevant companion.
- Core acceptance never depends on a deferred backlog item.
- A reference result never implies an external provider, remote application, CI platform, accessibility conformance or hosting environment was verified.
- If documents conflict, stop the affected work, apply the source-of-truth rule above and correct the conflict before merging.

## 2. Product and release boundaries

### PRD-001 Product purpose

Preflight is a deterministic assurance engine for testing declared tenant, role, billing-state, webhook-state, entitlement and optional usage rules. It arranges controlled fixtures, executes scenarios through replaceable ports, compares observations with explicit expectations, records sanitized evidence and produces a release gate.

### PRD-002 Intended users

- Technical founder or CTO reviewing assurance results.
- Engineer configuring adapters and correcting findings.
- Agency engineer operating an authorized preflight.
- Future CI system consuming stable exit codes and artifacts.

The current product has no hosted user, account, organization or subscription. The post-baseline
local dashboard defined by `DASH-001` is an operator interface, not a hosted control plane.

### PRD-003 Core Development Baseline

The currently authorized build is a fully working provider-neutral engine validated against an in-process or loopback reference target. It includes:

- Python package and CLI;
- local-only dashboard behind the existing application-service boundary;
- strict versioned configuration and artifacts;
- provider-neutral ports and canonical observations;
- immutable reference scenario catalog;
- dependency, applicability, concurrency and lifecycle engine;
- deterministic assertions, findings, gates and exit codes;
- fixture journal, interruption recovery and idempotent cleanup;
- evidence allowlisting and baseline secret redaction;
- console, JSON and responsive offline HTML;
- correct reference target and seeded defective variants;
- core unit, contract, functional, scenario, negative, recovery and UI tests; and
- requirement-to-test-to-acceptance traceability.

### PRD-004 Integrated Foundational MVP

This later release connects the proven core to selected external systems. Supabase test integration,
remote HTTP safety and GitHub Actions have separate activation records; none changes core behavior or
provenance. Stripe and cPanel remain deferred. External assurance claims are prohibited unless the
named integration's activation gate and acceptance criteria pass.

GitHub Actions and artifact-specific accessibility validation have been activated and verified under
their decision records. cPanel deployment remains an independent deferred capability and is not
required for the Integrated Foundational MVP unless later approved.

### PRD-005 Exclusions from the core baseline

The current build must not:

- call Stripe, Supabase or any other external provider;
- execute probes against a non-loopback target;
- generate or install GitHub Actions workflows;
- claim WCAG or other formal accessibility conformance;
- deploy or include cPanel/Passenger-specific application code;
- implement a hosted control plane;
- add Preflight registration, organizations, billing or subscriptions;
- use AI to decide an assertion, severity, finding, gate or fix;
- claim penetration-testing, compliance or comprehensive-security coverage; or
- require Node/npm, Redis, Celery, WebSockets, Docker, root access or persistent workers.

### PRD-006 Core outcomes

The core proves that the engine can correctly detect reference defects in:

1. cross-tenant reads and mutations;
2. role-based authorization;
3. billing-state transitions;
4. duplicate and stale event application;
5. combined role and plan capability decisions; and
6. optional usage attribution, idempotency and quota boundaries.

It does not prove any customer's implementation until external adapters and safe transport are completed and an authorized external run passes.

## 3. Verification claims and provenance

### VER-001 Verification levels

```python
VerificationLevel = Literal[
    "reference_verified",
    "integration_incomplete",
    "externally_verified",
]
```

- `reference_verified`: selected scenarios completed only against bundled reference ports/target.
- `integration_incomplete`: the selected verification profile did not complete because execution, required coverage, cleanup, or—in a later external profile—an adapter/control was unavailable or unverified.
- `externally_verified`: reserved until a named integration release and authorized external run meet backlog acceptance criteria.

The core baseline emits `reference_verified` only after a reference run completes with complete required coverage, regardless of whether its assertion gate is PASS, WARN or FAIL. An execution error, interruption, missing required coverage or cleanup failure emits `integration_incomplete`. Core configuration must reject `externally_verified`; only an activated later integration may emit it.

### VER-002 Required provenance

Every run records:

- execution profile: `reference` or reserved `external`;
- verification level;
- adapter names and versions;
- transport name and version;
- scenario catalog version;
- configuration hash;
- tool version and optional Git commit;
- selected suites; and
- explicit `verifiedScopes` and `unverifiedScopes`.

Core reports must display: **Reference verification only. No external provider or customer environment was tested.**

## 4. Core user workflows

### WF-001 Initialize a reference project

Command: `preflight init [--force] [--non-interactive]`

1. Detect existing `.preflight/core.yml` and reference override file.
2. Collect project label, reference suites, feature flags, role/plan/capability policies and artifact directory.
3. Validate the complete candidate configuration in memory.
4. Write files atomically using temporary files and rename only after all validation succeeds.
5. Never overwrite without interactive confirmation or `--force` in non-interactive mode.
6. Print created paths and next command.

Interactive cancellation exits 0 with no change. Invalid input or filesystem failure exits 2. If a multi-file write fails, restore original files and remove temporary files.

### WF-002 Validate readiness

Command: `preflight doctor [--ci]`

Doctor validates schema, cross-references, reference port contracts, selected scenario dependencies, output-directory permissions and catalog compatibility. It performs no scenario action or fixture mutation. It prints one `PASS`, `WARN` or `FAIL` line per check and a stable diagnostic code in CI mode.

Exit 0 means ready; exit 2 means invalid or incomplete. Safety refusal exit 3 is reserved for future external execution and is not produced by a valid core/reference configuration.

### WF-003 Run reference scenarios

Command: `preflight run [--suite NAME ...] [--fail-fast] [--ci]`

1. Perform doctor validation.
2. Create the run directory and journal.
3. Provision only fixtures required by selected scenarios through reference ports.
4. Execute the dependency graph.
5. Observe normalized state and assert deterministic oracles.
6. Create findings only for failed assertions.
7. Write provisional JSON and HTML.
8. Cleanup in `finally`.
9. Update artifacts with final cleanup/execution/gate state.
10. Return the normative exit code.

CLI suites override configured suites. Repeated suite values are deduplicated in canonical order. `reference_core` expands to tenant_reference, rbac_reference, billing_reference, webhook_reference and entitlement_reference. Usage is separate.

### WF-004 Clean reference fixtures

Command: `preflight clean <run-id>`

Validate run ID and journal, verify the journal names reference adapters only, and delete exact registered fixtures in reverse dependency order. Already-absent fixtures are successful no-ops. Invalid or inconsistent journals stop cleanup with exit 2 and safe manual guidance. Reports are retained.

### WF-005 Regenerate a report

Command: `preflight report <run.json>`

Validate supported result schema and regenerate HTML without scenario execution or outcome recalculation. Invalid/unsupported input exits 2 and writes no partial output.

### WF-006 Inspect catalog

Command: `preflight catalog [--suite NAME] [--json]`

Display stable scenario ID, title, suite, severity, applicability, dependencies and verification level. This is read-only and provides AI tools/users an exact implementation inventory.

## 5. Core architecture

### ARC-001 Structure

```text
src/preflight/
  cli/          commands and terminal presentation
  schemas/      strict versioned models
  core/         lifecycle, graph, assertions, gates, journal
  scenarios/    immutable reference definitions/oracles
  ports/        provider-neutral interfaces only
  reference/    in-memory/loopback port implementations and target
  evidence/     allowlisting and baseline redaction
  reporters/    JSON and standalone HTML
  diagnostics/  core diagnostic catalog
tests/          layers defined in Document 02
```

### ARC-002 Dependency direction

`cli/reporters/reference adapters → core interfaces/models`; core must never import a concrete external provider. Scenario oracles depend only on canonical models and ports. Reporters do not call ports or calculate outcomes. Dependency tests enforce these rules.

### ARC-003 Provider-neutral ports

The core exposes only:

- `FixturePort`;
- `IdentityTenantPort`;
- `BillingStatePort`;
- `EventDeliveryPort`;
- `UsagePort` when enabled;
- `ProbeTransport`; and
- `ClockPort`.

Detailed contracts are in Document 01. Future integrations implement these ports without changing core models, scenario IDs or gate behavior.

### ARC-004 Reference implementations

The bundled reference system is deterministic, local and resettable. It includes correct behavior and one focused defect toggle per scenario. Reference ports must not import Stripe/Supabase SDKs or access the public network.

### ARC-005 Runtime and dependencies

CPython 3.12, Typer, Pydantic v2, PyYAML, Jinja2 and pytest are current baseline dependencies. Standard-library async primitives are preferred. An HTTP client is not a required core dependency; a loopback implementation may use an in-process callable transport. `pyproject.toml` accepts the tested Python 3.12 release series (`>=3.12,<3.13`), CI uses an exact constraints file, and releases are tested from a built wheel.

### ARC-006 Concurrency

The engine is async. Independent read-only scenarios may run concurrently, default maximum 4. Mutations sharing a fixture namespace or logical aggregate serialize. Cleanup waits for running tasks to settle/cancel. Business actions are never transparently retried.

## 6. State, gate and exit rules

### STA-001 Canonical states

```python
ScenarioStatus = Literal["passed", "failed", "skipped", "error"]
ExecutionStatus = Literal["completed", "error", "interrupted"]
AssertionGateStatus = Literal["PASS", "WARN", "FAIL"]
GateStatus = Literal["PASS", "WARN", "FAIL", "INCOMPLETE"]
CleanupStatus = Literal["not_required", "completed", "partial", "failed"]
```

External `refused/REFUSED/exit 3` values are reserved in schema for forward compatibility but cannot arise from reference adapters.

### STA-002 Lifecycle

`validating → provisioning → executing → reporting → cleaning → finished`

- Invalid config/dependency: execution error, incomplete, no fixtures.
- Partial provisioning/runtime error: preserve results, cleanup, incomplete.
- Interruption: stop scheduling, bounded cancel, cleanup, partial artifacts, incomplete.
- Cleanup failure: retain assertion gate, final incomplete.

### STA-003 Scenario semantics

- Passed: all deterministic assertions passed.
- Failed: observation contradicts oracle; exactly one finding.
- Skipped: feature absent, optional disabled or dependency unavailable; reason required.
- Error: behavior could not be reliably determined; error code required.

Skipped/error never pass. Required applicable skipped/error produces incomplete coverage.

### STA-004 Gate calculation

```text
assertion gate:
  any Blocker/High failure → FAIL
  promoted Medium failure → FAIL
  Medium failure → WARN
  otherwise → PASS

final gate:
  execution error, interruption, required coverage missing or cleanup failure → INCOMPLETE
  otherwise → assertion gate
```

Store and display both gates.

### STA-005 Exit codes

0 = completed PASS/WARN; 1 = completed FAIL; 2 = INCOMPLETE/error/interrupted/cleanup failure. Exit 3 is reserved for future safe external refusal.

## 7. Core safety and data boundaries

### SEC-CORE-001 No external egress

Core/reference execution must not resolve DNS, open non-loopback sockets or call any external provider. Network-spy tests enforce this. A reference configuration containing a remote URL or external adapter type fails doctor with `CORE_EXTERNAL_NOT_ENABLED`.

### SEC-CORE-002 Trusted code boundary

Bundled reference adapters are trusted package code. Future customer adapters are deferred. No plugin discovery, arbitrary module path or dynamic third-party code execution exists in the core baseline.

### SEC-CORE-003 Evidence minimization

Persist only engine-generated fixture aliases/IDs, actions, normalized states, counters, timestamps/durations and stable hashes required by an oracle. Never persist environment dumps, source code or arbitrary payloads. Baseline redaction removes common token/password/key fields. Full provider-specific scanners are deferred.

### SEC-CORE-004 Journal and cleanup

Register every created reference fixture before the next dependent action. Journal sequence is contiguous and run-bound. Cleanup uses exact registered IDs, never prefix-wide discovery. On POSIX, run directory/files default to owner-only permissions where supported.

### SEC-CORE-005 Configuration boundaries

Strict schemas reject unknown fields and all external provider/remote transport blocks until their backlog item is activated in a later schema version.

## 8. Error, retry and recovery

### ERR-001 Typed core errors

Core uses `CFG_*`, `CORE_*`, `PORT_*`, `SCN_*`, `EVD_*`, `CLN_*` and `RPT_*`. Provider-owned namespaces are reserved but not emitted by the core.

### ERR-002 Reference retries

Reference ports are deterministic and receive no automatic retry. A retry scenario explicitly invokes the same logical event/action as part of the oracle.

### ERR-003 Partial provisioning

Stop dependent work, clean all journaled fixtures and exit 2. Failure to journal a newly created fixture is a core error; the reference implementation must make create-and-register atomic.

### ERR-004 Interruption

SIGINT/SIGTERM stops new scheduling, allows 10 seconds to settle/cancel, attempts cleanup, writes a partial valid artifact when possible and exits 2.

### ERR-005 Reporter failure

Cleanup still runs. If JSON cannot be validated/persisted, write only a minimal sanitized emergency summary to stderr; never claim PASS/FAIL. Exit 2.

## 9. Report UI/UX

### UI-001 Terminal

Show run ID, `reference` profile, suites, one scenario line, counts, assertion/final gates, cleanup, report path and exit explanation. Text labels accompany optional color/symbols. `--verbose` adds only sanitized core diagnostics.

### UI-002 HTML

Required order: reference-only banner; final/assertion decisions; run provenance; counts; incomplete causes; findings; full selected coverage; fixture/cleanup; limitations.

States:

- PASS/WARN: coverage follows decision.
- FAIL: Blocker/High findings first.
- INCOMPLETE: missing dependency/error above ordinary counts.
- Partial: completed results remain visible; unfinished scenarios explicit.
- Cleanup failure: persistent warning and exact clean command.

### UI-003 Baseline usability

Documentation-style layout, about 1120px maximum, system sans body 15–16px, phone body at least 14px, restrained borders and spacing, color never the only status signal, semantic headings/tables/details, native keyboard-operable controls and visible browser-default or enhanced focus. These are compatibility requirements, not a WCAG conformance claim.

### UI-004 Responsive/offline

Usable at 320, 375, 768 and 1440 CSS pixels without essential clipping or page-level horizontal overflow. Below 600px, use single column, wrapping IDs, stacked timelines and labeled scrolling/row-group tables. Report has bundled CSS, optional minimal vanilla JS, no CDN/remote font/request, and escapes all rendered text.

## 10. Observability and artifacts

### OPS-001 Artifacts

`.preflight/runs/<run-id>/` contains `journal.jsonl`, `run.json`, `preflight-report.html`, with optional local-only `logs.jsonl` and `debug.json`. Cleanup retains reports.

### OPS-002 Structured events

Run/scenario start/finish, fixture register/delete and cleanup finish include run ID, type, UTC timestamp, duration/status/code and safe fixture alias. No arbitrary body.

### OPS-003 Supported platforms

Current macOS and Linux on CPython 3.12. The local dashboard and installed CLI are additionally verified on Windows with CPython 3.12; the full Windows core platform is not otherwise promised. No performance SLA applies before calibration; record durations immediately.

## 11. Implementation sequence

| Phase | Deliverable | Exit gate |
| --- | --- | --- |
| C1 | Package, core models, config, diagnostics | clean-wheel/unit/contract tests |
| C2 | Ports, reference implementations, catalog loader | port and no-egress tests |
| C3 | Lifecycle, graph, journal, gates, cleanup | state/failure/interruption tests |
| C4 | Reference tenant/RBAC/entitlement scenarios | correct/defect variants |
| C5 | Reference billing/event/usage-state scenarios | correct/defect variants; no provider claim |
| C6 | Console, JSON, HTML | golden/offline/responsive tests |
| C7 | Traceability and full core acceptance | all core ACs and definition of done |
| C8 | Local-first dashboard vertical slice | DASH-AC-001–004 |

Deferred work begins only through backlog activation. It cannot be silently added to C1–C7.

## 12. Assumptions and governance

| ID | Assumption |
| --- | --- |
| A-001 | One `src/` Python distribution named `saas-preflight`. |
| A-002 | CPython 3.12 only (`>=3.12,<3.13`) for current builds; Python 3.11 evidence remains historical and does not validate current releases. |
| A-003 | UTC RFC 3339 timestamps. |
| A-004 | Default concurrency 4 and interruption grace 10 seconds. |
| A-005 | Reference fixtures are synthetic and contain no personal/customer data. |
| A-006 | Usage-reference suite is optional and excluded from `reference_core`. |

No product-owner decision blocks C1–C7.

Deviation rule: before implementation, record affected IDs, proposed behavior, reason, security/data/provenance/test impact and approval. A deviation cannot weaken provenance, no-egress, deterministic authority, scenario severity or exclusions. Unapproved behavior changes block merge.

## 13. Implementation authority

- Document 01 controls models, ports, config, scenario oracles and diagnostics.
- Document 02 controls validation and completion.
- Document 03 alone controls deferred activation and readiness.
- Core reports may claim only reference verification.
- Missing behavior becomes an error/incomplete result, not an inferred expectation.
- Completion requires observable acceptance, not code presence or test-count targets.
