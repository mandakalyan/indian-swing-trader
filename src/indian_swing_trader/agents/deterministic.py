"""Example deterministic agents proving the handoff contract."""
from __future__ import annotations
from indian_swing_trader.agents.contracts import AgentResult, AgentTask

class InputValidationAgent:
    """Reject incomplete stock-research requests before downstream work."""
    name = "input-validator"
    supported_kinds = frozenset({"validate_research_request"})

    def handle(self, task: AgentTask) -> AgentResult:
        symbols = task.payload.get("symbols")
        if not isinstance(symbols, list) or not symbols:
            return AgentResult(self.name, task.task_id, "rejected", findings=("At least one symbol is required.",))
        normalized = sorted({str(symbol).strip().upper() for symbol in symbols if str(symbol).strip()})
        if not normalized:
            return AgentResult(self.name, task.task_id, "rejected", findings=("No valid symbols were supplied.",))
        follow_up = AgentTask(
            task_id=f"{task.task_id}:data-quality",
            kind="check_data_quality",
            payload={"symbols": normalized},
            parent_task_id=task.task_id,
        )
        return AgentResult(self.name, task.task_id, "accepted", output={"symbols": normalized}, next_tasks=(follow_up,))

class DataQualityAgent:
    """Require explicit freshness/completeness evidence; never invent market data."""
    name = "data-quality"
    supported_kinds = frozenset({"check_data_quality"})

    def handle(self, task: AgentTask) -> AgentResult:
        evidence = task.payload.get("data_evidence")
        if evidence is None:
            return AgentResult(self.name, task.task_id, "blocked", findings=("Market data evidence was not supplied; analysis was not run.",))
        if not isinstance(evidence, dict) or not evidence.get("source") or not evidence.get("as_of"):
            return AgentResult(self.name, task.task_id, "blocked", findings=("Evidence must include source and as_of timestamp.",))
        return AgentResult(
            self.name, task.task_id, "accepted",
            output={"symbols": task.payload.get("symbols", []), "evidence": evidence},
            findings=("Evidence metadata present; freshness policy must be checked by caller.",),
        )
