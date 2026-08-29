"""Explicit Capability and Phase routing over the verified Skill Registry."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from .core import DispatchError, SkillRegistry


WRITING_PHASES = (
    "intake",
    "evidence",
    "planning",
    "drafting",
    "review",
    "polishing",
    "formatting",
    "verification",
    "delivery",
)

PHASE_TO_MODE = {
    "intake": "analyze",
    "evidence": "analyze",
    "planning": "plan",
    "drafting": "draft",
    "review": "review",
    "polishing": "transform",
    "formatting": "export",
    "verification": "verify",
    "delivery": "export",
}


class RoutingError(ValueError):
    """Raised when an explicit route request is malformed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _normalize_capabilities(capabilities: Sequence[str]) -> tuple[str, ...]:
    if isinstance(capabilities, (str, bytes)) or not isinstance(capabilities, Sequence):
        raise RoutingError("invalid_capabilities", "capabilities must be a sequence of strings")
    if not capabilities:
        raise RoutingError("missing_capabilities", "at least one capability is required")

    normalized: list[str] = []
    seen: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, str) or not capability.strip():
            raise RoutingError("invalid_capability", "capability must be a non-empty string")
        value = capability.strip()
        if value in seen:
            raise RoutingError("duplicate_capability", f"duplicate capability: {value}")
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)


@dataclass(frozen=True)
class CapabilityRoute:
    capability: str
    mode: str
    skill_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "capability": self.capability,
            "mode": self.mode,
            "skill_ids": list(self.skill_ids),
        }


@dataclass(frozen=True)
class PhaseRoute:
    phase: str
    mode: str
    capabilities: tuple[str, ...]
    routes: tuple[CapabilityRoute, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "mode": self.mode,
            "capabilities": list(self.capabilities),
            "routes": [route.to_dict() for route in self.routes],
        }


class CapabilityRouter:
    """Resolve every enabled Registry Skill for explicit capability IDs."""

    def __init__(self, registry: SkillRegistry):
        self.registry = registry

    def route(self, capabilities: Sequence[str], mode: str) -> tuple[CapabilityRoute, ...]:
        normalized = _normalize_capabilities(capabilities)
        routes: list[CapabilityRoute] = []
        for capability in normalized:
            matches = self.registry.select_all(capability, mode)
            routes.append(
                CapabilityRoute(
                    capability=capability,
                    mode=mode,
                    skill_ids=tuple(item["skill_id"] for item in matches),
                )
            )
        return tuple(routes)


class PhaseRouter:
    """Map a declared writing Phase to one runtime mode before selection."""

    def __init__(self, registry: SkillRegistry):
        self.capability_router = CapabilityRouter(registry)

    def route(self, phase: str, capabilities: Sequence[str]) -> PhaseRoute:
        if not isinstance(phase, str) or not phase.strip() or phase.strip() not in PHASE_TO_MODE:
            raise RoutingError("unsupported_phase", f"unsupported phase: {phase}")
        normalized_phase = phase.strip()
        normalized_capabilities = _normalize_capabilities(capabilities)
        mode = PHASE_TO_MODE[normalized_phase]
        routes = self.capability_router.route(normalized_capabilities, mode)
        return PhaseRoute(
            phase=normalized_phase,
            mode=mode,
            capabilities=normalized_capabilities,
            routes=routes,
        )
