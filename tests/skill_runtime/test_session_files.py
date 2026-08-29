from __future__ import annotations

import json

import pytest

from skill_runtime import (
    SessionFileAmbiguousError,
    SessionFileConflictError,
    SessionFileRegistry,
)


def test_registry_round_trips_metadata_without_content(tmp_path):
    registry = SessionFileRegistry(tmp_path / "files.json")
    record = registry.register(
        "conversation-1",
        "upload-1",
        "a" * 64,
        12,
        "report.md",
        "text/markdown",
        "dify-file-ref:opaque",
        metadata={"source": "web"},
    )

    assert registry.resolve("conversation-1", file_id="upload-1") == record
    assert SessionFileRegistry.load(tmp_path / "files.json").list("conversation-1") == (record,)

    persisted = json.loads((tmp_path / "files.json").read_text(encoding="utf-8"))
    assert persisted["records"][0]["file_id"] == "upload-1"
    assert "content" not in persisted["records"][0]
    assert "report body" not in (tmp_path / "files.json").read_text(encoding="utf-8")


def test_registry_rejects_same_file_id_with_changed_hash(tmp_path):
    registry = SessionFileRegistry(tmp_path / "files.json")
    registry.register("s", "f", "a" * 64, 1, "a.md", "text/markdown", "ref-a")

    with pytest.raises(SessionFileConflictError):
        registry.register("s", "f", "b" * 64, 1, "a.md", "text/markdown", "ref-b")


def test_registry_requires_explicit_reference_for_ambiguous_name(tmp_path):
    registry = SessionFileRegistry(tmp_path / "files.json")
    registry.register("s", "f1", "a" * 64, 1, "same.md", "text/markdown", "ref-1")
    registry.register("s", "f2", "b" * 64, 1, "same.md", "text/markdown", "ref-2")

    with pytest.raises(SessionFileAmbiguousError):
        registry.resolve("s", name="same.md")


def test_registry_returns_stable_session_order_and_missing_is_key_error(tmp_path):
    registry = SessionFileRegistry(tmp_path / "files.json")
    first = registry.register("s", "f1", "a" * 64, 1, "first.md", "text/markdown", "ref-1")
    second = registry.register("s", "f2", "b" * 64, 2, "second.md", "text/markdown", "ref-2")

    assert registry.list("s") == (first, second)
    with pytest.raises(KeyError):
        registry.resolve("s", file_id="missing")

