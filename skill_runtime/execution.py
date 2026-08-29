"""Deterministic execution budgets for bounded host-side actions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class TaskKind(str, Enum):
    SIMPLE_TEXT = "simple_text"
    ATTACHMENT_READ = "attachment_read"
    LITERATURE_SEARCH = "literature_search"
    DOCUMENT_EXPORT = "document_export"
    RESEARCH_WORKFLOW = "research_workflow"


class ActionNotAllowed(PermissionError):
    """Raised when the task policy does not permit an action."""


class BudgetExceeded(RuntimeError):
    """Raised when an otherwise permitted action exceeds its hard budget."""


_ACTIONS = {"file_read", "file_generate", "external_search", "shell", "export"}


@dataclass(frozen=True)
class ExecutionBudget:
    max_tool_calls: int
    max_generated_files: int
    allow_file_generation: bool
    allow_export: bool
    allow_external_search: bool
    allow_shell: bool
    stop_when_sufficient: bool = True

    def __post_init__(self) -> None:
        if isinstance(self.max_tool_calls, bool) or self.max_tool_calls < 0:
            raise ValueError("max_tool_calls must be a non-negative integer")
        if isinstance(self.max_generated_files, bool) or self.max_generated_files < 0:
            raise ValueError("max_generated_files must be a non-negative integer")

    @classmethod
    def for_task(
        cls,
        kind: TaskKind | str,
        *,
        user_requested_file: bool = False,
        user_requested_search: bool = False,
    ) -> "ExecutionBudget":
        try:
            task_kind = kind if isinstance(kind, TaskKind) else TaskKind(kind)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"unsupported task kind: {kind}") from exc

        defaults: dict[TaskKind, dict[str, Any]] = {
            TaskKind.SIMPLE_TEXT: {
                "max_tool_calls": 0,
                "max_generated_files": 0,
                "allow_shell": False,
            },
            TaskKind.ATTACHMENT_READ: {
                "max_tool_calls": 4,
                "max_generated_files": 0,
                "allow_shell": False,
            },
            TaskKind.LITERATURE_SEARCH: {
                "max_tool_calls": 6,
                "max_generated_files": 0,
                "allow_shell": False,
            },
            TaskKind.DOCUMENT_EXPORT: {
                "max_tool_calls": 8,
                "max_generated_files": 2,
                "allow_shell": True,
            },
            TaskKind.RESEARCH_WORKFLOW: {
                "max_tool_calls": 12,
                "max_generated_files": 3,
                "allow_shell": True,
            },
        }[task_kind]
        can_search = bool(user_requested_search) and task_kind in {
            TaskKind.LITERATURE_SEARCH,
            TaskKind.RESEARCH_WORKFLOW,
        }
        can_generate = bool(user_requested_file) and task_kind in {
            TaskKind.DOCUMENT_EXPORT,
            TaskKind.RESEARCH_WORKFLOW,
        }
        return cls(
            max_tool_calls=defaults["max_tool_calls"],
            max_generated_files=defaults["max_generated_files"] if can_generate else 0,
            allow_file_generation=can_generate,
            allow_export=can_generate,
            allow_external_search=can_search,
            allow_shell=defaults["allow_shell"] and task_kind is not TaskKind.SIMPLE_TEXT,
        )

    def _validate_counters(self, tool_calls_used: int, generated_files: int) -> None:
        for name, value in (
            ("tool_calls_used", tool_calls_used),
            ("generated_files", generated_files),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a non-negative integer")

    def check(
        self,
        action: str,
        *,
        tool_calls_used: int = 0,
        generated_files: int = 0,
    ) -> None:
        if action not in _ACTIONS:
            raise ValueError(f"unsupported action: {action}")
        self._validate_counters(tool_calls_used, generated_files)

        permissions = {
            "file_generate": self.allow_file_generation,
            "export": self.allow_export,
            "external_search": self.allow_external_search,
            "shell": self.allow_shell,
            "file_read": self.max_tool_calls > 0,
        }
        if not permissions[action]:
            raise ActionNotAllowed(f"action not allowed by task budget: {action}")
        if tool_calls_used >= self.max_tool_calls:
            raise BudgetExceeded(f"tool-call budget exhausted before action: {action}")
        if action == "file_generate" and generated_files >= self.max_generated_files:
            raise BudgetExceeded("generated-file budget exhausted before action")

    def should_stop(
        self,
        sufficient: bool,
        tool_calls_used: int,
        generated_files: int,
    ) -> bool:
        self._validate_counters(tool_calls_used, generated_files)
        if self.stop_when_sufficient and sufficient:
            return True
        if self.max_tool_calls == 0 or tool_calls_used >= self.max_tool_calls:
            return True
        if self.max_generated_files > 0 and generated_files >= self.max_generated_files:
            return True
        return False

