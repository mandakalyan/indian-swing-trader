# GitHub multi-agent engineering team

## Architecture

The first release is a deterministic, zero-external-API-cost agent team. It uses
specialised Python roles coordinated by a small orchestrator:

1. **Triage agent** classifies failed CI jobs from their names and sanitized logs.
2. **Security agent** fails closed when log sanitization is uncertain and blocks
   changes outside the permitted source/documentation scope.
3. **Repair agent** runs Ruff autofix and formatting on `src/` only. It does
   not generate arbitrary code or execute repository code.
4. **Testing agent** records the original CI failures and requires the repair
   draft PR to pass the normal read-only CI workflow.
5. **Review agent** checks changed paths, patch size, file count and destructive
   diff metadata before a draft PR can be opened.
6. **Orchestrator** waits for the ordinary `CI` workflow to finish, coordinates
   the roles, and opens a draft PR only when a bounded repair exists.

## Model and cost strategy

**No LLM is called in release 1.** GitHub Actions performs deterministic
classification, Ruff autofixes and validation. This avoids OpenAI API charges,
does not depend on Copilot or a retired inference endpoint, and keeps the
system usable with a zero-rupee model budget.

The only platform usage is GitHub Actions. The repository is public, so GitHub's
current public-repository Actions policy generally makes standard hosted-runner
minutes free; concurrency and abuse limits still apply. Re-check GitHub's
current plan and usage pages before relying on that for private repositories.

A future optional model adapter may be added behind an explicit opt-in and a
hard spend limit. It must never be enabled by default. Do not treat Copilot
subscription access as a general-purpose API key. Do not add model credentials
to this workflow.

## Security boundaries

- The privileged workflow uses `pull_request_target`, but checks out only the
  trusted `development` branch containing the automation.
- Fork PRs are skipped.
- The candidate commit is fetched as Git data. Candidate code is not run.
- Ruff is used as a parser/formatter; pytest, build hooks, package imports and
  candidate scripts are not executed in the privileged job.
- Logs are sanitized locally and are not sent to an external model.
- The repair allowlist is `src/`, `docs/`, `README.md` and
  `pyproject.toml`; workflow, script, test, secret and trading-risk paths are
  excluded.
- A repair must pass the ordinary CI workflow on its own draft PR.
- No auto-merge, no direct pushes to `development` or `main`, and no live
  trading actions.

## Known limitations

This version can automatically repair only deterministic Ruff lint/format
issues under `src/`. It can classify test, build, dependency and permission
failures, but it deliberately does not invent code fixes for them. Those cases
are reported in the workflow summary for a human to investigate.

The log scrubber covers common credential formats, not every possible secret.
Logs are never forwarded to a model in this version. Keep privileged workflow
permissions minimal and rotate any credential that may have appeared in logs.

## Future roadmap

- Add static security analysis agents (dependency audit, secret scan, unsafe
  configuration checks) with pinned tools and bounded permissions.
- Add deterministic repair rules for known dependency and packaging failures.
- Consider an optional local model only after measuring runner time and memory.
- Consider a paid external model only with explicit opt-in, usage caps and
  human-reviewed draft PRs.
