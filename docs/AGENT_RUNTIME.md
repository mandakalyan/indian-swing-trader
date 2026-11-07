# Hybrid agent runtime (foundation)

## Architecture

The runtime has an explicit agent contract, registry, task router, and bounded
orchestrator. Agents are independently implemented units with their own supported
task types. They do not mutate shared state: each receives an AgentTask and returns
an AgentResult containing findings and optional handoff tasks. The orchestrator
records results and dispatches follow-up tasks to the registered agent for that kind.

User / CLI / scheduled workflow -> AgentOrchestrator -> AgentRegistry ->
InputValidationAgent -> DataQualityAgent (explicit task handoff).

The example workflow validates a requested symbol list, then hands off to a
data-quality agent. That agent fails closed if source and timestamp evidence are
absent. It does not fetch prices, calculate indicators, or make buy/sell calls.

## Agent boundaries

- Input validation normalizes and validates the requested stock universe.
- Data quality checks that evidence metadata is present before analysis.
- Future technical analysis calculates deterministic indicators from validated OHLCV.
- Future fundamental research summarizes sourced facts and flags missing periods.
- Future risk review independently enforces position sizing and risk limits.
- Future synthesis combines findings while retaining source references and uncertainty.

## Model strategy and cost

**Phase 1 (this PR): deterministic agents only.** No model API, API key, paid
inference, external agent framework, or always-on server is required. GitHub Actions
can run tests and scheduled workflows within applicable repository allowances. The
orchestration runtime is sequential and lightweight.

**Phase 2 (optional): local model adapter.** Define a narrow reasoning-provider
contract only when a concrete summarization/research task needs language reasoning.
A local model can run on user-controlled hardware if memory and latency are suitable.
Do not assume GitHub-hosted runners can run a useful LLM for free. Deterministic
checks remain authoritative and validate all model outputs.

**Phase 3 (only if explicitly approved): remote model adapter.** Hosted inference is
opt-in, disabled by default, with budget caps, redacted inputs, structured outputs,
and a deterministic fallback. No paid provider is configured by this foundation.

## Operational guarantees

- Human review remains required for any future trade decision.
- No broker connection or order placement is implemented.
- No auto-merge or privileged autonomous repository writes are part of this runtime.
- Handoffs have parent task IDs and the orchestrator enforces a maximum task budget.
- Agent results are immutable records; no shared mutable state is passed between agents.
- This initial runtime is modular but executes sequentially in one process. Separate
  worker processes, queues, persistent memory, and dashboards are later decisions,
  not claims about the current implementation.

## Extending the team

Implement the Agent protocol, assign a unique name and one or more unique supported
kinds, and register the instance. Return follow-up AgentTask objects from handle() to
hand work to another registered agent. Add isolated tests for success, missing inputs,
malformed evidence, and refusal paths.
