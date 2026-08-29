from __future__ import annotations

import json

import pytest

from scripts.dify_agent_preflight import DifyPreflightError, check_agent


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args) -> None:
        return None


class RecordingOpener:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout: int):
        self.requests.append((request, timeout))
        if request.full_url.endswith("/v1/info"):
            return FakeResponse({"name": "科研助手", "mode": "agent", "description": ""})
        if request.full_url.endswith("/v1/parameters"):
            return FakeResponse({"file_upload": {"enabled": True}, "system_parameters": {}})
        raise AssertionError(f"unexpected URL: {request.full_url}")


def test_check_agent_only_reads_info_and_parameters_and_returns_redacted_metadata():
    opener = RecordingOpener()

    result = check_agent("http://localhost", "secret-api-key", opener=opener)

    assert [request.full_url for request, _ in opener.requests] == [
        "http://localhost/v1/info",
        "http://localhost/v1/parameters",
    ]
    assert all(request.method == "GET" for request, _ in opener.requests)
    assert result == {
        "info": {"name": "科研助手", "mode": "agent"},
        "parameters": {"file_upload": {"enabled": True}},
    }
    assert "secret-api-key" not in repr(result)


def test_check_agent_rejects_missing_api_key_before_network_call():
    opener = RecordingOpener()

    with pytest.raises(DifyPreflightError, match="DIFY_API_KEY is required"):
        check_agent("http://localhost", "", opener=opener)

    assert opener.requests == []
