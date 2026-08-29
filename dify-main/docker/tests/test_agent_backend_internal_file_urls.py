import subprocess


BACKEND = "docker-agent_backend-1"
ROOT = "/app/api/.venv/lib/python3.12/site-packages/dify_agent"


def _read(path: str) -> str:
    return subprocess.check_output(
        ["docker", "exec", BACKEND, "cat", path], text=True
    )


def test_agent_file_downloads_default_to_internal_urls() -> None:
    protocol = _read(f"{ROOT}/agent_stub/protocol/agent_stub.py")
    tools_layer = _read(f"{ROOT}/layers/dify_plugin/tools_layer.py")

    assert "for_external: bool = False" in protocol
    assert '"for_external": False' in tools_layer
