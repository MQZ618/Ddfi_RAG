"""Metadata-only session file references for host runtimes."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_SCHEMA_VERSION = "1"


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def _validate_record_values(
    session_id: Any,
    file_id: Any,
    sha256: Any,
    size: Any,
    name: Any,
    mime_type: Any,
    runtime_reference: Any,
    created_at: Any,
    metadata: Any,
) -> tuple[str, str, str, int, str, str, str, str, dict[str, Any]]:
    session = _required_text(session_id, "session_id")
    file = _required_text(file_id, "file_id")
    digest = _required_text(sha256, "sha256")
    if not _SHA256.fullmatch(digest):
        raise ValueError("sha256 must be 64 lowercase hexadecimal characters")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("size must be a non-negative integer")
    filename = _required_text(name, "name")
    mime = _required_text(mime_type, "mime_type")
    reference = _required_text(runtime_reference, "runtime_reference")
    created = _required_text(created_at, "created_at")
    if not isinstance(metadata, Mapping):
        raise ValueError("metadata must be an object")
    normalized_metadata = json.loads(json.dumps(dict(metadata), ensure_ascii=False, sort_keys=True))
    return session, file, digest, size, filename, mime, reference, created, normalized_metadata


@dataclass(frozen=True)
class SessionFileRecord:
    session_id: str
    file_id: str
    sha256: str
    size: int
    name: str
    mime_type: str
    runtime_reference: str
    created_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        values = _validate_record_values(
            self.session_id,
            self.file_id,
            self.sha256,
            self.size,
            self.name,
            self.mime_type,
            self.runtime_reference,
            self.created_at,
            self.metadata,
        )
        for field_name, value in zip(
            ("session_id", "file_id", "sha256", "size", "name", "mime_type", "runtime_reference", "created_at", "metadata"),
            values,
        ):
            object.__setattr__(self, field_name, value)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SessionFileRecord":
        if not isinstance(value, Mapping):
            raise ValueError("session file record must be an object")
        required = (
            "session_id",
            "file_id",
            "sha256",
            "size",
            "name",
            "mime_type",
            "runtime_reference",
            "created_at",
        )
        missing = [field_name for field_name in required if field_name not in value]
        if missing:
            raise ValueError(f"session file record missing fields: {', '.join(missing)}")
        return cls(
            session_id=value["session_id"],
            file_id=value["file_id"],
            sha256=value["sha256"],
            size=value["size"],
            name=value["name"],
            mime_type=value["mime_type"],
            runtime_reference=value["runtime_reference"],
            created_at=value["created_at"],
            metadata=value.get("metadata", {}),
        )


class SessionFileConflictError(ValueError):
    """Raised when a host reuses one session/file identity with a new hash."""


class SessionFileAmbiguousError(KeyError):
    """Raised when a file name resolves to multiple session records."""


class SessionFileRegistry:
    """Persist stable file references without persisting file content."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._records: dict[str, list[SessionFileRecord]] = defaultdict(list)

    def register(
        self,
        session_id: str,
        file_id: str,
        sha256: str,
        size: int,
        name: str,
        mime_type: str,
        runtime_reference: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> SessionFileRecord:
        record = SessionFileRecord(
            session_id=session_id,
            file_id=file_id,
            sha256=sha256,
            size=size,
            name=name,
            mime_type=mime_type,
            runtime_reference=runtime_reference,
            created_at=_now(),
            metadata=dict(metadata or {}),
        )
        records = self._records[record.session_id]
        for existing in records:
            if existing.file_id != record.file_id:
                continue
            if existing.sha256 != record.sha256:
                raise SessionFileConflictError(
                    f"file identity conflict for session={record.session_id}, file_id={record.file_id}"
                )
            return existing
        records.append(record)
        self.save()
        return record

    def list(self, session_id: str) -> tuple[SessionFileRecord, ...]:
        session = _required_text(session_id, "session_id")
        return tuple(self._records.get(session, ()))

    def resolve(
        self,
        session_id: str,
        *,
        file_id: str | None = None,
        name: str | None = None,
    ) -> SessionFileRecord:
        session = _required_text(session_id, "session_id")
        if file_id is None and name is None:
            raise ValueError("file_id or name is required")
        if file_id is not None:
            file_id = _required_text(file_id, "file_id")
        if name is not None:
            name = _required_text(name, "name")
        matches = [
            record
            for record in self._records.get(session, ())
            if (file_id is None or record.file_id == file_id)
            and (name is None or record.name == name)
        ]
        if not matches:
            raise KeyError(f"session file not found: session={session}")
        if len(matches) > 1:
            raise SessionFileAmbiguousError(f"session file name is ambiguous: session={session}, name={name}")
        return matches[0]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "records": [
                record.to_dict()
                for records in self._records.values()
                for record in records
            ],
        }
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{self.path.name}.",
            suffix=".tmp",
            dir=self.path.parent,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, self.path)
        finally:
            if os.path.exists(temporary_name):
                os.unlink(temporary_name)

    @classmethod
    def load(cls, path: Path) -> "SessionFileRegistry":
        registry = cls(path)
        if not registry.path.exists():
            return registry
        try:
            document = json.loads(registry.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid session file registry: {registry.path}") from exc
        if not isinstance(document, Mapping) or document.get("schema_version") != _SCHEMA_VERSION:
            raise ValueError("unsupported session file registry")
        records = document.get("records")
        if not isinstance(records, list):
            raise ValueError("session file registry records must be a list")
        for raw_record in records:
            record = SessionFileRecord.from_dict(raw_record)
            existing = registry._records[record.session_id]
            if any(item.file_id == record.file_id for item in existing):
                raise ValueError(f"duplicate session file identity: {record.session_id}/{record.file_id}")
            existing.append(record)
        return registry

