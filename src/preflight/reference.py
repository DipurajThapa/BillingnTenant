"""Deterministic local reference implementation and defect corpus."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from preflight.models import (
    AuthContext,
    BillingProjection,
    EventEnvelope,
    EventReceipt,
    UsageProjection,
)

if TYPE_CHECKING:
    from preflight.config import CoreConfig


@dataclass
class ReferenceTarget:
    defects: set[str] = field(default_factory=set)
    errors: set[str] = field(default_factory=set)
    cleanup_error: bool = False
    resources: dict[str, tuple[str, str]] = field(
        default_factory=lambda: {"a1": ("TA", "A"), "b1": ("TB", "B")}
    )
    roles: dict[tuple[str, str], str] = field(
        default_factory=lambda: {
            ("AM", "TA"): "member",
            ("AO", "TA"): "owner",
            ("MA", "TA"): "admin",
            ("MA", "TB"): "member",
        }
    )
    plans: dict[str, str] = field(default_factory=lambda: {"TA": "pro", "TB": "free"})
    active_tenants: dict[str, str] = field(
        default_factory=lambda: {"AM": "TA", "AO": "TA", "MA": "TA"}
    )
    account_bindings: dict[str, str] = field(default_factory=dict)
    subscriptions: dict[str, BillingProjection] = field(default_factory=dict)
    events: dict[str, EventReceipt] = field(default_factory=dict)
    versions: dict[str, int] = field(default_factory=dict)
    side_effects: dict[tuple[str, str], int] = field(default_factory=dict)
    usage: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    usage_keys: set[tuple[str, str, str]] = field(default_factory=set)
    clock: datetime = field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=UTC))

    def _active_role(self, actor_id: str) -> tuple[str, str] | None:
        tenant_id = self.active_tenants.get(actor_id)
        role = self.roles.get((actor_id, tenant_id)) if tenant_id else None
        return (tenant_id, role) if tenant_id and role else None

    def switch_tenant(self, actor_id: str, tenant_id: str) -> bool:
        if (actor_id, tenant_id) not in self.roles:
            return False
        self.active_tenants[actor_id] = tenant_id
        return True

    def set_role(self, actor_id: str, tenant_id: str, role: str) -> None:
        self.roles[(actor_id, tenant_id)] = role

    def remove_membership(self, actor_id: str, tenant_id: str) -> None:
        self.roles.pop((actor_id, tenant_id), None)

    def read_resource(self, actor_id: str, resource_id: str) -> tuple[str, str] | None:
        context = self._active_role(actor_id)
        resource = self.resources.get(resource_id)
        if not context or not resource or resource[0] != context[0]:
            return None
        return resource

    def list_resources(self, actor_id: str) -> list[str]:
        context = self._active_role(actor_id)
        if not context:
            return []
        return sorted(key for key, value in self.resources.items() if value[0] == context[0])

    def create_resource(self, actor_id: str, resource_id: str, requested_tenant: str) -> bool:
        context = self._active_role(actor_id)
        if not context or resource_id in self.resources:
            return False
        self.resources[resource_id] = (context[0], actor_id)
        return self.resources[resource_id][0] == context[0]

    def mutate_resource(self, actor_id: str, resource_id: str, *, delete: bool = False) -> bool:
        if self.read_resource(actor_id, resource_id) is None:
            return False
        if delete:
            del self.resources[resource_id]
        return True

    def permitted(self, actor_id: str, permissions: dict[str, list[str]], permission: str) -> bool:
        context = self._active_role(actor_id)
        return bool(context and permission in permissions.get(context[1], []))

    def bind_account(self, tenant_id: str, account_id: str) -> None:
        self.account_bindings[tenant_id] = account_id

    def get_binding(self, tenant_id: str) -> str | None:
        return self.account_bindings.get(tenant_id)

    def create_subscription(
        self, tenant_id: str, plan: str, trial_days: int | None = None
    ) -> BillingProjection:
        projection = BillingProjection(
            tenantId=tenant_id,
            plan=plan,
            status="trialing" if trial_days else "active",
            periodEnd=self.clock + timedelta(days=trial_days or 30),
        )
        self.subscriptions[tenant_id] = projection
        self.plans[tenant_id] = plan
        return projection

    def transition(
        self, tenant_id: str, action: str, target_plan: str | None = None
    ) -> BillingProjection:
        current = self.subscriptions.get(
            tenant_id, BillingProjection(tenantId=tenant_id, plan=None, status="inactive")
        )
        if action in {"upgrade", "downgrade", "reactivate", "recover"}:
            plan = target_plan or current.plan
            status = "active"
        elif action == "past_due":
            plan, status = current.plan, "past_due"
        elif action == "cancel":
            plan, status = current.plan, "canceled"
        else:
            raise ValueError("unsupported billing transition")
        projection = BillingProjection(
            tenantId=tenant_id,
            plan=plan,
            status=status,
            periodEnd=current.period_end,
            cancelAtPeriodEnd=action == "cancel",
        )
        self.subscriptions[tenant_id] = projection
        if plan:
            self.plans[tenant_id] = plan
        return projection

    def projection(self, tenant_id: str) -> BillingProjection:
        return self.subscriptions.get(
            tenant_id, BillingProjection(tenantId=tenant_id, plan=None, status="inactive")
        )

    def deliver(self, event: EventEnvelope, auth: AuthContext) -> EventReceipt:
        if auth.mode != "signed_event" or auth.credential_handle != "reference:event":
            return EventReceipt(
                eventId=event.event_id,
                outcome="rejected",
                stateChanged=False,
                errorCode="invalid_signature",
            )
        if event.event_type == "irrelevant":
            return EventReceipt(
                eventId=event.event_id,
                outcome="ignored",
                stateChanged=False,
            )
        if event.event_id in self.events:
            prior = self.events[event.event_id]
            return EventReceipt(
                eventId=event.event_id,
                outcome="duplicate",
                objectVersion=prior.object_version,
                stateChanged=False,
            )
        current_version = self.versions.get(event.object_id, -1)
        if event.object_version <= current_version:
            receipt = EventReceipt(
                eventId=event.event_id,
                outcome="stale",
                objectVersion=current_version,
                stateChanged=False,
            )
            self.events[event.event_id] = receipt
            return receipt
        self.versions[event.object_id] = event.object_version
        tenant_id = str(event.state.get("tenantId", "unknown"))
        counter = str(event.state.get("counter", event.event_type))
        self.side_effects[(tenant_id, counter)] = self.side_effects.get((tenant_id, counter), 0) + 1
        receipt = EventReceipt(
            eventId=event.event_id,
            outcome="applied",
            objectVersion=event.object_version,
            stateChanged=True,
        )
        self.events[event.event_id] = receipt
        return receipt

    def side_effect_count(self, tenant_id: str, counter: str) -> int:
        return self.side_effects.get((tenant_id, counter), 0)

    def record_usage(
        self, tenant_id: str, meter: str, quantity: Decimal, idempotency_key: str
    ) -> None:
        if quantity < 0:
            raise ValueError("usage quantity must be non-negative")
        key = (tenant_id, meter, idempotency_key)
        if key in self.usage_keys:
            return
        self.usage_keys.add(key)
        aggregate = (tenant_id, meter)
        self.usage[aggregate] = self.usage.get(aggregate, Decimal(0)) + quantity

    def usage_projection(self, tenant_id: str, meter: str) -> UsageProjection:
        return UsageProjection(
            tenantId=tenant_id,
            meter=meter,
            quantity=self.usage.get((tenant_id, meter), Decimal(0)),
            periodStart=self.clock,
            periodEnd=self.clock + timedelta(days=30),
        )

    def evaluate(self, test_id: str, config: "CoreConfig") -> tuple[bool, str]:
        if test_id in self.errors:
            raise RuntimeError(f"seeded runtime error {test_id}")
        from preflight.scenario_oracles import evaluate_reference_scenario

        return evaluate_reference_scenario(self, config, test_id, test_id in self.defects)

    def cleanup(self) -> None:
        if self.cleanup_error:
            raise RuntimeError("seeded cleanup error")
        self.events.clear()
        self.versions.clear()
        self.side_effects.clear()
        self.usage.clear()
        self.usage_keys.clear()
