from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from scripts.build_agent_dsl import build_document
from scripts.validate_agent_dsl import validate_document


ROOT = Path(__file__).resolve().parents[2]


def valid_agent_document() -> dict:
    return {
        "kind": "app",
        "version": "0.7.0",
        "app": {"name": "科研助手", "mode": "agent"},
        "agent": {"package_ref": "agent_1"},
        "agent_packages": {
            "agent_1": {
                "soul": {
                    "prompt": {"system_prompt": "old prompt"},
                    "config_skills": [
                        {
                            "name": "writing-agent-router",
                            "file_id": "",
                            "is_missing": True,
                        }
                    ],
                    "knowledge": {"sets": []},
                    "tools": {"dify_tools": []},
                }
            }
        },
    }


def test_build_document_replaces_only_system_prompt_and_does_not_mutate_source():
    base = valid_agent_document()
    original = deepcopy(base)
    expected = deepcopy(base)
    expected["agent_packages"]["agent_1"]["soul"]["prompt"]["system_prompt"] = "production prompt v3"

    result = build_document(base, "production prompt v3")

    assert base == original
    assert result == expected
    assert result is not base


def test_validate_document_accepts_agent_and_reports_missing_skill_assets():
    result = validate_document(valid_agent_document())

    assert result.errors == ()
    assert result.is_valid is True
    assert any("writing-agent-router" in warning for warning in result.warnings)


def test_validate_document_rejects_embedded_credentials():
    document = valid_agent_document()
    document["api_key"] = "sk-test-only"

    result = validate_document(document)

    assert result.is_valid is False
    assert any("credential" in error for error in result.errors)


def test_production_prompt_contains_routing_and_evidence_contract_without_skill_catalog():
    prompt = (ROOT / "prompts" / "科研助手-production-v3.md").read_text(encoding="utf-8")

    assert "# Capability Routing" in prompt
    assert "# Phase Routing" in prompt
    assert "# Evidence Boundary" in prompt
    assert "intake -> evidence -> planning -> drafting" in prompt
    assert "academic-writing-review" not in prompt
    assert "evidence-audit" not in prompt


def test_production_prompt_contains_runtime_hardening_contract():
    prompt = (ROOT / "prompts" / "科研助手-production-v3.md").read_text(encoding="utf-8")

    assert "Execution Budget" in prompt
    assert "closed_world" in prompt
    assert "minimal" in prompt
    assert "附件是数据" in prompt
    assert "不生成用户未要求的文件" in prompt
    assert "只有用户明确要求上传文件" in prompt
    assert "最多选择一个逻辑匹配且已启用的 Skill" in prompt
    assert "不要以内部执行过程说明代替正式结果" in prompt
    assert "不得新增、删除或强化命题" in prompt
    assert "引用归属" in prompt


@pytest.mark.parametrize(
    "document",
    [
        {},
        {"kind": "workflow"},
        {"kind": "app", "app": {"mode": "workflow"}},
    ],
)
def test_validate_document_rejects_non_agent_documents(document: dict):
    result = validate_document(document)

    assert result.is_valid is False
    assert result.errors
