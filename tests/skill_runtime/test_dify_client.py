from __future__ import annotations

from tests.dify_workflow.dify_client import DifyClient
from skill_runtime import SessionFileRegistry


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def json(self) -> dict:
        return self.payload


class FakeHttpClient:
    def __init__(self):
        self.posts: list[dict] = []

    def post(self, url: str, **kwargs):
        self.posts.append({"url": url, **kwargs})
        return FakeResponse({"conversation_id": "conversation-1", "answer": "ok"})


def test_chat_rebinds_registered_files_for_later_conversation_turn(tmp_path):
    registry = SessionFileRegistry(tmp_path / "session-files.json")
    http = FakeHttpClient()
    client = DifyClient(
        "http://localhost",
        "test-key",
        file_registry=registry,
        http_client=http,
    )
    client.remember_file(
        "conversation-1",
        file_id="upload-1",
        sha256="a" * 64,
        size=12,
        name="report.md",
        mime_type="text/markdown",
    )

    client.chat("continue", conversation_id="conversation-1")

    assert http.posts[0]["json"]["files"] == [
        {
            "type": "document",
            "transfer_method": "local_file",
            "upload_file_id": "upload-1",
        }
    ]


def test_chat_does_not_rebind_files_when_empty_list_is_explicit(tmp_path):
    registry = SessionFileRegistry(tmp_path / "session-files.json")
    http = FakeHttpClient()
    client = DifyClient("http://localhost", "test-key", file_registry=registry, http_client=http)
    client.remember_file(
        "conversation-1",
        file_id="upload-1",
        sha256="a" * 64,
        size=12,
        name="report.md",
        mime_type="text/markdown",
    )

    client.chat("ignore prior files", conversation_id="conversation-1", files=[])

    assert "files" not in http.posts[0]["json"]
