"""Tests for agent registration, handoffs, and fail-closed data checks."""
import pytest
from indian_swing_trader.agents.contracts import AgentResult, AgentTask
from indian_swing_trader.agents.deterministic import DataQualityAgent, InputValidationAgent
from indian_swing_trader.agents.orchestrator import AgentOrchestrator
from indian_swing_trader.agents.registry import AgentRegistry

def build_runtime():
    registry = AgentRegistry()
    registry.register(InputValidationAgent())
    registry.register(DataQualityAgent())
    return AgentOrchestrator(registry), registry

def test_agents_are_registered_and_route_by_task_kind():
    runtime, registry = build_runtime()
    assert registry.names == ("data-quality", "input-validator")
    results = runtime.run(AgentTask("research-1", "validate_research_request", {"symbols": ["reliance", "TCS"]}))
    assert [result.agent_name for result in results] == ["input-validator", "data-quality"]
    assert results[0].output["symbols"] == ["RELIANCE", "TCS"]
    assert results[1].status == "blocked"

def test_missing_symbols_are_rejected_without_handoff():
    runtime, _ = build_runtime()
    results = runtime.run(AgentTask("research-2", "validate_research_request", {"symbols": []}))
    assert len(results) == 1
    assert results[0].status == "rejected"

def test_data_quality_requires_source_and_timestamp():
    agent = DataQualityAgent()
    result = agent.handle(AgentTask("dq-1", "check_data_quality", {"symbols": ["TCS"], "data_evidence": {"source": "NSE"}}))
    assert result.status == "blocked"

def test_registry_rejects_duplicate_task_routes():
    registry = AgentRegistry()
    registry.register(InputValidationAgent())
    class ConflictingAgent:
        name = "conflict"
        supported_kinds = frozenset({"validate_research_request"})
        def handle(self, task):
            return AgentResult(self.name, task.task_id, "ok")
    with pytest.raises(ValueError, match="already routed"):
        registry.register(ConflictingAgent())

def test_orchestrator_enforces_task_budget():
    class LoopAgent:
        name = "loop"
        supported_kinds = frozenset({"loop"})
        def handle(self, task):
            child = AgentTask(task.task_id + ":next", "loop", parent_task_id=task.task_id)
            return AgentResult(self.name, task.task_id, "ok", next_tasks=(child,))
    registry = AgentRegistry()
    registry.register(LoopAgent())
    with pytest.raises(RuntimeError, match="task budget"):
        AgentOrchestrator(registry, max_tasks=2).run(AgentTask("loop-1", "loop"))
