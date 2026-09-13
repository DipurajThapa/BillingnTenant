"""Deterministic local reference implementation and defect corpus."""

from dataclasses import dataclass, field
from decimal import Decimal


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
    events: set[str] = field(default_factory=set)
    versions: dict[str, int] = field(default_factory=dict)
    usage: dict[tuple[str, str], Decimal] = field(default_factory=dict)

    def evaluate(self, test_id: str) -> tuple[bool, str]:
        if test_id in self.errors:
            raise RuntimeError(f"seeded runtime error {test_id}")
        if test_id in self.defects:
            return False, f"seeded defect {test_id} observed"
        return True, "reference oracle satisfied"

    def cleanup(self) -> None:
        if self.cleanup_error:
            raise RuntimeError("seeded cleanup error")
        self.events.clear()
        self.versions.clear()
        self.usage.clear()
