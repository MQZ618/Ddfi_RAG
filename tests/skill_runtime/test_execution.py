from __future__ import annotations

import pytest

from skill_runtime import (
    ActionNotAllowed,
    BudgetExceeded,
    ExecutionBudget,
    TaskKind,
)


def test_simple_text_has_zero_tool_calls_and_no_search_or_files():
    budget = ExecutionBudget.for_task(TaskKind.SIMPLE_TEXT)

    assert budget.max_tool_calls == 0
    assert budget.allow_external_search is False
    assert budget.allow_file_generation is False
    assert budget.allow_export is False
    assert budget.allow_shell is False

    with pytest.raises(ActionNotAllowed):
        budget.check("external_search")
    with pytest.raises(ActionNotAllowed):
        budget.check("file_generate")


def test_attachment_read_allows_bounded_reads_but_not_unrequested_generation():
    budget = ExecutionBudget.for_task(TaskKind.ATTACHMENT_READ)

    budget.check("file_read", tool_calls_used=0)
    with pytest.raises(ActionNotAllowed):
        budget.check("file_generate")
    with pytest.raises(BudgetExceeded):
        budget.check("file_read", tool_calls_used=budget.max_tool_calls)


def test_search_and_export_require_explicit_user_authorization():
    search = ExecutionBudget.for_task(TaskKind.LITERATURE_SEARCH, user_requested_search=True)
    search.check("external_search")

    export = ExecutionBudget.for_task(TaskKind.DOCUMENT_EXPORT, user_requested_file=True)
    export.check("file_generate")
    export.check("export")


def test_stop_policy_stops_when_sufficient_or_limit_reached():
    budget = ExecutionBudget.for_task(TaskKind.ATTACHMENT_READ)

    assert budget.should_stop(sufficient=True, tool_calls_used=1, generated_files=0) is True
    assert budget.should_stop(sufficient=False, tool_calls_used=budget.max_tool_calls, generated_files=0) is True
    assert budget.should_stop(sufficient=False, tool_calls_used=0, generated_files=0) is False


def test_budget_rejects_unknown_actions_and_invalid_counters():
    budget = ExecutionBudget.for_task(TaskKind.RESEARCH_WORKFLOW)

    with pytest.raises(ValueError, match="unsupported action"):
        budget.check("send_email")
    with pytest.raises(ValueError, match="non-negative"):
        budget.check("file_read", tool_calls_used=-1)

