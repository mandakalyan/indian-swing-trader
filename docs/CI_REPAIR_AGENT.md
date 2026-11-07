# AI-assisted CI repair

The CI repair job is a guarded, proposal-only fallback for failures on trusted
pushes to `development`.

## Flow

1. The normal CI jobs run Ruff lint/format checks, the Python 3.11–3.13 test
   matrix, and the wheel/source build.
2. If any required job fails on a direct push to `development`, the repair job
   downloads the failed job logs.
3. It first runs deterministic `ruff check --fix` and `ruff format` repairs.
4. If validation still fails, it asks the configured OpenAI model for a minimal
   unified diff using the Responses API structured-output format.
5. The patch is restricted to `src/`, `tests/`, `docs/`, `pyproject.toml`,
   and `README.md`; file deletions, renames, workflow edits, and patches over
   300 lines are rejected.
6. Ruff, pytest, and the package build must all pass before a draft PR is opened
   against `development`.

The agent never merges, never writes to `main`, and never runs with write
permissions on pull-request code. A person must review and merge any proposal.

## Required repository configuration

Add this Actions secret:

- `OPENAI_API_KEY`: an OpenAI API key with API access and an appropriate
  project spending limit.

Optional Actions variable:

- `OPENAI_MODEL`: model ID to use. Defaults to `gpt-4.1-mini`; choose a model
  available to the API project and supporting Responses structured outputs.

The repair job uses the repository's `GITHUB_TOKEN` with job-scoped
`actions: read`, `contents: write`, and `pull-requests: write` permissions.
The repository's Actions setting must allow the workflow token to create pull
requests. No PAT is required.

## Boundaries

- It only repairs failures from direct pushes to `development`; PR CI remains
  read-only to avoid exposing write-capable credentials to untrusted code.
- The model sees CI logs as untrusted input and is instructed not to follow
  instructions embedded in them.
- The agent cannot modify GitHub workflow files or security permissions.
- Tests are never deleted or weakened. If the failure cannot be repaired
  safely, the agent declines and leaves the original CI failure visible.
- Every generated change is a draft PR for human review. There is no retry loop
  and no automatic merge.

This is an initial guarded implementation. Trading logic, market-data parsers,
and risk rules still require domain-owner review even if the automated checks
pass.
