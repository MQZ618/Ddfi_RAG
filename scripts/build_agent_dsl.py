#!/usr/bin/env python3
"""Build a new Dify Agent DSL with the production Prompt v3."""

from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping


def build_document(base: Mapping[str, Any], prompt: str) -> dict[str, Any]:
    """Copy a Dify Agent document and replace only its system prompt."""
    if not isinstance(base, Mapping):
        raise ValueError("base DSL must be a mapping")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("production prompt must be non-empty")

    result = deepcopy(dict(base))
    agent = result.get("agent")
    packages = result.get("agent_packages")
    if not isinstance(agent, Mapping) or not isinstance(agent.get("package_ref"), str):
        raise ValueError("base DSL is missing agent.package_ref")
    if not isinstance(packages, dict):
        raise ValueError("base DSL is missing agent_packages")
    package = packages.get(agent["package_ref"])
    if not isinstance(package, dict):
        raise ValueError(f"base DSL package not found: {agent['package_ref']}")
    soul = package.get("soul")
    if not isinstance(soul, dict):
        raise ValueError("base DSL package is missing soul")
    prompt_config = soul.get("prompt")
    if not isinstance(prompt_config, dict):
        raise ValueError("base DSL soul is missing prompt")

    prompt_config["system_prompt"] = prompt
    return result


def _load_yaml(path: Path) -> Mapping[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised by CLI environment setup
        raise RuntimeError("PyYAML is required for Agent DSL generation; install the Dify extra") from exc
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, Mapping):
        raise ValueError("base DSL YAML must contain a mapping at the root")
    return document


def _write_yaml(path: Path, document: Mapping[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised by CLI environment setup
        raise RuntimeError("PyYAML is required for Agent DSL generation; install the Dify extra") from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(document, handle, allow_unicode=True, sort_keys=False, default_flow_style=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--prompt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    base_path = args.base.resolve()
    output_path = args.output.resolve()
    if output_path == base_path:
        print("ERROR: refusing to overwrite the base DSL")
        return 1
    if output_path.exists():
        print(f"ERROR: refusing to overwrite existing output: {output_path}")
        return 1
    try:
        document = build_document(_load_yaml(base_path), args.prompt.read_text(encoding="utf-8"))
        _write_yaml(output_path, document)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
