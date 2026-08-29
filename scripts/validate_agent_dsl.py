#!/usr/bin/env python3
"""Validate the repository's Dify Agent DSL without contacting Dify."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


_CREDENTIAL_KEY = re.compile(r"(?:api[_-]?key|access[_-]?token|authorization|client[_-]?secret|password)", re.IGNORECASE)


@dataclass(frozen=True)
class AgentDslValidation:
    errors: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def is_valid(self) -> bool:
        return not self.errors


def _walk_credential_keys(value: Any, path: str = "root") -> list[str]:
    hits: list[str] = []
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if _CREDENTIAL_KEY.search(str(key)):
                hits.append(child_path)
            hits.extend(_walk_credential_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            hits.extend(_walk_credential_keys(child, f"{path}[{index}]"))
    return hits


def validate_document(document: Mapping[str, Any]) -> AgentDslValidation:
    """Return structural errors and non-fatal missing-asset warnings."""
    errors: list[str] = []
    warnings: list[str] = []

    if not isinstance(document, Mapping):
        return AgentDslValidation(("DSL root must be a mapping",), ())
    if document.get("kind") != "app":
        errors.append("DSL kind must be 'app'")

    app = document.get("app")
    if not isinstance(app, Mapping):
        errors.append("missing 'app' mapping")
    elif app.get("mode") != "agent":
        errors.append("app.mode must be 'agent'")

    agent = document.get("agent")
    packages = document.get("agent_packages")
    if not isinstance(agent, Mapping) or not isinstance(agent.get("package_ref"), str):
        errors.append("missing agent.package_ref")
        package = None
    elif not isinstance(packages, Mapping):
        errors.append("missing agent_packages mapping")
        package = None
    else:
        package_ref = agent["package_ref"]
        package = packages.get(package_ref)
        if not isinstance(package, Mapping):
            errors.append(f"agent package not found: {package_ref}")

    if isinstance(package, Mapping):
        soul = package.get("soul")
        if not isinstance(soul, Mapping):
            errors.append("agent package is missing soul mapping")
        else:
            prompt = soul.get("prompt")
            if not isinstance(prompt, Mapping) or not isinstance(prompt.get("system_prompt"), str) or not prompt["system_prompt"].strip():
                errors.append("agent soul prompt.system_prompt must be non-empty")

            skills = soul.get("config_skills")
            if not isinstance(skills, list):
                errors.append("agent soul config_skills must be a list")
            else:
                for index, skill in enumerate(skills):
                    if not isinstance(skill, Mapping):
                        errors.append(f"config_skills[{index}] must be a mapping")
                        continue
                    name = skill.get("name")
                    if not isinstance(name, str) or not name.strip():
                        errors.append(f"config_skills[{index}].name must be non-empty")
                        continue
                    missing = skill.get("is_missing", False)
                    if not isinstance(missing, bool):
                        errors.append(f"config_skills[{index}].is_missing must be boolean")
                    elif missing:
                        if skill.get("file_id", ""):
                            errors.append(f"missing Skill retains file_id: {name}")
                        warnings.append(f"Dify Skill asset requires upload: {name}")
                    elif not isinstance(skill.get("file_id"), str) or not skill["file_id"].strip():
                        errors.append(f"bound Skill has no file_id: {name}")

            knowledge = soul.get("knowledge")
            if not isinstance(knowledge, Mapping) or not isinstance(knowledge.get("sets"), list):
                errors.append("agent soul knowledge.sets must be a list")
            tools = soul.get("tools")
            if not isinstance(tools, Mapping):
                errors.append("agent soul tools must be a mapping")

    for path in _walk_credential_keys(document):
        errors.append(f"credential-bearing field is not allowed in DSL: {path}")

    return AgentDslValidation(tuple(errors), tuple(warnings))


def _load_yaml(path: Path) -> Mapping[str, Any]:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - exercised by CLI environment setup
        raise RuntimeError("PyYAML is required for Agent DSL validation; install the Dify extra") from exc
    with path.open(encoding="utf-8") as handle:
        document = yaml.safe_load(handle)
    if not isinstance(document, Mapping):
        raise ValueError("DSL YAML must contain a mapping at the root")
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dsl_file", type=Path)
    args = parser.parse_args(argv)
    try:
        result = validate_document(_load_yaml(args.dsl_file))
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1
    for warning in result.warnings:
        print(f"WARNING: {warning}")
    for error in result.errors:
        print(f"ERROR: {error}")
    if result.is_valid:
        print("OK")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
