from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol


SUPPORTED_PROVIDERS = {"procedural_skill", "invokable_skill", "tool"}
SUPPORTED_MODES = {"analyze", "plan", "draft", "transform", "review", "verify", "export"}
RECEIPT_STATUSES = {"accepted", "running", "success", "failed", "blocked", "cancelled"}
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
SKILL_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
MANIFEST_SCHEMA_VERSION = "1.0"
REGISTRY_VERSION = "1"


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _as_bytes(value: bytes | str | Mapping[str, Any]) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    return canonical_json(value).encode("utf-8")


def _catalog_entries(catalog: Mapping[str, Any] | list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(catalog, Mapping):
        entries = catalog.get("skills")
    else:
        entries = catalog
    if not isinstance(entries, list):
        raise ValueError("manifest catalog must contain a skills list")
    return [dict(entry) for entry in entries]


def _safe_relative_path(value: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"unsafe definition path: {value}")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or path == Path("."):
        raise ValueError(f"unsafe definition path: {value}")
    return path


def discover_manifests(manifest_root: Path) -> list[Path]:
    """Return all per-Skill manifest files in deterministic path order."""
    root = Path(manifest_root)
    if not root.is_dir():
        raise ValueError(f"manifest root is not a directory: {root}")
    return sorted((path for path in root.rglob("manifest.json") if path.is_file()), key=lambda path: path.as_posix())


def _normalize_schema_version(value: Any) -> str:
    if value in (1, 1.0, "1", MANIFEST_SCHEMA_VERSION):
        return MANIFEST_SCHEMA_VERSION
    raise ValueError(f"unsupported manifest schema_version: {value}")


def _normalize_string_list(value: Any, field_name: str, skill_id: str, allowed: set[str] | None = None) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"empty {field_name} for {skill_id}")
    values = sorted({item.strip() for item in value})
    if allowed is not None and not set(values).issubset(allowed):
        raise ValueError(f"invalid {field_name} for {skill_id}")
    return values


def _skills_root(project_root: Path) -> Path:
    return (Path(project_root).resolve() / "skills").resolve()


def _under(path: Path, root: Path) -> bool:
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False


def _definition_location(
    definition: str | Mapping[str, Any], project_root: Path, manifest_path: Path | None = None
) -> tuple[Path, dict[str, Any]]:
    project_root = Path(project_root).resolve()
    if isinstance(definition, str):
        relative = _safe_relative_path(definition)
        base = Path(manifest_path).resolve().parent if manifest_path is not None else project_root
        path = (base / relative).resolve()
        normalized = {"path": path.relative_to(project_root).as_posix()}
    elif isinstance(definition, Mapping):
        raw_path = definition.get("path")
        if not isinstance(raw_path, str):
            raise ValueError("missing definition path")
        relative = _safe_relative_path(raw_path)
        path = (project_root / relative).resolve()
        normalized = json.loads(canonical_json(definition))
        normalized["path"] = relative.as_posix()
    else:
        raise ValueError("missing definition")

    skills_root = _skills_root(project_root)
    if not _under(path, skills_root):
        raise ValueError(f"unsafe definition path: {definition}")
    return path, normalized


def _validate_definition(
    definition: Any, skill_id: str, project_root: Path, manifest_path: Path | None
) -> dict[str, Any]:
    try:
        definition_path, normalized = _definition_location(definition, project_root, manifest_path)
    except (TypeError, ValueError) as exc:
        if "missing definition" in str(exc):
            raise ValueError(f"missing definition for {skill_id}") from exc
        raise

    relative = Path(normalized["path"])
    if not relative.parts or relative.parts[0] != "skills":
        raise ValueError(f"definition directory mismatch for {skill_id}")
    skill_location = relative.parts[1:]
    if not skill_location or not (
        relative.stem == skill_id or skill_location[0] == skill_id
    ):
        raise ValueError(f"definition directory mismatch for {skill_id}")
    if not definition_path.is_file():
        raise ValueError(f"missing definition for {skill_id}")

    content_entry = normalized.get("content_entry")
    if content_entry is not None:
        try:
            content_relative = _safe_relative_path(content_entry)
        except ValueError as exc:
            raise ValueError(f"invalid definition content_entry for {skill_id}") from exc
        if content_relative != Path(content_entry):
            raise ValueError(f"invalid definition content_entry for {skill_id}")

    if zipfile.is_zipfile(definition_path):
        if not isinstance(content_entry, str) or not content_entry:
            raise ValueError(f"missing definition content_entry for {skill_id}")
        with zipfile.ZipFile(definition_path) as archive:
            if content_entry not in archive.namelist():
                raise ValueError(f"definition content missing for {skill_id}: {content_entry}")
    elif content_entry is not None:
        raise ValueError(f"definition content_entry requires ZIP archive for {skill_id}")
    return normalized


def validate_manifest(
    manifest: Mapping[str, Any], project_root: Path, manifest_path: Path | None = None
) -> dict[str, Any]:
    """Validate and normalize one MVP Skill manifest."""
    if not isinstance(manifest, Mapping):
        raise ValueError("manifest must be an object")
    skill_id = manifest.get("skill_id")
    if not isinstance(skill_id, str) or not SKILL_ID.fullmatch(skill_id):
        raise ValueError("missing or invalid skill_id")
    if not isinstance(manifest.get("version"), str) or not SEMVER.fullmatch(manifest["version"]):
        raise ValueError(f"version anomaly for {skill_id}")
    if not isinstance(manifest.get("enabled"), bool):
        raise ValueError(f"enabled must be boolean for {skill_id}")
    if manifest.get("provider_type") not in SUPPORTED_PROVIDERS:
        raise ValueError(f"invalid provider_type for {skill_id}")
    description = manifest.get("description")
    if not isinstance(description, str) or not description.strip():
        raise ValueError(f"missing description for {skill_id}")
    if "schema_version" not in manifest:
        raise ValueError(f"missing schema_version for {skill_id}")
    definition = manifest.get("definition")
    if definition is None:
        raise ValueError(f"missing definition for {skill_id}")
    normalized_definition = _validate_definition(definition, skill_id, project_root, manifest_path)
    capabilities = _normalize_string_list(manifest.get("capabilities"), "capability", skill_id)
    modes = _normalize_string_list(manifest.get("modes"), "mode", skill_id, SUPPORTED_MODES)
    normalized: dict[str, Any] = {
        "schema_version": _normalize_schema_version(manifest["schema_version"]),
        "skill_id": skill_id,
        "version": manifest["version"].strip(),
        "enabled": manifest["enabled"],
        "provider_type": manifest["provider_type"],
        "description": description.strip(),
        "definition": normalized_definition,
        "capabilities": capabilities,
        "modes": modes,
    }
    for field_name in ("inputs", "outputs", "mutation"):
        value = manifest.get(field_name)
        if not isinstance(value, Mapping):
            raise ValueError(f"missing {field_name} for {skill_id}")
        normalized[field_name] = json.loads(canonical_json(value))
    return normalized


def validate_manifest_catalog(
    catalog: Mapping[str, Any] | list[Mapping[str, Any]], project_root: Path
) -> list[dict[str, Any]]:
    """Validate and normalize a catalog or a list of individual manifests."""
    entries = _catalog_entries(catalog)
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for entry in entries:
        item = validate_manifest(entry, project_root)
        if item["skill_id"] in seen:
            raise ValueError(f"duplicate skill_id: {item['skill_id']}")
        seen.add(item["skill_id"])
        normalized.append(item)
    return normalized


def load_manifest_source(source: Path) -> list[tuple[dict[str, Any], Path | None]]:
    """Load a manifest directory, an individual manifest, or a legacy catalog."""
    source = Path(source)
    if source.is_dir():
        paths = discover_manifests(source)
        if not paths:
            raise ValueError(f"no manifest.json files found under: {source}")
        return [(json.loads(path.read_text(encoding="utf-8")), path) for path in paths]
    if not source.is_file():
        raise ValueError(f"manifest source does not exist: {source}")
    document = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(document, Mapping) and isinstance(document.get("skills"), list):
        return [(dict(entry), source) for entry in document["skills"]]
    if not isinstance(document, Mapping):
        raise ValueError(f"manifest source must contain an object: {source}")
    return [(dict(document), source)]


def _registry_payload(
    schema_version: str,
    registry_version: str,
    skills: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "registry_version": registry_version,
        "skills": sorted(skills, key=lambda item: item["skill_id"]),
    }


def _normalized_source_entries(manifest_path: Path, project_root: Path) -> list[tuple[dict[str, Any], Path | None]]:
    loaded = load_manifest_source(manifest_path)
    seen: set[str] = set()
    entries: list[tuple[dict[str, Any], Path | None]] = []
    for raw, source_path in loaded:
        item = validate_manifest(raw, project_root, source_path)
        if item["skill_id"] in seen:
            raise ValueError(f"duplicate skill_id: {item['skill_id']}")
        seen.add(item["skill_id"])
        entries.append((item, source_path))
    return entries


def _build_payload(manifest_path: Path, project_root: Path, registry_parent: Path) -> dict[str, Any]:
    entries = _normalized_source_entries(manifest_path, project_root)
    schema_version = entries[0][0]["schema_version"]
    root = os.path.relpath(project_root.resolve(), registry_parent.resolve())
    skills: list[dict[str, Any]] = []
    for entry, source_path in entries:
        item = json.loads(canonical_json(entry))
        path, _ = _definition_location(item["definition"], project_root, source_path)
        item["definition"]["sha256"] = _sha256(path.read_bytes())
        item["definition"]["size"] = path.stat().st_size
        skills.append(item)
    payload = _registry_payload(schema_version, REGISTRY_VERSION, skills)
    payload["registry_hash"] = _sha256(canonical_json(payload).encode("utf-8"))
    payload["definition_root"] = root
    return payload


def build_registry(
    manifest_path: Path,
    project_root: Path,
    output_path: Path,
    generated_at: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _build_payload(Path(manifest_path), Path(project_root), output_path.parent)
    document = dict(payload)
    document["generated_at"] = generated_at or _now()
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


class SkillRegistry:
    def __init__(self, document: Mapping[str, Any], path: Path):
        self.document = dict(document)
        self.path = Path(path)
        self.skills = {item["skill_id"]: dict(item) for item in document["skills"]}
        self.registry_hash = document["registry_hash"]
        self.definition_root = (self.path.parent / document["definition_root"]).resolve()

    @classmethod
    def from_file(cls, path: Path) -> "SkillRegistry":
        path = Path(path)
        document = json.loads(path.read_text(encoding="utf-8"))
        expected = document.get("registry_hash")
        payload = _registry_payload(
            document.get("schema_version"),
            document.get("registry_version"),
            document.get("skills", []),
        )
        if not expected or expected != _sha256(canonical_json(payload).encode("utf-8")):
            raise ValueError("registry hash mismatch")
        validate_manifest_catalog(document.get("skills", []), (path.parent / document["definition_root"]).resolve())
        return cls(document, path)

    def select_all(self, capability: str, mode: str) -> list[dict[str, Any]]:
        if not isinstance(capability, str) or not capability.strip():
            raise DispatchError("invalid_capability", "capability is required")
        if mode not in SUPPORTED_MODES:
            raise DispatchError("invalid_mode", f"unsupported mode: {mode}")
        matches = [
            item
            for item in self.skills.values()
            if item.get("enabled") and capability in item.get("capabilities", []) and mode in item.get("modes", [])
        ]
        if not matches:
            raise DispatchError("unknown_capability", f"unknown capability or no enabled skill for capability={capability}, mode={mode}")
        return sorted(matches, key=lambda item: item["skill_id"])

    def select(self, capability: str, mode: str) -> dict[str, Any]:
        """Return the first stable match for backward-compatible callers."""
        return self.select_all(capability, mode)[0]

    def definition_path(self, skill: Mapping[str, Any]) -> Path:
        path = _safe_relative_path(skill["definition"]["path"])
        resolved = (self.definition_root / path).resolve()
        skills_root = (self.definition_root / "skills").resolve()
        if os.path.commonpath((str(resolved), str(skills_root))) != str(skills_root):
            raise DispatchError("unsafe_definition", "definition path escapes the skills directory")
        return resolved

    def check_drift(self, manifest_path: Path) -> bool:
        current = _build_payload(Path(manifest_path), self.definition_root, self.path.parent)
        return current["registry_hash"] != self.registry_hash


@dataclass
class InvocationReceipt:
    receipt_id: str
    task_id: str
    capability: str
    mode: str
    requested_at: str
    status: str = "accepted"
    started_at: str | None = None
    finished_at: str | None = None
    skill_id: str | None = None
    skill_version: str | None = None
    provider_type: str | None = None
    registry_hash: str | None = None
    input_artifact_ids: list[str] = field(default_factory=list)
    output_artifact_ids: list[str] = field(default_factory=list)
    artifact_lineage: list[dict[str, Any]] = field(default_factory=list)
    execution_confirmed: bool = False
    output_verified: bool = False
    evidence: dict[str, Any] = field(default_factory=dict)
    error: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.status not in RECEIPT_STATUSES:
            raise ValueError(f"invalid receipt status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "InvocationReceipt":
        return cls(**dict(value))


class ReceiptStore(Protocol):
    def save_receipt(self, receipt: InvocationReceipt) -> None: ...

    def get_receipt(self, receipt_id: str) -> InvocationReceipt: ...

    def list_receipts_for_task(self, task_id: str) -> list[InvocationReceipt]: ...


class FileReceiptStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save_receipt(self, receipt: InvocationReceipt) -> None:
        path = self.root / f"{receipt.receipt_id}.json"
        path.write_text(json.dumps(receipt.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def get_receipt(self, receipt_id: str) -> InvocationReceipt:
        path = self.root / f"{receipt_id}.json"
        if not path.is_file():
            raise KeyError(receipt_id)
        return InvocationReceipt.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_receipts_for_task(self, task_id: str) -> list[InvocationReceipt]:
        receipts = []
        for path in self.root.glob("*.json"):
            receipt = InvocationReceipt.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if receipt.task_id == task_id:
                receipts.append(receipt)
        return sorted(receipts, key=lambda item: item.requested_at)


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    sha256: str
    size: int
    metadata: dict[str, Any]


class ArtifactStore(Protocol):
    def put(self, content: bytes | str | Mapping[str, Any], metadata: Mapping[str, Any] | None = None) -> ArtifactRecord: ...

    def get(self, artifact_id: str) -> bytes: ...

    def exists(self, artifact_id: str) -> bool: ...

    def hash(self, artifact_id: str) -> str: ...


class FileArtifactStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _digest(self, artifact_id: str) -> str:
        if not artifact_id.startswith("sha256:"):
            raise ValueError("invalid artifact id")
        digest = artifact_id.removeprefix("sha256:")
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("invalid artifact id")
        return digest

    def _path(self, artifact_id: str) -> Path:
        return self.root / f"{self._digest(artifact_id)}.bin"

    def put(self, content: bytes | str | Mapping[str, Any], metadata: Mapping[str, Any] | None = None) -> ArtifactRecord:
        data = _as_bytes(content)
        digest = _sha256(data)
        artifact_id = f"sha256:{digest}"
        self._path(artifact_id).write_bytes(data)
        meta = dict(metadata or {})
        meta_path = self.root / f"{digest}.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return ArtifactRecord(artifact_id, digest, len(data), meta)

    def get(self, artifact_id: str) -> bytes:
        return self._path(artifact_id).read_bytes()

    def exists(self, artifact_id: str) -> bool:
        try:
            return self._path(artifact_id).is_file()
        except ValueError:
            return False

    def hash(self, artifact_id: str) -> str:
        data = self.get(artifact_id)
        digest = _sha256(data)
        if digest != self._digest(artifact_id):
            raise ValueError("artifact hash mismatch")
        return digest


class DispatchError(RuntimeError):
    def __init__(self, code: str, message: str, status: str = "blocked"):
        super().__init__(message)
        self.code = code
        self.status = status


class ProceduralSkillAdapter:
    """Load a real ZIP Skill and emit evidence; semantic LLM execution is host-specific."""

    def __init__(self, registry: SkillRegistry | None = None):
        self.registry = registry

    def execute(self, skill: Mapping[str, Any], request: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        if self.registry is None:
            raise RuntimeError("procedural adapter has no registry")
        definition_path = self.registry.definition_path(skill)
        expected_archive_hash = skill["definition"].get("sha256")
        actual_archive_hash = _sha256(definition_path.read_bytes())
        if expected_archive_hash != actual_archive_hash:
            raise RuntimeError("definition drift detected")
        entry = skill["definition"]["content_entry"]
        with zipfile.ZipFile(definition_path) as archive:
            content = archive.read(entry)
        task = request["inputs"]["task"]
        output = {
            "definition_loaded": True,
            "definition_entry": entry,
            "definition_sha256": actual_archive_hash,
            "mode": request["mode"],
            "skill_id": skill["skill_id"],
            "task_received_as_data": task,
        }
        evidence = {
            "adapter": "procedural_zip",
            "definition_content_sha256": _sha256(content),
            "source": "dispatcher_runtime",
        }
        return output, evidence


def _validate_inputs(skill: Mapping[str, Any], inputs: Mapping[str, Any]) -> None:
    if not isinstance(inputs, Mapping):
        raise DispatchError("invalid_input", "inputs must be an object")
    schema = skill["inputs"]
    for name in schema.get("required", []):
        if name not in inputs:
            raise DispatchError("invalid_input", f"missing input: {name}")
    for name, rule in schema.get("properties", {}).items():
        if name not in inputs or not isinstance(rule, Mapping):
            continue
        expected = rule.get("type")
        actual = inputs[name]
        if expected == "string" and not isinstance(actual, str):
            raise DispatchError("invalid_input", f"input {name} must be a string")
        if expected == "object" and not isinstance(actual, Mapping):
            raise DispatchError("invalid_input", f"input {name} must be an object")


class SkillDispatcher:
    def __init__(
        self,
        registry: SkillRegistry,
        receipt_store: ReceiptStore,
        artifact_store: ArtifactStore,
        adapter: ProceduralSkillAdapter | None = None,
    ):
        self.registry = registry
        self.receipt_store = receipt_store
        self.artifact_store = artifact_store
        self.adapter = adapter or ProceduralSkillAdapter(registry)

    def dispatch(
        self,
        task_id: str,
        capability: str,
        mode: str,
        inputs: Mapping[str, Any],
        input_artifact_ids: list[str] | None = None,
    ) -> InvocationReceipt:
        receipt = InvocationReceipt(
            receipt_id=str(uuid.uuid4()),
            task_id=task_id,
            capability=capability,
            mode=mode,
            requested_at=_now(),
            registry_hash=self.registry.registry_hash,
            input_artifact_ids=list(input_artifact_ids or []),
        )
        self.receipt_store.save_receipt(receipt)
        try:
            skill = self.registry.select(capability, mode)
            _validate_inputs(skill, inputs)
            for artifact_id in receipt.input_artifact_ids:
                if not self.artifact_store.exists(artifact_id):
                    raise DispatchError("missing_input_artifact", f"input artifact not found: {artifact_id}")
            receipt.skill_id = skill["skill_id"]
            receipt.skill_version = skill["version"]
            receipt.provider_type = skill["provider_type"]
            receipt.status = "running"
            receipt.started_at = _now()
            self.receipt_store.save_receipt(receipt)
            try:
                output, evidence = self.adapter.execute(
                    skill,
                    {"task_id": task_id, "capability": capability, "mode": mode, "inputs": dict(inputs)},
                )
            except Exception as exc:
                receipt.status = "failed"
                receipt.finished_at = _now()
                receipt.error = {"code": "adapter_failed", "message": str(exc)}
                self.receipt_store.save_receipt(receipt)
                raise DispatchError("adapter_failed", str(exc), status="failed") from exc
            artifact = self.artifact_store.put(
                output,
                metadata={
                    "task_id": task_id,
                    "capability": capability,
                    "skill_id": skill["skill_id"],
                    "parents": receipt.input_artifact_ids,
                },
            )
            receipt.output_artifact_ids = [artifact.artifact_id]
            receipt.artifact_lineage = [
                {"artifact_id": artifact.artifact_id, "role": "output", "sha256": artifact.sha256, "parents": receipt.input_artifact_ids}
            ]
            receipt.evidence = {
                "source": "dispatcher_runtime",
                "definition_archive_sha256": skill["definition"].get("sha256"),
                **evidence,
            }
            receipt.status = "success"
            receipt.execution_confirmed = True
            receipt.finished_at = _now()
            self.receipt_store.save_receipt(receipt)
            return receipt
        except DispatchError as exc:
            if receipt.status not in {"failed", "success"}:
                receipt.status = exc.status
                receipt.finished_at = _now()
                receipt.error = {"code": exc.code, "message": str(exc)}
                self.receipt_store.save_receipt(receipt)
            raise


if __name__ == "__main__":
    raise SystemExit("Use scripts/build_skill_registry.py to build the registry.")
