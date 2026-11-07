"""Bounded task dispatcher with explicit agent-to-agent handoffs."""
from __future__ import annotations
from collections import deque
from indian_swing_trader.agents.contracts import AgentResult, AgentTask
from indian_swing_trader.agents.registry import AgentRegistry

class AgentOrchestrator:
    """Dispatch tasks without giving agents shared mutable state or credentials.

    Agents communicate only by returning typed follow-up tasks. A maximum task
    budget prevents accidental loops. Execution is sequential in this first
    runtime; the contract permits a future queue/worker implementation.
    """
    def __init__(self, registry: AgentRegistry, *, max_tasks: int = 20) -> None:
        if max_tasks < 1:
            raise ValueError("max_tasks must be positive")
        self.registry = registry
        self.max_tasks = max_tasks

    def run(self, initial_task: AgentTask) -> tuple[AgentResult, ...]:
        pending = deque([initial_task])
        results: list[AgentResult] = []
        seen: set[str] = set()
        while pending:
            if len(results) >= self.max_tasks:
                raise RuntimeError("Agent task budget exceeded; possible handoff loop")
            task = pending.popleft()
            if task.task_id in seen:
                raise ValueError(f"Duplicate task id: {task.task_id}")
            seen.add(task.task_id)
            agent = self.registry.resolve(task.kind)
            result = agent.handle(task)
            if result.task_id != task.task_id or result.agent_name != agent.name:
                raise ValueError("Agent result identity does not match dispatched task")
            results.append(result)
            pending.extend(result.next_tasks)
        return tuple(results)
