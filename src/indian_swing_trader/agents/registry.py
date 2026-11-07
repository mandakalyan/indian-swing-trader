"""Agent registration and task routing."""
from __future__ import annotations
from indian_swing_trader.agents.contracts import Agent

class AgentRegistry:
    """Maps task kinds to one agent and rejects ambiguous registrations."""
    def __init__(self) -> None:
        self._agents: dict[str, Agent] = {}
        self._routes: dict[str, str] = {}

    def register(self, agent: Agent) -> None:
        if not agent.name.strip() or not agent.supported_kinds:
            raise ValueError("Agents need a name and at least one supported task kind")
        if agent.name in self._agents:
            raise ValueError(f"Agent already registered: {agent.name}")
        duplicates = self._routes.keys() & agent.supported_kinds
        if duplicates:
            raise ValueError(f"Task kinds already routed: {sorted(duplicates)}")
        self._agents[agent.name] = agent
        for kind in agent.supported_kinds:
            self._routes[kind] = agent.name

    def resolve(self, task_kind: str) -> Agent:
        try:
            return self._agents[self._routes[task_kind]]
        except KeyError as exc:
            raise LookupError(f"No agent registered for task kind: {task_kind}") from exc

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._agents))
