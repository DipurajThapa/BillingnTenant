"""Complete provider-neutral port implementations for the bundled reference target."""

from __future__ import annotations

from datetime import UTC, datetime

from preflight.lifecycle import FixtureJournal
from preflight.models import ActorRef, FixtureSet, ResourceRef
from preflight.reference import ReferenceTarget


class ReferenceFixturePort:
    contract_version = "1.0"

    def __init__(self, target: ReferenceTarget, journal: FixtureJournal) -> None:
        self.target = target
        self.journal = journal

    def provision(self, run_id: str, requirements: list[str]) -> FixtureSet:
        resources: list[ResourceRef] = []
        for index, requirement in enumerate(dict.fromkeys(requirements), start=1):
            if self.target.provision_error_at == index:
                raise RuntimeError("PORT_INVALID_RETURN")
            resource = ResourceRef(
                kind="scenario_fixture",
                externalId=f"{run_id}-{index}",
                runId=run_id,
                createdAt=datetime.now(UTC),
                metadata={"alias": requirement},
            )
            # Creation and registration share this synchronous critical section. If
            # registration fails, creation is rolled back before the exception escapes.
            self.target.created_fixture_ids.add(resource.external_id)
            try:
                self.journal.register(resource)
            except Exception:
                self.target.created_fixture_ids.discard(resource.external_id)
                raise
            resources.append(resource)
        return FixtureSet(runId=run_id, tenants={}, actors={}, resources=resources)

    def cleanup(self, run_id: str, fixtures: FixtureSet) -> None:
        if fixtures.run_id != run_id:
            raise ValueError("PORT_WRONG_RUN")
        failures = 0
        for resource in reversed(fixtures.resources):
            self.journal.cleanup_attempted(resource)
            if resource.external_id in self.target.cleanup_fixture_fail_ids:
                self.journal.cleanup_failed(resource)
                failures += 1
                continue
            self.target.created_fixture_ids.discard(resource.external_id)
            self.journal.cleaned(resource)
        if failures:
            raise RuntimeError("CLN_PARTIAL")


class ReferenceIdentityTenantPort:
    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def auth_context(self, actor: ActorRef):
        from preflight.models import AuthContext

        return AuthContext(mode="actor_session", actorId=actor.id, credentialHandle="reference")

    def switch_tenant(self, actor_id: str, tenant_id: str):
        from preflight.models import AuthContext

        if not self.target.switch_tenant(actor_id, tenant_id):
            raise ValueError("PORT_INVALID_RETURN")
        return AuthContext(mode="actor_session", actorId=actor_id, credentialHandle="reference")

    def set_role(self, actor_id: str, tenant_id: str, role: str) -> None:
        self.target.set_role(actor_id, tenant_id, role)

    def remove_membership(self, actor_id: str, tenant_id: str) -> None:
        self.target.remove_membership(actor_id, tenant_id)

    def execute(self, auth, request):
        return self.target.execute(auth, request)


class ReferenceBillingStatePort:
    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def bind_account(self, tenant_id, account_id):
        return self.target.bind_account(tenant_id, account_id)

    def get_binding(self, tenant_id):
        return self.target.account_bindings.get(tenant_id)

    def create_subscription(self, tenant_id, plan, trial_days):
        return self.target.create_subscription(tenant_id, plan, trial_days)

    def transition(self, tenant_id, action, target_plan=None):
        return self.target.transition(tenant_id, action, target_plan)

    def projection(self, tenant_id):
        return self.target.projection(tenant_id)

    def entitlements(self, tenant_id):
        return self.target.entitlements(tenant_id)


class ReferenceEventDeliveryPort:
    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def deliver(self, event, auth):
        return self.target.deliver(event, auth)

    def current_object_version(self, object_id):
        return self.target.versions.get(object_id, 0)

    def side_effect_count(self, tenant_id, counter):
        return self.target.side_effects.get((tenant_id, counter), 0)

    def fail_next_delivery(self, event_type):
        self.target.fail_next_event_type = event_type

    def restart(self):
        return "reference-restarted"


class ReferenceUsagePort:
    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def record(self, tenant_id, meter, quantity, idempotency_key):
        return self.target.record_usage(tenant_id, meter, quantity, idempotency_key)

    def projection(self, tenant_id, meter):
        return self.target.usage_projection(tenant_id, meter)


class ReferenceClockPort:
    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def now(self):
        return self.target.clock

    def tick(self, count=1):
        return self.target.tick(count)


class ReferenceProbeTransport:
    name = "in-process-reference"
    version = "1.0"
    kind = "reference"

    def __init__(self, target: ReferenceTarget) -> None:
        self.target = target

    def execute(self, auth, request):
        return self.target.execute(auth, request)


def build_reference_ports(target: ReferenceTarget, journal: FixtureJournal) -> dict[str, object]:
    return {
        "FixturePort": ReferenceFixturePort(target, journal),
        "IdentityTenantPort": ReferenceIdentityTenantPort(target),
        "BillingStatePort": ReferenceBillingStatePort(target),
        "EventDeliveryPort": ReferenceEventDeliveryPort(target),
        "UsagePort": ReferenceUsagePort(target),
        "ProbeTransport": ReferenceProbeTransport(target),
        "ClockPort": ReferenceClockPort(target),
    }
