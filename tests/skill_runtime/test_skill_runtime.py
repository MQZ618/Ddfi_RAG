import json
import sys
import zipfile
from pathlib import Path

import pytest

import skill_runtime.core as runtime
import scripts.build_skill_registry as registry_script
from skill_runtime.core import (
    ArtifactStore,
    DispatchError,
    FileArtifactStore,
    FileReceiptStore,
    InvocationReceipt,
    ProceduralSkillAdapter,
    SkillDispatcher,
    SkillRegistry,
    build_registry,
    canonical_json,
    validate_manifest_catalog,
)
from skill_runtime import ExecutionBudget, ExecutionGuard, TaskKind


def manifest(skill_id="demo", **overrides):
    value = {
        "schema_version": "1.0",
        "skill_id": skill_id,
        "version": "1.0.0",
        "enabled": True,
        "provider_type": "procedural_skill",
        "description": "demo",
        "definition": {"path": f"skills/{skill_id}.zip", "content_entry": f"{skill_id}/SKILL.md"},
        "capabilities": ["demo.run"],
        "modes": ["analyze"],
        "inputs": {"type": "object", "required": ["task"], "properties": {"task": {"type": "string"}}},
        "outputs": {"type": "object"},
        "mutation": {"writes_artifacts": False, "network": False},
    }
    value.update(overrides)
    return value


def write_skill_zip(root: Path, skill_id: str, content: str = "---\nname: demo\n---\n# Skill") -> Path:
    path = root / "skills" / f"{skill_id}.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"{skill_id}/SKILL.md", content)
    return path


def write_manifest_file(root: Path, skill_id: str = "demo", **overrides) -> Path:
    path = root / "skills" / skill_id / "manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    value = manifest(skill_id, **overrides)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_individual_manifests_are_discovered_and_validated(tmp_path):
    write_skill_zip(tmp_path, "demo")
    path = write_manifest_file(tmp_path)

    assert callable(getattr(runtime, "discover_manifests", None))
    assert callable(getattr(runtime, "validate_manifest", None))
    assert runtime.discover_manifests(tmp_path / "skills") == [path]
    normalized = runtime.validate_manifest(json.loads(path.read_text()), tmp_path, path)
    assert normalized["skill_id"] == "demo"


def test_manifest_validation_rejects_invalid_mode_and_unsafe_definition(tmp_path):
    write_skill_zip(tmp_path, "demo")
    validator = getattr(runtime, "validate_manifest", None)
    assert callable(validator)

    with pytest.raises(ValueError, match="invalid mode"):
        validator({**manifest(), "modes": ["unknown"]}, tmp_path)
    with pytest.raises(ValueError, match="unsafe definition"):
        validator({**manifest(), "definition": {"path": "skills/../outside.zip"}}, tmp_path)


def test_manifest_can_reference_a_local_skill_definition(tmp_path):
    skill_root = tmp_path / "skills" / "demo"
    skill_root.mkdir(parents=True)
    (skill_root / "SKILL.md").write_text("# Demo", encoding="utf-8")
    path = skill_root / "manifest.json"
    value = manifest(definition="SKILL.md")
    path.write_text(json.dumps(value), encoding="utf-8")

    loaded = runtime.load_manifest_source(tmp_path / "skills")
    assert loaded == [(value, path)]
    normalized = runtime.validate_manifest(value, tmp_path, path)
    assert normalized["definition"] == {"path": "skills/demo/SKILL.md"}


def test_manifest_validation_rejects_required_invalid_shapes():
    cases = [
        ({"version": "1.0.0"}, "missing skill_id"),
        ([manifest(), manifest()], "duplicate skill_id"),
        (manifest(provider_type="unknown"), "invalid provider_type"),
        (manifest(definition={}), "missing definition"),
        (manifest(version="v1"), "version anomaly"),
        (manifest(capabilities=[]), "empty capability"),
        (manifest(definition={"path": "other.zip"}), "directory mismatch"),
        (manifest(enabled=True, definition={"path": "skills/missing.zip"}), "enabled missing definition"),
    ]
    for value, _ in cases:
        with pytest.raises(ValueError):
            validate_manifest_catalog(value if isinstance(value, list) else [value], Path("/tmp/does-not-matter"))


def test_registry_hash_is_deterministic_and_detects_drift(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    first = tmp_path / "registry-1.json"
    second = tmp_path / "registry-2.json"
    build_registry(source, tmp_path, first, generated_at="2026-01-01T00:00:00Z")
    build_registry(source, tmp_path, second, generated_at="2026-01-02T00:00:00Z")
    a = json.loads(first.read_text())
    b = json.loads(second.read_text())
    assert a["registry_hash"] == b["registry_hash"]
    assert SkillRegistry.from_file(first).check_drift(source) is False
    write_skill_zip(tmp_path, "demo", "changed")
    assert SkillRegistry.from_file(first).check_drift(source) is True


def test_discovered_registry_hash_ignores_generated_at_and_output_location(tmp_path):
    write_skill_zip(tmp_path, "demo")
    manifest_file = write_manifest_file(tmp_path)
    first = tmp_path / "out-1" / "registry.json"
    second = tmp_path / "out-2" / "registry.json"

    build_registry(tmp_path / "skills", tmp_path, first, generated_at="2026-01-01T00:00:00Z")
    build_registry(tmp_path / "skills", tmp_path, second, generated_at="2026-01-02T00:00:00Z")

    first_document = json.loads(first.read_text())
    second_document = json.loads(second.read_text())
    assert first_document["registry_hash"] == second_document["registry_hash"]
    assert SkillRegistry.from_file(first).check_drift(tmp_path / "skills") is False

    manifest_file.write_text(manifest_file.read_text().replace('"1.0.0"', '"1.0.1"'), encoding="utf-8")
    assert SkillRegistry.from_file(first).check_drift(tmp_path / "skills") is True

    build_registry(tmp_path / "skills", tmp_path, second)
    assert SkillRegistry.from_file(second).check_drift(tmp_path / "skills") is False


def test_cli_defaults_to_discovered_skill_manifests(tmp_path, monkeypatch):
    write_skill_zip(tmp_path, "demo")
    write_manifest_file(tmp_path)
    output = tmp_path / "registry.json"
    monkeypatch.setattr(registry_script, "ROOT", tmp_path)
    monkeypatch.setattr(sys, "argv", ["build_skill_registry.py", "--output", str(output)])

    assert registry_script.main() == 0
    document = json.loads(output.read_text())
    assert [item["skill_id"] for item in document["skills"]] == ["demo"]


def test_dispatch_routes_by_capability_and_writes_runtime_receipt(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    receipt_store = FileReceiptStore(tmp_path / "receipts")
    artifact_store = FileArtifactStore(tmp_path / "artifacts")
    dispatcher = SkillDispatcher(SkillRegistry.from_file(registry_path), receipt_store, artifact_store)

    receipt = dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "read this"})

    assert receipt.status == "success"
    assert receipt.skill_id == "demo"
    assert receipt.execution_confirmed is True
    assert receipt.output_verified is False
    saved = receipt_store.get_receipt(receipt.receipt_id)
    assert saved.status == "success"
    assert artifact_store.exists(receipt.output_artifact_ids[0])


def test_dispatch_rejects_unregistered_disabled_and_bad_input(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    disabled = manifest(enabled=False)
    source.write_text(json.dumps({"schema_version": 1, "skills": [disabled]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    dispatcher = SkillDispatcher(SkillRegistry.from_file(registry_path), FileReceiptStore(tmp_path / "r"), FileArtifactStore(tmp_path / "a"))

    with pytest.raises(DispatchError, match="no enabled skill"):
        dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})
    with pytest.raises(DispatchError, match="unknown capability"):
        dispatcher.dispatch("task-1", "missing.run", "analyze", {"task": "x"})


def test_failed_adapter_cannot_be_marked_success(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)

    class BrokenAdapter(ProceduralSkillAdapter):
        def execute(self, skill, request):
            raise RuntimeError("adapter failed")

    receipts = FileReceiptStore(tmp_path / "receipts")
    dispatcher = SkillDispatcher(SkillRegistry.from_file(registry_path), receipts, FileArtifactStore(tmp_path / "artifacts"), BrokenAdapter())
    with pytest.raises(DispatchError, match="adapter failed"):
        dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})
    stored = receipts.list_receipts_for_task("task-1")[-1]
    assert stored.status == "failed"
    assert stored.execution_confirmed is False


def test_dispatcher_blocks_skill_load_when_execution_budget_forbids_it(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    receipts = FileReceiptStore(tmp_path / "receipts")
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path),
        receipts,
        FileArtifactStore(tmp_path / "artifacts"),
        execution_guard=ExecutionGuard(ExecutionBudget.for_task(TaskKind.SIMPLE_TEXT)),
    )

    with pytest.raises(DispatchError, match="execution budget"):
        dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})

    stored = receipts.list_receipts_for_task("task-1")[-1]
    assert stored.status == "blocked"
    assert stored.execution_confirmed is False


def test_dispatch_receipt_records_sufficient_stop_decision(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    guard = ExecutionGuard(ExecutionBudget.for_task(TaskKind.ATTACHMENT_READ))
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path),
        FileReceiptStore(tmp_path / "receipts"),
        FileArtifactStore(tmp_path / "artifacts"),
        execution_guard=guard,
    )

    receipt = dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})

    assert receipt.evidence["execution_guard"]["stop_decision"] == {
        "stop": True,
        "reason": "sufficient",
    }


def test_dispatch_requires_explicit_mutation_authorization(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(
        json.dumps(
            {"schema_version": 1, "skills": [manifest(mutation={"writes_artifacts": True, "network": False})]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    receipts = FileReceiptStore(tmp_path / "receipts")
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path), receipts, FileArtifactStore(tmp_path / "artifacts")
    )

    with pytest.raises(DispatchError, match="mutation authorization"):
        dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})

    stored = receipts.list_receipts_for_task("task-1")[-1]
    assert stored.status == "blocked"
    assert stored.error["code"] == "mutation_authorization_required"


def test_review_mode_rejects_mutating_skill_even_when_authorized(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "skills": [
                    manifest(
                        modes=["review"],
                        mutation={"writes_artifacts": True, "network": False},
                    )
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    receipts = FileReceiptStore(tmp_path / "receipts")
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path), receipts, FileArtifactStore(tmp_path / "artifacts")
    )

    with pytest.raises(DispatchError, match="review-only"):
        dispatcher.dispatch(
            "task-1", "demo.run", "review", {"task": "x"}, mutation_authorized=True
        )

    stored = receipts.list_receipts_for_task("task-1")[-1]
    assert stored.status == "blocked"
    assert stored.error["code"] == "review_only_mutation"


def test_authorized_mutating_skill_records_explicit_authorization(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(
        json.dumps(
            {"schema_version": 1, "skills": [manifest(mutation={"writes_artifacts": True})]},
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path),
        FileReceiptStore(tmp_path / "receipts"),
        FileArtifactStore(tmp_path / "artifacts"),
    )

    receipt = dispatcher.dispatch(
        "task-1", "demo.run", "analyze", {"task": "x"}, mutation_authorized=True
    )

    assert receipt.status == "success"
    assert receipt.evidence["mutation_authorized"] is True


@pytest.mark.parametrize("value", ["true", 1, None])
def test_manifest_rejects_non_boolean_mutation_flags(tmp_path, value):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifest.json"
    source.write_text(
        json.dumps(manifest(mutation={"writes_artifacts": value}), ensure_ascii=False),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="mutation flags must be boolean"):
        runtime.validate_manifest(json.loads(source.read_text(encoding="utf-8")), tmp_path)


def test_artifact_lineage_and_structured_receipt(tmp_path):
    store = FileArtifactStore(tmp_path / "artifacts")
    parent = store.put("source", metadata={"role": "input"})
    child = store.put(json.dumps({"value": 1}), metadata={"role": "output", "parents": [parent.artifact_id]})
    assert store.hash(parent.artifact_id) == parent.sha256
    assert json.loads(store.get(child.artifact_id).decode()) == {"value": 1}
    assert child.metadata["parents"] == [parent.artifact_id]


def test_artifact_persistence_failure_marks_receipt_failed(tmp_path):
    write_skill_zip(tmp_path, "demo")
    source = tmp_path / "manifests.json"
    source.write_text(json.dumps({"schema_version": 1, "skills": [manifest()]}, ensure_ascii=False), encoding="utf-8")
    registry_path = tmp_path / "registry.json"
    build_registry(source, tmp_path, registry_path)

    class BrokenArtifactStore(FileArtifactStore):
        def put(self, content, metadata=None):
            raise OSError("artifact store unavailable")

    receipts = FileReceiptStore(tmp_path / "receipts")
    dispatcher = SkillDispatcher(
        SkillRegistry.from_file(registry_path), receipts, BrokenArtifactStore(tmp_path / "artifacts")
    )

    with pytest.raises(DispatchError, match="artifact store unavailable"):
        dispatcher.dispatch("task-1", "demo.run", "analyze", {"task": "x"})

    stored = receipts.list_receipts_for_task("task-1")[-1]
    assert stored.status == "failed"
    assert stored.error["code"] == "artifact_persistence_failed"


def test_real_router_skill_is_loaded_by_dispatcher(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    source = repo / "skills"
    registry_path = tmp_path / "registry.json"
    build_registry(source, repo, registry_path)
    dispatcher = SkillDispatcher(SkillRegistry.from_file(registry_path), FileReceiptStore(tmp_path / "r"), FileArtifactStore(tmp_path / "a"))

    receipt = dispatcher.dispatch("real-task", "route.writing_task", "analyze", {"task": "审查论文结构"})
    output = json.loads(dispatcher.artifact_store.get(receipt.output_artifact_ids[0]).decode())
    assert receipt.status == "success"
    assert output["definition_loaded"] is True
    assert output["skill_id"] == "writing-agent-router"


def test_real_sample_manifests_build_only_registered_skills(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    source = repo / "skills"
    manifest_paths = runtime.discover_manifests(source)
    assert [path.parent.name for path in manifest_paths] == [
        "academic-writing-review",
        "evidence-audit",
        "writing-agent-router",
    ]

    registry_path = tmp_path / "registry.json"
    build_registry(source, repo, registry_path)
    document = json.loads(registry_path.read_text())
    assert [item["skill_id"] for item in document["skills"]] == [
        "academic-writing-review",
        "evidence-audit",
        "writing-agent-router",
    ]
    assert all(
        (repo / item["definition"]["path"]).is_file()
        for item in document["skills"]
    )


def test_canonical_json_is_stable():
    assert canonical_json({"b": 1, "a": [2, 1]}) == '{"a":[2,1],"b":1}'
