# INC-001: Stateful reference scenario execution

**Status:** Complete
**Requirements:** PRD-006, WF-003, ARC-003–004, STA-003–004, SCN-TEN, SCN-RBAC,
SCN-BILL, SCN-WEB, SCN-ENT, SCN-USG

## Delivered behavior

- The engine passes validated core configuration into every applicable reference scenario.
- Scenario oracles execute isolated stateful tenant, authorization, billing, event, entitlement and
  usage actions; they no longer return PASS merely because no defect flag is present.
- Each scenario observes normalized behavior and returns one deterministic assertion outcome.
- Per-scenario deep copies prevent one scenario's mutations from contaminating another scenario.
- Feature-disabled scenarios remain explicit `skipped(feature_absent)` results.
- Runtime exceptions remain errors, create no findings and preserve incomplete coverage behavior.
- Defect toggles alter the behavior under test and are evaluated through the same oracle as the
  correct target.

## Validation evidence

- All 42 scenarios pass with seat and usage features enabled.
- Each of 42 isolated defect variants fails only its matching scenario.
- Default `reference_core` passes 35 required/applicable scenarios and reports BILL-011 as one
  feature-absent conditional skip.
- Alternative trial, past-due, upgrade, downgrade, cancellation and reactivation policies pass.
- A runtime cross-tenant leak injected without a defect flag is detected by TEN-001.
- Full repository suite: 71 passed, no skips or expected failures.
- Ruff lint: passed.
- Built-wheel journey: init, doctor, reference_core run, report regeneration and clean passed.

## Claim boundary

This increment proves bundled reference behavior only. It does not verify Stripe, a customer
system, production Supabase, cPanel, or formal accessibility conformance.

## Next dependency

INC-002 will complete fixture provisioning/journaling, interruption recovery and lifecycle state
evidence before remaining phase gates can be closed.
