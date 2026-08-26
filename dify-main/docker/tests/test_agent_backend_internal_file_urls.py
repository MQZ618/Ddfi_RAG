import os
import subprocess


IMAGE = os.environ.get(
    "DIFY_AGENT_BACKEND_IMAGE", "local/dify-agent-backend:1.16.1-pdf-internal-url"
)
ROOT = "/app/api/.venv/lib/python3.12/site-packages/dify_agent"


def _read(path: str) -> str:
    return subprocess.check_output(
        ["docker", "run", "--rm", "--entrypoint", "cat", IMAGE, path], text=True
    )


def test_agent_file_downloads_default_to_internal_urls() -> None:
    protocol = _read(f"{ROOT}/agent_stub/protocol/agent_stub.py")
    tools_layer = _read(f"{ROOT}/layers/dify_plugin/tools_layer.py")

    assert "for_external: bool = False" in protocol
    assert '"for_external": False' in tools_layer
