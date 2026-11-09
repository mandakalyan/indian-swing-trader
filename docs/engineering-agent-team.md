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

## Activation and validation

GitHub evaluates a `pull_request_target` workflow from the PR's base branch.
Because this workflow is introduced by PR #7 targeting `development`, it
cannot run on PR #7 itself; it becomes active for subsequent PRs after it lands
in `development`. GitHub exposes `workflow_dispatch` only when the workflow
file is present on the repository's default branch (`main`). Until those
conditions are met, the privileged orchestration can be validated with the
static boundary checks and mocked end-to-end tests, but not with a live
write-capable Actions run. Do not treat the mocked test as proof of live token
permissions or runner integration.

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

- The repair workflow is triggered by `pull_request_target` for opened,
  synchronized, or reopened PRs targeting `development`; a manual
  `workflow_dispatch` path is also provided.
- The privileged job checks out only the trusted `development` branch with
  checkout credentials disabled. It never checks out the candidate PR branch.
- The job accepts only open, same-repository PRs targeting `development`,
  rejects protected head branches, and revalidates the PR head SHA before
  creating a repair proposal.
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
