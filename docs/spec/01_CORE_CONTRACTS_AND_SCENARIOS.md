# SaaS Preflight Version 1.5

## Core Contracts and Reference Scenario Catalog

Authoritative for current core models, configuration, ports, scenario definitions and diagnostics. Read with [the primary specification](00_PRIMARY_PRODUCT_SPEC.md).

## 1. Contract rules

### DATA-001 Modeling

- Strict Pydantic v2 models; unknown fields rejected.
- `JsonValue` is Pydantic's recursive JSON scalar/array/object type; binary values and arbitrary Python objects are invalid.
- Configuration and result schemas exported as JSON Schema.
- UTC RFC 3339 timestamps; monotonic integer milliseconds for duration.
- Engine identifiers match `^[a-zA-Z][a-zA-Z0-9_-]{2,63}$`.
- Decimal values serialize as strings; sets as sorted unique arrays.
- Mutable fields use factories.
- Core models contain no Stripe, Supabase, GitHub or hosting-specific field.

### DATA-002 Fixtures and actors

```python
class ResourceRef(BaseModel):
    kind: str
    external_id: str
    tenant_id: str | None = None
    owner_actor_id: str | None = None
    run_id: str
    created_at: datetime
    metadata: dict[str, str] = Field(default_factory=dict)

class MembershipRef(BaseModel):
    tenant_id: str
    role: str
    active: bool = True

class ActorRef(BaseModel):
    id: str
    alias: str
    memberships: list[MembershipRef]
    active_tenant_id: str

class TenantFixture(BaseModel):
    id: str
    alias: str
    resources: dict[str, ResourceRef]

class FixtureSet(BaseModel):
    run_id: str
    tenants: dict[str, TenantFixture]
    actors: dict[str, ActorRef]
    resources: list[ResourceRef]
```

Invariants: all run IDs match; dictionary key equals alias; active tenant is an active membership; every reference belongs to the set; resource IDs are unique within kind.

### DATA-003 Authentication and requests

```python
AuthMode = Literal["actor_session", "public", "signed_event"]

class AuthContext(BaseModel):
    mode: AuthMode
    actor_id: str | None = None
    credential_handle: str | None = None
    privileged: bool = False

class ProbeRequest(BaseModel):
    operation: str
    resource_kind: str | None = None
    resource_id: str | None = None
    input: dict[str, JsonValue] = Field(default_factory=dict)

class Observation(BaseModel):
    outcome: Literal["allowed", "denied", "success", "not_found", "invalid", "conflict"]
    state: dict[str, JsonValue] = Field(default_factory=dict)
    changed: bool
    error_code: str | None = None
```

Rules:

- `actor_session` requires a current-run `actor_id`, a non-empty opaque `credential_handle` and `privileged=false`.
- `public` has no actor or credential.
- `signed_event` has no actor and requires an engine/reference-generated opaque credential handle.
- `privileged=true` is rejected for authorization scenarios.
- Credentials are never stored in evidence/result.
- ProbeRequest is logical, not HTTP-specific. Future HTTP transport maps it without changing scenario logic.
- `Observation.changed` reports whether durable reference state changed. `error_code` is required only for `invalid` or `conflict`; it is absent for the other outcomes. State contains only normalized allowlisted values.

### DATA-004 Billing, events and usage

```python
class BillingProjection(BaseModel):
    tenant_id: str
    plan: str | None
    status: Literal["trialing","active","past_due","canceled","inactive","unknown"]
    period_end: datetime | None
    cancel_at_period_end: bool

class EventEnvelope(BaseModel):
    event_id: str
    event_type: str
    object_id: str
    object_version: int
    occurred_at: datetime
    state: dict[str, JsonValue]

class EventReceipt(BaseModel):
    event_id: str
    outcome: Literal["applied", "duplicate", "stale", "ignored", "rejected", "failed"]
    object_version: int | None = None
    state_changed: bool
    error_code: str | None = None

class UsageProjection(BaseModel):
    tenant_id: str
    meter: str
    quantity: Decimal
    period_start: datetime
    period_end: datetime

class SeatProjection(BaseModel):
    tenant_id: str
    active_memberships: int
    pending_invitations: int
    billable_quantity: int
```

Event `object_version` is the reference ordering authority. Future integrations may map provider state to it but must not change the stale-state oracle. Usage is finite/non-negative. Seat values are non-negative integers.

Event receipt rules: `applied` changes state; `duplicate`, `stale`, `ignored` and `rejected` do not; `failed` may be retried but has no committed state change. `rejected` and `failed` require an error code. The receipt event ID must equal the envelope event ID.

### DATA-005 Results and provenance

```python
class ComponentProvenance(BaseModel):
    name: str
    version: str
    kind: Literal["reference", "external"]

class Evidence(BaseModel):
    type: str
    source: str
    timestamp: datetime
    payload: dict[str, JsonValue]

class ScenarioResult(BaseModel):
    test_id: str
    suite: str
    severity: Literal["blocker","high","medium","info"]
    applicability: Literal["required","conditional","optional","not_applicable"]
    status: Literal["passed","failed","skipped","error"]
    duration_ms: int
    expected: str
    observed: str
    skip_reason: str | None = None
    error_code: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    finding_id: str | None = None

class Finding(BaseModel):
    id: str
    scenario_id: str
    severity: Literal["blocker", "high", "medium", "info"]
    impact: str
    expected: str
    observed: str
    reproduction_steps: list[str]
    remediation_hint: str
    evidence: list[Evidence]

class RunSummary(BaseModel):
    passed: int
    failed: int
    skipped: int
    error: int
    findings: int

class RunResult(BaseModel):
    schema_version: Literal["1.0"]
    run_id: str
    tool_version: str
    catalog_version: str
    execution_profile: Literal["reference", "external"]
    verification_level: Literal["reference_verified","integration_incomplete","externally_verified"]
    components: list[ComponentProvenance]
    verified_scopes: list[str]
    unverified_scopes: list[str]
    started_at: datetime
    finished_at: datetime | None
    config_hash: str
    git_sha: str | None
    selected_suites: list[str]
    execution_status: Literal["completed", "error", "interrupted"]
    assertion_gate_status: Literal["PASS", "WARN", "FAIL"]
    gate_status: Literal["PASS", "WARN", "FAIL", "INCOMPLETE"]
    cleanup_status: Literal["not_required", "completed", "partial", "failed"]
    summary: RunSummary
    results: list[ScenarioResult]
    findings: list[Finding]
    missing_coverage: list[str]
    diagnostics: list[str]
```

Core invariants:

- profile is reference; verification is reference_verified only when final gate is PASS/WARN/FAIL with complete execution, otherwise integration_incomplete;
- all components are `reference`;
- external providers/remote targets/CI/a11y/hosting appear in unverified scopes;
- exactly one result per selected visible scenario;
- failed has exactly one finding; other statuses none;
- skipped has reason; error has code;
- counts and gates recompute exactly from rows;
- finding severity equals catalog.

## 2. Core configuration

### CFG-001 Canonical file

Path: `.preflight/core.yml`

```yaml
schemaVersion: "1.0"
profile: reference
projectLabel: sample-saas
artifactDirectory: .preflight/runs
features:
  multiOrgUsers: true
  membershipManagement: true
  seatBilling: false
  meteredUsage: false
roles: [owner, admin, member]
rolePermissions:
  owner: [billing_settings, member_management, export]
  admin: [billing_settings, member_management, export]
  member: [export]
plans:
  free: {entitlements: [dashboard]}
  pro: {entitlements: [dashboard, export, generation]}
capabilities:
  export:
    requiredPermission: export
    requiredEntitlement: export
    operation: export
  billing_settings:
    requiredPermission: billing_settings
    requiredEntitlement: null
    operation: billing_settings
billingPolicy:
  trialPlan: pro
  trialDays: 14
  trialEndBehavior: inactive
  pastDueBehavior: grace_period
  gracePeriodSeconds: 259200
  upgradeEffective: immediate
  downgradeEffective: period_end
  cancelBehavior: end_of_period
  reactivationBehavior: restore_selected_plan
  unknownPlanEntitlements: []
consistency:
  authorizationPropagationTicks: 1
  billingConvergenceTicks: 3
suites:
  enabled: [reference_core]
execution:
  maxConcurrency: 4
  interruptGraceSeconds: 10
policy:
  failMedium: false
```

If metering enabled:

```yaml
usagePolicy:
  meter: api_calls
  quotasByPlan: {free: "100", pro: "10000"}
  quotaBoundary: deny_above
  planChangeTreatment: preserve_period_usage
```

If seats enabled:

```yaml
seatPolicy:
  minimumQuantity: 1
  pendingInvitationsCount: false
```

### CFG-002 Validation

- Unknown fields fail with exact YAML path.
- `profile` must be reference; provider/remote/CI/hosting keys are rejected.
- Project/role/plan/permission/entitlement/capability IDs use the ID pattern and are unique.
- Every rolePermissions key is a role; capability references resolve.
- Expected capability access is `(no required permission OR role has it) AND (no required entitlement OR plan has it)`.
- Trial plan exists; trial days 1–365.
- Trial end: inactive/free/active_selected_plan; free requires free plan.
- Past due: immediate_suspend/grace_period/retain_access; grace 0–2,592,000 only for grace mode.
- Upgrade/downgrade: immediate/period_end; cancel: immediate/end_of_period; reactivation: restore_selected_plan/require_new_subscription.
- Unknown plan fallback defaults empty and may reference only declared entitlements.
- Ticks are integers 0–100. A reference mutation advances one logical tick unless scenario specifies otherwise.
- Concurrency 1–4; interruption grace 1–60.
- Metering requires usage policy and usage suite must be explicitly selected.
- Seat billing requires seat policy.
- `reference_core` excludes usage.

### CFG-003 Suites

Canonical order and names:

1. `tenant_reference`
2. `rbac_reference`
3. `billing_reference`
4. `webhook_reference`
5. `entitlement_reference`
6. `usage_reference`

`reference_core` aliases 1–5. Names without `_reference`, `external` profiles and `externally_verified` requests fail with `CORE_EXTERNAL_NOT_ENABLED`.

## 3. Provider-neutral ports

All methods may be sync or async; loader normalizes them. Reference ports are bundled/trusted and accept current-run objects only.

### PORT-001 FixturePort

```python
class FixturePort(Protocol):
    contract_version: Literal["1.0"]
    def provision(self, run_id: str, requirements: list[str]) -> FixtureSet: ...
    def cleanup(self, run_id: str, fixtures: FixtureSet) -> None: ...
```

Provision minimum requested fixture types. Create-and-journal is atomic in reference implementation. Cleanup is exact and idempotent.

### PORT-002 IdentityTenantPort

```python
class IdentityTenantPort(Protocol):
    def auth_context(self, actor: ActorRef) -> AuthContext: ...
    def switch_tenant(self, actor_id: str, tenant_id: str) -> AuthContext: ...
    def set_role(self, actor_id: str, tenant_id: str, role: str) -> None: ...
    def remove_membership(self, actor_id: str, tenant_id: str) -> None: ...
    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation: ...
```

### PORT-003 BillingStatePort

```python
class BillingStatePort(Protocol):
    def bind_account(self, tenant_id: str, account_id: str) -> None: ...
    def get_binding(self, tenant_id: str) -> str | None: ...
    def create_subscription(self, tenant_id: str, plan: str, trial_days: int | None) -> BillingProjection: ...
    def transition(self, tenant_id: str, action: str, target_plan: str | None = None) -> BillingProjection: ...
    def projection(self, tenant_id: str) -> BillingProjection: ...
    def entitlements(self, tenant_id: str) -> list[str]: ...
```

### PORT-004 EventDeliveryPort

```python
class EventDeliveryPort(Protocol):
    def deliver(self, event: EventEnvelope, auth: AuthContext) -> EventReceipt: ...
    def current_object_version(self, object_id: str) -> int: ...
    def side_effect_count(self, tenant_id: str, counter: str) -> int: ...
    def fail_next_delivery(self, event_type: str) -> None: ...
    def restart(self) -> str: ...
```

Reference signed_event auth validates an engine-generated handle. It models authenticity behavior without claiming a real provider signature.

### PORT-005 UsagePort

```python
class UsagePort(Protocol):
    def record(self, tenant_id: str, meter: str, quantity: Decimal, idempotency_key: str) -> None: ...
    def projection(self, tenant_id: str, meter: str) -> UsageProjection: ...
```

### PORT-006 ProbeTransport

```python
class ProbeTransport(Protocol):
    name: str
    version: str
    kind: Literal["reference", "external"]
    def execute(self, auth: AuthContext, request: ProbeRequest) -> Observation: ...
```

Core accepts only `kind=reference`. The bundled in-process transport invokes reference target functions directly. It cannot accept URLs or open sockets.

### PORT-007 ClockPort

```python
class ClockPort(Protocol):
    def now(self) -> datetime: ...
    def tick(self, count: int = 1) -> datetime: ...
```

Reference clock starts at fixed UTC time per run seed and advances only explicitly.

## 4. Scenario model and applicability

```python
class ScenarioDefinition(BaseModel):
    id: str
    title: str
    suite: str
    severity: Literal["blocker","high","medium","info"]
    coverage: Literal["required","conditional","optional"]
    feature_guard: str | None
    fixture_dependencies: list[str]
    port_dependencies: list[str]
    scenario_dependencies: list[str]
    evidence_allowlist: list[str]
```

- Feature false: skipped(feature_absent), not incomplete.
- Feature true and missing dependency: error/missing coverage, incomplete.
- Dependency error: skipped(dependency_error), incomplete if required.
- Failed assertion does not skip a dependent scenario when valid state remains.
- Independent scenarios continue unless fail-fast.

## 5. Reference scenario catalog

Aliases: TA/TB tenants, AO/AA/AM A owner/admin/member, MA multi-org actor. Evidence is limited to aliases, logical operation, normalized status/state, version and counter.

### SCN-TEN Tenant isolation

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| TEN-001 Blocker | required | AM reads B exact resource; denied and no B data |
| TEN-002 Blocker | required | AM lists A; intersection with B IDs is empty |
| TEN-003 Blocker | required | AM creates with B tenant; rejected/no record or owner overwritten to A |
| TEN-004 Blocker | required | AM reassigns A resource to B; persisted owner remains A |
| TEN-005 Blocker | required | AM updates/deletes B resource; B before/after unchanged and present |
| TEN-006 High | multiOrgUsers | MA switches A→B; B context correct and no stale A data |
| TEN-007 High | membershipManagement | remove A membership, reuse old auth; denied within configured ticks |

Ports: Fixture, IdentityTenant, Clock. Defect toggles: cross-read, list-leak, trust-client-tenant, owner-reassign, foreign-mutate, stale-context, stale-membership.

### SCN-RBAC Role authorization

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| RBAC-001 High | required | member direct admin operation denied/no effect; allowed role succeeds |
| RBAC-002 High | required | non-billing role requests billing settings; denied and no account action |
| RBAC-003 High | required | admin allowed, downgraded, then denied within ticks |
| RBAC-004 Medium | membershipManagement | unauthorized invite/remove denied and membership unchanged |
| RBAC-005 High | multiOrgUsers | same user admin A/member B; admin action allowed A, denied B |

Ports: Fixture, IdentityTenant, BillingState where RBAC-002 observes no billing action, Clock.

### SCN-BILL Billing-state logic

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| BILL-001 High | required | bind reference account/readback; subscribe; active plan and entitlements converge |
| BILL-002 High | required | create trial; status trialing and trial-plan entitlements |
| BILL-003 High | required | advance trial boundary; state/access equals trialEndBehavior |
| BILL-004 High | required | upgrade; new entitlements at configured boundary |
| BILL-005 High | required | downgrade; premium retained only until boundary |
| BILL-006 High | required | cancel; access transition equals policy |
| BILL-007 High | required | failed renewal; access before/at/after grace equals policy |
| BILL-008 High | required | recover; paid access and effect restored exactly once |
| BILL-009 High | required | reactivate; state/access equals policy |
| BILL-010 High | multiOrgUsers | active tenant account action uses its binding, never other tenant |
| BILL-011 Medium | seatBilling | billable quantity equals seat formula |
| BILL-012 High | required | unknown plan grants subset of explicit fallback, empty default |

Ports: Fixture, BillingState, IdentityTenant as applicable, Clock. All results state reference billing logic only.

### SCN-WEB Event-state resilience

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| WEB-001 Blocker | required | identical event ID twice; second side-effect delta zero |
| WEB-002 High | required | distinct IDs, same type/object/version; one logical effect |
| WEB-003 Blocker | required | newer version then older; final projection remains newest |
| WEB-004 High | required | first delivery fails, retry; final correct and one effect |
| WEB-005 High | required | invalid reference signed-event handle; rejected/no effect |
| WEB-006 Medium | required | irrelevant event type; no state mutation or error |
| WEB-007 High | required | process, restart reference port, replay; no second effect |

Ports: Fixture, EventDelivery, Clock. These test generic event logic, not Stripe webhook signing or delivery.

### SCN-ENT Capability enforcement

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| ENT-001 High | required | every plan×capability equals capability formula |
| ENT-002 High | required | every relevant role×plan×capability equals formula |
| ENT-003 High | required | downgrade with same auth loses premium access at boundary |
| ENT-004 Medium | required | unknown entitlement enables nothing and is reported |
| ENT-005 High | required | direct paid capability denied to unentitled actor/no effect |

Ports: Fixture, IdentityTenant, BillingState, Clock.

### SCN-USG Usage logic

| ID/severity | Applicability | Action and oracle |
| --- | --- | --- |
| USG-001 High | meteredUsage + selected | distinct TA/TB quantities remain isolated |
| USG-002 High | meteredUsage + selected | duplicate idempotency key counts once |
| USG-003 High | meteredUsage + selected | below/at/above quota equals boundary policy |
| USG-004 High | meteredUsage + selected | plan-change total/quota treatment equals policy |
| USG-005 Medium | meteredUsage + selected | explicitly stale projection causes no irreversible decision |
| USG-006 High | meteredUsage + selected | mismatched tenant attribution rejected; wrong delta zero |

Ports: Fixture, Usage, BillingState, Clock.

## 6. Evidence, findings and journal

### EVD-001 Evidence

Scenario definition contains explicit field allowlist. Unknown evidence field is discarded and diagnostic emitted. Core permits fixture aliases/IDs, logical action, normalized status/state, counters, versions, timestamps and stable hashes. It never stores arbitrary request/event bodies.

### EVD-002 Finding

One failed scenario creates one finding with stable finding ID, scenario ID, fixed severity, impact, expected, observed, reproduction steps using reference operations, remediation hint and evidence. Error/skip creates no finding.

### JRN-001 Journal

JSONL events: `run_created`, `fixture_registered`, `cleanup_attempted`, `fixture_cleaned`, `cleanup_failed`. Each includes schema version, run ID, sequence, UTC time and safe ResourceRef where applicable. Sequence is contiguous; run constant; duplicate registration must be identical. Invalid sequence/run/schema blocks automated cleanup.

## 7. Core diagnostic ownership

| Namespace | Owner/use |
| --- | --- |
| `CFG_*` | core config/schema |
| `CORE_*` | profile, lifecycle and unsupported external functionality |
| `PORT_*` | provider-neutral port contract |
| `SCN_*` | scenario dependency/runtime |
| `EVD_*` | evidence/report-input privacy |
| `CLN_*` | journal/cleanup |
| `RPT_*` | JSON/HTML rendering |

Minimum codes: `CFG_INVALID`, `CFG_UNKNOWN_FIELD`, `CFG_REFERENCE_INVALID`, `CFG_UNSUPPORTED_SCHEMA`, `CORE_EXTERNAL_NOT_ENABLED`, `CORE_INTERRUPTED`, `PORT_MISSING`, `PORT_INVALID_RETURN`, `PORT_WRONG_RUN`, `PORT_PRIVILEGED_AUTH`, `SCN_DEPENDENCY_ERROR`, `SCN_UNEXPECTED`, `EVD_FIELD_REJECTED`, `EVD_SENSITIVE_VALUE`, `CLN_JOURNAL_INVALID`, `CLN_PARTIAL`, `CLN_FAILED`, `RPT_SCHEMA_INVALID`, `RPT_RENDER_FAILED`.

Provider/deferred namespaces `STR_*`, `SUP_*`, `HTTP_*`, `GHA_*`, `A11Y_*`, `CPANEL_*` are reserved and not emitted by core.

## 8. Hard limits

Core configurable ceilings: concurrency 4, interruption grace 60 seconds, roles 20, plans 20, capabilities 100, scenario definitions 200, evidence items per scenario 50, evidence serialized size per scenario 64 KiB, total JSON artifact 10 MiB. Defaults: concurrency 4, grace 10 seconds. Above-ceiling config fails before execution.

