"""Stable contracts shared by agents and the orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class AgentTask:
    """A named unit of work with explicit input and correlation identity."""
    task_id: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    parent_task_id: str | None = None


@dataclass(frozen=True, slots=True)
class AgentResult:
    """An agent's auditable result; agents do not mutate shared task state."""
    agent_name: str
    task_id: str
    status: str
    output: dict[str, Any] = field(default_factory=dict)
    findings: tuple[str, ...] = ()
    next_tasks: tuple[AgentTask, ...] = ()


class Agent(Protocol):
    """Contract implemented by every independently registered agent."""
    name: str
    supported_kinds: frozenset[str]

    def handle(self, task: AgentTask) -> AgentResult:
        """Handle one task and return a result or explicit handoff tasks."""
