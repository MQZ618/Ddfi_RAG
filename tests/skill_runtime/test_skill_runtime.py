import json
import zipfile
from pathlib import Path

import pytest

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


def manifest(skill_id="demo", **overrides):
    value = {
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


def test_artifact_lineage_and_structured_receipt(tmp_path):
    store = FileArtifactStore(tmp_path / "artifacts")
    parent = store.put("source", metadata={"role": "input"})
    child = store.put(json.dumps({"value": 1}), metadata={"role": "output", "parents": [parent.artifact_id]})
    assert store.hash(parent.artifact_id) == parent.sha256
    assert json.loads(store.get(child.artifact_id).decode()) == {"value": 1}
    assert child.metadata["parents"] == [parent.artifact_id]


def test_real_router_skill_is_loaded_by_dispatcher(tmp_path):
    repo = Path(__file__).resolve().parents[2]
    source = repo / "skills" / "registry-manifests.json"
    registry_path = tmp_path / "registry.json"
    build_registry(source, repo, registry_path)
    dispatcher = SkillDispatcher(SkillRegistry.from_file(registry_path), FileReceiptStore(tmp_path / "r"), FileArtifactStore(tmp_path / "a"))

    receipt = dispatcher.dispatch("real-task", "route.writing_task", "analyze", {"task": "审查论文结构"})
    output = json.loads(dispatcher.artifact_store.get(receipt.output_artifact_ids[0]).decode())
    assert receipt.status == "success"
    assert output["definition_loaded"] is True
    assert output["skill_id"] == "writing-agent-router"


def test_canonical_json_is_stable():
    assert canonical_json({"b": 1, "a": [2, 1]}) == '{"a":[2,1],"b":1}'
