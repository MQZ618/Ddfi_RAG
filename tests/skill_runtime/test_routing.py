from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from skill_runtime.core import DispatchError, SkillRegistry
from skill_runtime.routing import (
    PHASE_TO_MODE,
    CapabilityRouter,
    PhaseRouter,
    RoutingError,
)


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "skill-registry" / "skill-registry.json"


def load_registry() -> SkillRegistry:
    return SkillRegistry.from_file(REGISTRY_PATH)


def test_capability_router_returns_all_matching_enabled_skills_in_stable_order(tmp_path: Path):
    base = load_registry().skills["academic-writing-review"]
    first = deepcopy(base)
    first["skill_id"] = "z-review-adapter"
    second = deepcopy(base)
    second["skill_id"] = "a-review-adapter"
    document = {
        "schema_version": "1.0",
        "registry_version": "1",
        "skills": [first, second],
        "registry_hash": "test-hash",
        "definition_root": ".",
    }
    registry = SkillRegistry(document, tmp_path / "registry.json")

    routes = CapabilityRouter(registry).route(["review.academic_prose"], "review")

    assert len(routes) == 1
    assert routes[0].to_dict() == {
        "capability": "review.academic_prose",
        "mode": "review",
        "skill_ids": ["a-review-adapter", "z-review-adapter"],
    }


def test_capability_router_preserves_capability_order_and_rejects_duplicates():
    router = CapabilityRouter(load_registry())

    routes = router.route(["review.evidence", "review.academic_prose"], "review")

    assert [route.capability for route in routes] == [
        "review.evidence",
        "review.academic_prose",
    ]
    with pytest.raises(RoutingError, match="duplicate capability"):
        router.route(["review.evidence", "review.evidence"], "review")


def test_capability_router_rejects_unknown_capability_and_invalid_mode():
    router = CapabilityRouter(load_registry())

    with pytest.raises(DispatchError, match="unknown capability"):
        router.route(["review.not_registered"], "review")
    with pytest.raises(DispatchError, match="unsupported mode"):
        router.route(["review.evidence"], "unsupported")


def test_phase_router_maps_declared_phase_to_its_runtime_mode():
    router = PhaseRouter(load_registry())

    route = router.route("review", ["review.academic_prose", "review.evidence"])

    assert route.phase == "review"
    assert route.mode == PHASE_TO_MODE["review"] == "review"
    assert route.capabilities == ("review.academic_prose", "review.evidence")
    assert route.to_dict()["routes"][1]["skill_ids"] == ["evidence-audit"]


def test_phase_router_rejects_unknown_phase_and_phase_mode_mismatch():
    router = PhaseRouter(load_registry())

    with pytest.raises(RoutingError, match="unsupported phase"):
        router.route("unknown", ["review.evidence"])
    with pytest.raises(DispatchError, match="unknown capability"):
        router.route("planning", ["review.evidence"])
