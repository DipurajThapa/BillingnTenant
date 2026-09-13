# SaaS Preflight Version 1.5

## Deferred Integrations and Production Backlog

This document is authoritative only for work intentionally excluded from the Core Development Baseline. It preserves the compatibility boundaries that core development must honor. Nothing here is a prerequisite for implementing or accepting the core unless a row explicitly says otherwise.

## 1. Activation policy

### BL-POL-001 Release separation

The Core Development Baseline is built and verified with bundled reference ports and in-process transport. An integration becomes part of a later release only after its backlog item is activated, its product-owner decisions are resolved, and its own contract, security, failure, recovery, and acceptance tests pass.

### BL-POL-002 Claim isolation

A core or reference result must never state or imply that Stripe, Supabase, remote HTTP, GitHub Actions, formal accessibility conformance, cPanel, or any customer system was tested. Later integration runs must identify every exercised adapter and target in `verification.components` and leave every unexercised scope in `unverified_scopes`.

### BL-POL-003 No temporary coupling

Core code must depend only on the ports and canonical models in Document 01. Provider SDK types, HTTP framework objects, CI metadata, hosting paths, and provider-specific identifiers must not enter the domain model. Provider identifiers may later be stored only as opaque adapter metadata or explicit external-reference fields added by a versioned schema migration.

### BL-POL-004 Activation gate

Activating an item requires a dated decision record naming: owner, target release, chosen provider/mode, credentials and secret owner, data classification, rate/usage limits, failure policy, required tests, and rollback method. This record belongs to the activated integration work, not the core specification.

## 2. Dependency map

| Backlog item | May start after | Blocks core? | Later verification enabled |
| --- | --- | --- | --- |
| BL-HTTP | core ports and provenance are stable | No | remote target transport |
| BL-SUPABASE | BL-HTTP safety requirements selected when remote APIs are used | No | external identity/tenant/RBAC target |
| BL-STRIPE | BL-HTTP safety requirements selected | No | external billing/event target |
| BL-GITHUB | stable CLI exit codes and artifact contract | No | CI workflow execution only |
| BL-A11Y | stable report interaction model | No | declared formal conformance target |
| BL-CPANEL | packaging/runtime requirements chosen | No | selected cPanel environment |

Dependencies apply only to later integrated verification. They do not alter the core phase gates in Document 00.

## 3. Deferred items

### BL-HTTP — Remote HTTP transport safety and hardening

**Objective:** Add a production remote `ProbeTransport` without weakening the no-egress reference profile.

**Preserved now:** `ProbeRequest` is logical rather than framework-specific; `ProbeTransport` is replaceable; authentication material is referenced by secret name, never embedded in artifacts; core config rejects remote endpoints.

**Deferred decisions and work:** allowed schemes and ports; DNS resolution and rebinding defense; private/link-local/metadata address policy; redirect policy; proxy behavior; TLS validation and optional mTLS; credential injection; request/response byte limits; content types; connect/read/total timeouts; retryable methods and idempotency; rate limits; certificate and hostname errors; allowlists; sanitized capture; operator override policy; network isolation; penetration and abuse testing.

**Activation condition:** a real remote target must be probed.

**Failure and recovery contract:** transport failures must become typed inconclusive/error outcomes, not product defects; retries must be bounded and safe; credentials and sensitive bodies must never be logged; a failed remote run must retain enough sanitized evidence to diagnose and resume or rerun safely.

**Later acceptance outcome:** an approved remote target can be exercised without reaching prohibited destinations or leaking secrets, and provenance names the transport and target. Passing in-process tests is not evidence for this item.

### BL-SUPABASE — Supabase identity, tenant and data integration

**Objective:** Implement provider adapters behind `IdentityTenantPort` and, only if selected, persistence adapters for run metadata or evidence.

**Preserved now:** canonical UUID tenant/user/membership contracts; explicit active-tenant context; authentication mode is separate from authorization; authorization tests reject service-role/admin bypass; persistence is accessed through ports; external IDs do not define domain behavior.

**Deferred decisions and work:** whether Supabase supplies authentication, database, or both; project topology and regions; schema and migration ownership; RLS policies; JWT issuer/audience and key rotation; service-role use; invitation and membership lifecycle; data residency, retention and deletion; backups; local/test environment; connection pooling; quotas; secrets; privacy/compliance; provider outage behavior; integration and security tests.

**Activation condition:** the product must verify or persist against a Supabase project.

**Failure and recovery contract:** unavailable or unverifiable Supabase dependencies produce an inconclusive/error integration result, never a reference PASS; partial resources must be journaled for exact cleanup; privileged credentials must not be used to prove end-user authorization behavior.

**Later acceptance outcome:** selected tenant/RBAC scenarios pass through the activated adapter with least-privilege identities, isolation is demonstrated against a real project, and provenance names the project alias and adapter without exposing secrets.

### BL-STRIPE — Stripe billing and webhook integration

**Objective:** Implement billing and event-delivery adapters behind `BillingStatePort` and `EventDeliveryPort`.

**Preserved now:** internal plan/entitlement identifiers are separate from provider price/product identifiers; billing projections are canonical; event IDs support deduplication; event order and terminal state are explicit; monetary values use integer minor units; reference billing/webhook suites do not claim provider verification.

**Deferred decisions and work:** Checkout versus other purchase flow; Billing Portal; products/prices/currencies; trials, tax, discounts, proration and cancellation policy; subscription status mapping; webhook endpoint and signature scheme; event selection and API version; idempotency storage; replay window; retry handling; test clocks; customer/account ownership; reconciliation; refund/dispute behavior; secrets; rate limits; privacy/compliance; operational alerts; Stripe-specific contract and end-to-end tests.

**Activation condition:** a real Stripe test or live environment must be verified.

**Failure and recovery contract:** webhook receipt and processing must be independently idempotent; invalid signatures are rejected without state mutation; out-of-order and duplicate events converge to the correct terminal projection; provider unavailability yields typed integration failure and supports reconciliation.

**Later acceptance outcome:** approved billing flows and webhook scenarios pass against the named Stripe environment, with provider-derived evidence and no false live-mode claim.

### BL-GITHUB — GitHub Actions automation

**Objective:** Run the stable CLI in CI and publish its artifacts without making CI a domain dependency.

**Preserved now:** deterministic noninteractive commands; documented exit codes; configuration and result schemas; artifacts use relative paths; package installs from a built wheel; no workflow metadata is required by the engine.

**Deferred decisions and work:** workflow triggers; supported runner matrix; Python matrix; dependency caching; permissions; OIDC versus stored secrets; artifact retention; annotations; branch protection; concurrency; fork/pull-request secret policy; release publishing; supply-chain attestations; action pinning and update policy.

**Activation condition:** a repository and CI policy are selected.

**Failure and recovery contract:** workflow failure must preserve available sanitized artifacts; missing secrets must skip or fail only the integration job as configured and must not be reported as a product defect; reruns must not corrupt prior evidence.

**Later acceptance outcome:** the selected workflow installs the built artifact, runs the intended profile, maps exit status correctly, and publishes provenance-preserving output.

### BL-A11Y — Formal accessibility conformance

**Objective:** Select and verify a formal accessibility target for the HTML report and any later interactive UI.

**Preserved now:** semantic HTML landmarks and tables; keyboard-operable native controls; visible focus; text status labels independent of color; ordered heading structure; responsive reflow; no required network or client-side framework. These are core usability requirements, not a conformance claim.

**Deferred decisions and work:** target standard and level; supported browser/assistive-technology matrix; automated rule set; manual keyboard and screen-reader protocol; contrast measurements; zoom/reflow thresholds beyond current responsive acceptance; VPAT or other documentation; remediation severity and release gate.

**Activation condition:** the product owner selects a formal standard or a release requires a conformance claim.

**Failure and recovery contract:** conformance failures block only the formal claim/release gate defined at activation; reports remain usable with the core semantic fallback while defects are tracked.

**Later acceptance outcome:** independent automated and manual evidence supports the declared standard, scope, platform matrix, and exceptions. Core responsive tests alone cannot support this claim.

### BL-CPANEL — cPanel-specific deployment

**Objective:** Package and operate the product in a selected cPanel environment without coupling the engine to hosting layout.

**Preserved now:** Python package entry point; relative/configurable workspace and artifact paths; no daemon, external database, cron, or web server required by core; no absolute hosting paths in domain logic; clean-wheel smoke test.

**Deferred decisions and work:** cPanel version and provider; Python/runtime availability; Passenger/WSGI/ASGI need, if any; shell and cron access; filesystem quotas and permissions; process/time limits; virtual environment and install procedure; environment variables and secrets; writable paths; log rotation; backups; TLS/domain routing; deployment, rollback and health checks; provider-specific constraints.

**Activation condition:** a target cPanel account and intended execution mode are known.

**Failure and recovery contract:** deployment failure must leave the prior installed version recoverable; host-specific diagnostics must distinguish unsupported runtime, permission, quota and timeout failures; sensitive configuration must not enter web-accessible paths or reports.

**Later acceptance outcome:** install, doctor, reference run, report access, cleanup and rollback succeed in the named environment within its documented limits.

## 4. Shared later-integration rules

### BL-SHARED-001 Adapter trust

Customer or provider adapters are not arbitrary in-process plugins by default. Before enabling third-party adapter code, the activated design must choose a trust model: reviewed trusted package, isolated process, or remote service. The choice must define version compatibility, time/resource limits, secret access, cancellation, error mapping and evidence sanitization.

### BL-SHARED-002 Schema evolution

Later integrations may add optional, namespaced fields or new schema majors. They must not reinterpret existing core fields, change reference scenario oracles, or make provider configuration mandatory for the reference profile.

### BL-SHARED-003 Integrated release gate

An Integrated Foundational MVP may be declared only when every integration named in that release has: an activated decision record; implemented adapter contracts; integration-specific security and failure tests; cleanup/recovery evidence; and accurate `external_verified` provenance. Integrations not named in the release remain explicitly unverified.

### BL-SHARED-004 Backlog traceability

When activated, each item must receive requirement, test and acceptance IDs within that integration's implementation plan. Until activation, this backlog item and its preserved-boundary clauses are the sole source of truth; speculative detailed tests must not be added to the core suite.

## 5. Deferred status

All six items are **non-blocking deferred work** for Version 1.5 Core Development Baseline. No unresolved decision in this document prevents core implementation or core acceptance. Each becomes a release blocker only after it is explicitly activated for a named later release.
