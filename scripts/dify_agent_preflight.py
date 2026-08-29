#!/usr/bin/env python3
"""Run a read-only preflight against a Dify Agent App API."""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


Opener = Callable[..., Any]


class DifyPreflightError(RuntimeError):
    """Raised when the read-only Dify preflight cannot be completed."""


def _fetch_json(opener: Opener, url: str, api_key: str) -> Mapping[str, Any]:
    request = Request(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        method="GET",
    )
    try:
        with opener(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise DifyPreflightError(f"Dify GET failed with HTTP {exc.code}: check the API key") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DifyPreflightError(f"Dify GET failed: {exc.reason if isinstance(exc, URLError) else exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DifyPreflightError("Dify returned a non-JSON response") from exc
    if not isinstance(payload, Mapping):
        raise DifyPreflightError("Dify response must be a JSON object")
    return payload


def _safe_info(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in ("name", "mode") if key in payload}


def _safe_parameters(payload: Mapping[str, Any]) -> dict[str, Any]:
    file_upload = payload.get("file_upload")
    if isinstance(file_upload, Mapping):
        return {"file_upload": dict(file_upload)}
    return {}


def check_agent(base_url: str, api_key: str, opener: Opener | None = None) -> dict[str, Any]:
    """Read only the public Agent info and parameter endpoints."""
    if not isinstance(base_url, str) or not base_url.strip():
        raise DifyPreflightError("DIFY_BASE_URL is required")
    if not isinstance(api_key, str) or not api_key.strip():
        raise DifyPreflightError("DIFY_API_KEY is required")
    root = base_url.rstrip("/")
    if root.endswith("/v1"):
        root = root[:-3].rstrip("/")
    request_opener = opener or urlopen
    info = _fetch_json(request_opener, f"{root}/v1/info", api_key)
    parameters = _fetch_json(request_opener, f"{root}/v1/parameters", api_key)
    return {"info": _safe_info(info), "parameters": _safe_parameters(parameters)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=None, help="Dify root URL; defaults to DIFY_BASE_URL or localhost")
    parser.add_argument("--api-key", default=None, help="Dify App API key; defaults to DIFY_API_KEY")
    args = parser.parse_args(argv)
    base_url = args.base_url or os.environ.get("DIFY_BASE_URL") or os.environ.get("DIFY_API_URL", "http://localhost")
    api_key = args.api_key if args.api_key is not None else os.environ.get("DIFY_API_KEY", "")
    try:
        result = check_agent(base_url, api_key)
    except DifyPreflightError as exc:
        print(f"ERROR: {exc}")
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
