# SaaS Preflight Version 1.5

## Core Verification, Traceability and Definition of Done

Authoritative for current tests and completion. Deferred tests live only in [Document 03](03_DEFERRED_INTEGRATIONS_BACKLOG.md).

## 1. Test principles

### TST-001 Scope

Core tests use bundled reference ports and in-process transport only. They must not require provider credentials, public network, GitHub, assistive-technology conformance tooling or hosting access.

### TST-002 Layers

| Layer | Purpose |
| --- | --- |
| Unit | models, config, policies, gates, applicability, evidence and diagnostics |
| Contract | provider-neutral ports, provenance, artifacts and journal |
| Functional/scenario | reference workflow and every selected scenario oracle |
| Negative/boundary | invalid config, wrong-run objects, privilege, limits and false claims |
| Failure/recovery | partial provisioning, interruption, report and cleanup failure |
| UI/report | golden console/JSON/HTML, offline and responsive behavior |
| Packaging | clean built-wheel and supported-platform smoke |

No test is duplicated unless it adds a distinct boundary or regression.

### TST-003 Determinism

AI never supplies expectations. Same seed/config/reference implementation yields the same scenario status matrix and normalized artifact except run IDs/timestamps/durations. Each Blocker/High scenario must catch its intended defect toggle and pass after correction.

## 2. Traceability matrix

| Requirement | Behavior boundary | Tests | Acceptance |
| --- | --- | --- | --- |
| PRD-001–003 | deterministic provider-neutral core | RUN-*, PORT-*, SCN-* | AC-001–012 |
| PRD-004–005 | deferred external work excluded | SCOPE-001–003 | AC-013 |
| PRD-006 | reference defect detection only | scenario IDs, DEF-* | AC-008, AC-009 |
| VER-001–002 | no false external claim | PROV-001–006, RPT-003 | AC-003 |
| WF-001 | atomic init | CLI-001–005 | AC-004 |
| WF-002 | read-only readiness | CLI-006–008 | AC-005 |
| WF-003 | ordered lifecycle | RUN-001–005, GATE-* | AC-006, AC-007 |
| WF-004 | exact cleanup | CLN-001–006 | AC-010 |
| WF-005 | report regeneration | RPT-001–002 | AC-011 |
| WF-006 | catalog inspection | CLI-009 | AC-005 |
| ARC-001–006 | boundaries/concurrency | ARCH-001–006, PORT-* | AC-001, AC-002 |
| STA-001–005 | statuses/gates/exits | GATE-001–007, COV-* | AC-007 |
| SEC-CORE-001–005 | no egress/trusted reference/minimal evidence/exact cleanup | SEC-001–008, EVD-*, CLN-* | AC-002, AC-003, AC-010 |
| ERR-001–005 | typed failures/recovery | ERR-001–007 | AC-006, AC-010 |
| UI-001–004 | clear responsive offline report | RPT-003–009 | AC-011, AC-012 |
| OPS-001–003 | artifacts/events/platform | OPS-001–005, PKG-001 | AC-001, AC-011 |
| DATA-001–005 | canonical strict models | DAT-001–012 | AC-002, AC-003, AC-011 |
| CFG-001–003 | reference-only config/suites | CFG-001–014 | AC-004, AC-005 |
| PORT-001–007 | replaceable ports | PORT-001–012 | AC-002, AC-006 |
| scenario catalog | deterministic oracles/applicability | all scenario IDs, DEF-* | AC-008, AC-009 |
| EVD-001–002, JRN-001 | evidence/findings/journal | EVD-*, CLN-* | AC-010, AC-011 |
| diagnostics/limits | owned codes and bounded resources | DIA-001–004, LIM-001–005 | AC-002, AC-005 |

A machine-readable copy must resolve every ID bidirectionally. Unknown/missing IDs fail the build.

### TST-006 Machine traceability contract

The repository contains `tests/traceability.yml` with schema version `1.0`. Each entry has one `requirementId`, non-empty `testIds`, and non-empty `acceptanceIds`; scenario requirements additionally use their scenario ID as a test ID. IDs may be listed individually or as declared catalog families, but the validator expands families before checking. A build-time validator loads the four specification sources/catalog metadata and fails on an unknown ID, an orphan material requirement, a test with no requirement, an acceptance criterion with no requirement, or a duplicate requirement entry. The table above is the readable view; the YAML file is the executable view and must express the same links.

## 3. Core test inventory

### 3.1 Models, provenance and configuration

| ID | Action | Expected |
| --- | --- | --- |
| DAT-001 | Validate canonical correct models | Accepted and stable serialization |
| DAT-002 | Add unknown field | Exact validation failure |
| DAT-003 | Mismatch fixture/run | Rejected before port call |
| DAT-004 | Active tenant not active membership | Rejected |
| DAT-005 | Duplicate resource ID within kind | Rejected |
| DAT-006 | Invalid auth-mode field combination | Rejected |
| DAT-007 | Privileged auth in authorization scenario | Rejected |
| DAT-008 | NaN/negative usage or negative seats | Rejected |
| DAT-009 | Failed result without finding/nonfailed with finding | Rejected |
| DAT-010 | Summary/gate differs from rows | Rejected |
| DAT-011 | Finding severity differs from catalog | Rejected |
| DAT-012 | Unsupported schema major | Rejected without interpretation |
| PROV-001 | Completed reference run | profile reference; reference components only |
| PROV-002 | Request externally_verified in core | `CORE_EXTERNAL_NOT_ENABLED` |
| PROV-003 | PASS reference report | reference-only banner and external scopes unverified |
| PROV-004 | External component in core result | Result rejected |
| PROV-005 | Incomplete run | verification level integration_incomplete |
| PROV-006 | Catalog/adapter/transport version absent | Result rejected |
| CFG-001 | Canonical core config | Validates/schema exports |
| CFG-002 | Unknown/provider/remote/CI/hosting block | Rejected with exact path |
| CFG-003 | Missing cross-reference | Exact `CFG_REFERENCE_INVALID` |
| CFG-004 | Invalid ID/duplicate | Rejected |
| CFG-005 | Capability formula combinations | Exact permission AND entitlement result |
| CFG-006 | Invalid billing enumeration/range | Rejected |
| CFG-007 | Unknown-plan fallback unknown entitlement | Rejected |
| CFG-008 | Meter enabled without policy/suite | Rejected |
| CFG-009 | Seat enabled without policy | Rejected |
| CFG-010 | Invalid tick/concurrency/grace | Rejected |
| CFG-011 | `reference_core` expansion | Five canonical suites, usage excluded |
| CFG-012 | Old/external suite name | `CORE_EXTERNAL_NOT_ENABLED` |
| CFG-013 | Repeated CLI suites | Deduplicated canonical order |
| CFG-014 | CLI suites present | Override configured suites for run only |

### 3.2 CLI and lifecycle

| ID | Action | Expected |
| --- | --- | --- |
| CLI-001 | Init new interactive | Valid files and next command |
| CLI-002 | Existing files, decline overwrite | No change, exit 0 |
| CLI-003 | Noninteractive existing without force | No change, exit 2 |
| CLI-004 | Force valid replacement | Atomic replacement |
| CLI-005 | Simulate second-file write failure | Originals restored; temps removed; exit 2 |
| CLI-006 | Doctor valid | Read-only PASS, exit 0 |
| CLI-007 | Doctor invalid dependency | Named FAIL/code, exit 2, no fixtures |
| CLI-008 | Doctor `--ci` | Stable machine-readable codes plus text |
| CLI-009 | Catalog text/JSON/filter | Stable complete metadata, no mutation |
| RUN-001 | Normal reference run | Ordered phases, artifacts, cleanup |
| RUN-002 | Partial provisioning | Dependents stop; journaled fixtures cleaned |
| RUN-003 | Default Blocker | Independent scenarios continue; assertion FAIL |
| RUN-004 | Fail-fast Blocker | No new scheduling; running work settles; cleanup |
| RUN-005 | Same seed/config twice | Same normalized scenario matrix |

### 3.3 Ports and architecture

| ID | Action | Expected |
| --- | --- | --- |
| PORT-001 | Load all conforming reference ports | Contracts accepted |
| PORT-002 | Sync/async return | Both normalized |
| PORT-003 | Missing required port method | Doctor incomplete |
| PORT-004 | Malformed return | `PORT_INVALID_RETURN` |
| PORT-005 | Wrong-run actor/tenant/resource | Rejected before implementation |
| PORT-006 | Privileged auth | Rejected before execute |
| PORT-007 | External-kind transport | `CORE_EXTERNAL_NOT_ENABLED` |
| PORT-008 | Reference transport receives URL | Rejected; no socket |
| PORT-009 | Clock same seed | Same initial time/explicit ticks |
| PORT-010 | Cleanup twice | Success then no-op |
| PORT-011 | Billing/event operations return assertion status | Contract rejects unexpected field/type |
| PORT-012 | Unsupported logical operation | Typed port/scenario error, not pass |
| ARCH-001 | Dependency import graph | Core imports no concrete provider |
| ARCH-002 | Reporter run with port spies | No port call |
| ARCH-003 | Reporter attempts gate calculation | Boundary test fails |
| ARCH-004 | Reference adapter imports provider SDK | Boundary test fails |
| ARCH-005 | Concurrent independent reads | ≤configured concurrency |
| ARCH-006 | Shared aggregate mutations | Serialized in scenario order |

### 3.4 Gates, coverage and diagnostics

| ID | Input | Expected |
| --- | --- | --- |
| GATE-001 | All passed | assertion/final PASS, exit 0 |
| GATE-002 | Medium only default | failed scenario, WARN/WARN, exit 0 |
| GATE-003 | Medium promoted | FAIL/FAIL, exit 1 |
| GATE-004 | High/Blocker | FAIL/FAIL, exit 1 when execution complete |
| GATE-005 | High plus cleanup error | assertion FAIL, final INCOMPLETE, exit 2 |
| GATE-006 | Runtime error | final INCOMPLETE, no fabricated finding |
| GATE-007 | Interruption | final INCOMPLETE, exit 2 |
| COV-001 | Feature false conditional | skipped(feature_absent), gate unaffected |
| COV-002 | Feature true, dependency missing | error/missing coverage, incomplete |
| COV-003 | Dependency error | dependent skipped(dependency_error) |
| DIA-001 | Enumerate emitted codes | All exist once in owned catalog |
| DIA-002 | Emit reserved provider code from core | Test/build fails |
| DIA-003 | Diagnostic with hostile/sensitive value | Safe message, value absent |
| DIA-004 | Duplicate/unknown diagnostic code | Build fails |

### 3.5 Evidence, failure and cleanup

| ID | Action | Expected |
| --- | --- | --- |
| EVD-001 | Evidence fields allowed/not allowed | Allowed persist; unknown discarded/code |
| EVD-002 | Common password/token/key field | Redacted or rejected |
| EVD-003 | Arbitrary body/source/environment object | Never persisted |
| EVD-004 | Customer-like script text in normalized value | Escaped in HTML |
| ERR-001 | Port raises exception | Typed error; no finding; cleanup |
| ERR-002 | Report render fails | Cleanup runs; stderr summary; exit 2 |
| ERR-003 | JSON validation fails | No PASS/FAIL claim; exit 2 |
| ERR-004 | SIGINT/SIGTERM | stop scheduling, bounded settle, cleanup, partial artifact |
| ERR-005 | Scenario dependency errors | Correct skip/incomplete behavior |
| ERR-006 | Create-and-journal atomic failure | No untracked reference object |
| ERR-007 | Unexpected scenario exception | Scenario error; independent work policy preserved |
| CLN-001 | Normal cleanup, repeat | Exact deletion; second no-op |
| CLN-002 | Unrelated fixture shares prefix | Untouched |
| CLN-003 | Journal sequence/run invalid | Automated cleanup blocked |
| CLN-004 | One cleanup handler fails | Continue independent safe cleanup; partial/exit 2 |
| CLN-005 | Interruption after provisioning | All journaled fixtures attempted |
| CLN-006 | Clean command on external adapter journal | Refused as unsupported with exit 2; no call |

### 3.6 Report, packaging, limits and scope

| ID | Action | Expected |
| --- | --- | --- |
| RPT-001 | Valid prior JSON | Deterministic offline HTML |
| RPT-002 | Invalid/unsupported JSON | Exit 2; no partial output |
| RPT-003 | PASS/WARN/FAIL/INCOMPLETE/partial/cleanup states | Required hierarchy, labels and provenance |
| RPT-004 | Network disabled | Full report readable, no request |
| RPT-005 | 320/375/768/1440 widths | No essential clipping/page overflow |
| RPT-006 | Long IDs/wide tables | Wrap or labeled scroll/row groups |
| RPT-007 | Status colors disabled | Meaning remains clear in text |
| RPT-008 | Keyboard through native controls | Operable with visible focus |
| RPT-009 | Reference banner/unverified scopes | Present above results |
| OPS-001 | Artifact paths | Exact documented files only |
| OPS-002 | Structured events | Required safe fields, no arbitrary body |
| OPS-003 | Cleanup | Reports retained |
| OPS-004 | macOS/Linux smoke | CLI starts and reference run works |
| OPS-005 | Public network spy | Zero DNS/non-loopback socket/provider call |
| PKG-001 | Clean Python 3.11 wheel install | CLI works; no Node/npm/provider SDK required |
| LIM-001 | Values at hard limits | Accepted/bounded |
| LIM-002 | Above each hard limit | Config/result rejected |
| LIM-003 | Evidence exceeds per-scenario size | Typed error/truncation policy: reject item, mark scenario error |
| LIM-004 | Artifact exceeds 10 MiB | Reporting error/incomplete; no partial valid claim |
| LIM-005 | Concurrency pressure | Never exceeds 4/configured value |
| SCOPE-001 | Dependency scan | No provider SDK, HTTP client required, GitHub generator or hosting framework |
| SCOPE-002 | Source scan | No external adapter/customer arbitrary module loading |
| SCOPE-003 | Acceptance graph | No deferred backlog test gates core completion |

## 4. Scenario and defect verification

### TST-004 Scenario tests

Every applicable scenario ID in Document 01 is a functional test using its stated port dependencies, action and oracle. The correct reference target must pass. Results always include reference provenance.

### TST-005 Defect corpus

Each Blocker/High scenario has `DEF-<scenario-id>` toggle that fails the intended scenario for the intended reason, produces allowed evidence and passes when disabled. Medium toggles are required for RBAC-004, BILL-011, WEB-006, ENT-004 and, when usage is enabled, USG-005.

Unexpected collateral failures block release unless logically inseparable and recorded in the defect manifest.

## 5. Core acceptance criteria

| ID | Completion condition |
| --- | --- |
| AC-001 | Built wheel installs/runs on clean Python 3.11 without Node/npm or provider SDK. |
| AC-002 | Models, config, ports, limits and diagnostics pass strict unit/contract tests. |
| AC-003 | Results prove reference provenance and cannot claim external verification. |
| AC-004 | Init is validated, atomic, non-destructive and follows overwrite/cancel rules. |
| AC-005 | Doctor/catalog validate and expose complete core readiness/metadata without mutation. |
| AC-006 | Normal, partial, fail-fast, runtime and interruption lifecycles behave exactly as specified. |
| AC-007 | Scenario/assertion/execution/gate/cleanup/exit truth tables pass. |
| AC-008 | Correct reference target passes all selected applicable reference_core scenarios. |
| AC-009 | Every required defect toggle is caught by its intended deterministic scenario. |
| AC-010 | Journal and cleanup handle success, repeat, partial provisioning, interruption and handler failure without unrelated deletion. |
| AC-011 | Console/JSON/HTML/artifacts are valid, sanitized, offline and reporters never alter outcomes. |
| AC-012 | HTML is usable at required widths with semantic/native keyboard behavior, without making formal conformance claims. |
| AC-013 | Source/dependency/acceptance scans prove all six deferred areas remain outside core implementation and release gates. |
| AC-014 | Machine traceability contains no unknown/missing requirement, test, scenario or acceptance ID. |

## 6. Phase gates

| Phase | Mandatory verification |
| --- | --- |
| C1 | DAT-*, CFG-*, DIA-*, PKG-001 |
| C2 | PORT-*, ARCH-*, SEC-001–008, SCOPE-001/002 |
| C3 | RUN-*, GATE-*, COV-*, ERR-004/006, CLN-* |
| C4 | TEN-*, RBAC-*, ENT-* and corresponding DEF-* |
| C5 | BILL-*, WEB-*, optional USG-* and corresponding DEF-* |
| C6 | EVD-*, RPT-*, OPS-* |
| C7 | AC-001–014, machine traceability, SCOPE-003 |

`SEC-001–008` here refers to these core no-egress/security cases:

| ID | Case |
| --- | --- |
| SEC-001 | Remote URL/provider block rejected |
| SEC-002 | Public network spy remains zero |
| SEC-003 | Arbitrary adapter module path rejected |
| SEC-004 | Privileged authorization context rejected |
| SEC-005 | Wrong-run object rejected |
| SEC-006 | Unknown evidence field cannot persist |
| SEC-007 | Owner-only artifact permissions used where supported |
| SEC-008 | Reference configuration cannot select external verification |

## 7. Core definition of done

Core Development Baseline is development-ready and releasable only when:

1. C1–C7 pass.
2. All 14 core acceptance criteria pass.
3. Correct and required defective reference variants are reproducible.
4. No Blocker/High defect remains.
5. All traceability links resolve bidirectionally.
6. No unapproved deviation affects behavior, provenance or safety boundaries.
7. No deferred dependency, test or acceptance criterion blocks core.
8. Reports visibly state reference-only scope.

This completion authorizes core-engine development/release only. It does not authorize any external assurance claim.
