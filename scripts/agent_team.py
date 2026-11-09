"""Zero-API-cost, role-based CI repair team.

The roles are deterministic Python agents, not LLMs. They inspect CI evidence,
apply only safe Ruff autofixes, review the resulting diff, and open draft PRs.
No candidate code is executed in this privileged workflow.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from pathlib import PurePosixPath

API = "https://api.github.com"
ALLOWED_PREFIXES = ("src/", "docs/")
ALLOWED_FILES = {"README.md", "pyproject.toml"}
MAX_PATCH_BYTES = 20_000
MAX_FILES = 5


def run(args: list[str], *, check: bool = False, env: dict[str, str] | None = None):
    result = subprocess.run(args, text=True, capture_output=True, env=env, timeout=120)
    if check and result.returncode:
        raise RuntimeError(f"{args[0]} failed: {(result.stderr or result.stdout)[-2000:]}")
    return result


def github(url: str, token: str, method: str = "GET", payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
    return json.loads(raw) if raw else {}


def redact_logs(text: str) -> str:
    """Redact common credentials; fail closed on suspicious leftovers."""
    text = re.sub(
        r"-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----",
        "[REDACTED PRIVATE KEY]",
        text,
        flags=re.S,
    )
    patterns = [
        (r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+", r"\1[REDACTED]"),
        (r"(?i)(authorization\s*[:=]\s*)[^\r\n]+", r"\1[REDACTED]"),
        (
            r"(?i)((?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|"
            r"password|passwd|secret)\s*[:=]\s*)[^\s,;]+",
            r"\1[REDACTED]",
        ),
        (r"(?i)(https?://)[^/@\s:]+:[^/@\s]+@", r"\1[REDACTED]@"),
        (r"\bgh[pousr]_[A-Za-z0-9]{20,}\b", "[REDACTED GITHUB TOKEN]"),
        (r"\bAKIA[0-9A-Z]{16}\b", "[REDACTED AWS KEY]"),
        (r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b", "[REDACTED SLACK TOKEN]"),
    ]
    for pattern, replacement in patterns:
        text = re.sub(pattern, replacement, text)
    lines = []
    for line in text.splitlines():
        if re.search(r"(?i)(cookie\s*[:=]|set-cookie\s*:|x-api-key\s*:|printenv)", line):
            continue
        lines.append(line)
    cleaned = "\n".join(lines)
    residual = re.search(
        r"(?i)(-----BEGIN .*PRIVATE KEY-----|bearer\s+[A-Za-z0-9._~+/=-]{16,}|"
        r"(?:password|client_secret|api_key)\s*[:=]\s*(?!\[REDACTED\])[^\s]{8,})",
        cleaned,
    )
    return "" if residual else cleaned[:20_000]


@dataclass
class Finding:
    role: str
    status: str
    detail: str


class TriageAgent:
    """Classifies failures from job names and sanitized log text."""

    def run(self, failed_jobs: list[dict], logs: str) -> Finding:
        names = " ".join(str(job.get("name", "")) for job in failed_jobs).lower()
        body = logs.lower()
        if "lint" in names or "ruff" in body or "format" in body:
            category = "lint_or_format"
        elif "test" in names or "pytest" in body or "assertionerror" in body:
            category = "tests"
        elif "build" in names or "build" in body or "packaging" in body:
            category = "build"
        elif "permission" in body or "denied" in body or "security" in body:
            category = "permissions_or_security"
        else:
            category = "unknown"
        return Finding("triage", "classified", f"Failure category: {category}")


class SecurityAgent:
    """Enforces log privacy and prevents edits to privileged or trading logic."""

    def run(self, logs: str, paths: list[str]) -> Finding:
        if not logs:
            return Finding("security", "blocked", "Logs failed the secret-scrubbing check.")
        unsafe = [path for path in paths if not safe_path(path)]
        if unsafe:
            return Finding("security", "blocked", f"Unsafe changed paths: {unsafe}")
        return Finding("security", "passed", "No disallowed paths or unsanitized log indicators.")


class RepairAgent:
    """Performs deterministic Ruff-only repairs; never generates arbitrary code."""

    def run(self) -> Finding:
        # Ruff parses source; it does not import or execute candidate project code.
        check = run(["ruff", "check", "--fix", "src"], check=False)
        fmt = run(["ruff", "format", "src"], check=False)
        if check.returncode not in (0, 1) or fmt.returncode:
            return Finding(
                "repair",
                "declined",
                "Ruff could not safely complete deterministic fixes.",
            )
        return Finding("repair", "completed", "Applied Ruff autofixes and formatting to src/ only.")


class TestAgent:
    """Uses CI's read-only results as test evidence; does not execute PR code here."""

    def run(self, findings: list[dict]) -> Finding:
        failed = [
            job.get("name", "unnamed job") for job in findings if job.get("conclusion") == "failure"
        ]
        return Finding(
            "testing",
            "awaiting_pr_ci",
            "The repair PR must rerun CI; original failed jobs: " + ", ".join(failed),
        )


class ReviewAgent:
    """Reviews patch scope and rejects structural, binary or oversized changes."""

    def run(self) -> tuple[Finding, list[str]]:
        # Inspect metadata separately from the patch: a safe filename alone does
        # not make an add/delete/rename or binary replacement safe.
        status = run(["git", "diff", "--name-status", "--no-renames", "HEAD"])
        if status.returncode:
            return Finding("review", "blocked", "Could not inspect changed-file status."), []
        entries = [line.split("\t", 1) for line in status.stdout.splitlines() if line]
        if not entries:
            return Finding("review", "no_change", "No repair changes were produced."), []
        if any(len(item) != 2 or item[0] != "M" for item in entries):
            return (
                Finding("review", "blocked", "Only modifications to existing files are permitted."),
                [item[-1] for item in entries if item],
            )
        names = [item[1] for item in entries]
        if len(names) > MAX_FILES or any(not safe_path(name) for name in names):
            return (
                Finding("review", "blocked", "Repair exceeds file-count or path allowlist limits."),
                names,
            )
        if any(not name.startswith("src/") or not name.endswith(".py") for name in names):
            return (
                Finding(
                    "review",
                    "blocked",
                    "Deterministic Ruff repairs may modify only Python files under src/.",
                ),
                names,
            )

        diff = run(["git", "diff", "--no-ext-diff", "--no-color", "HEAD"])
        if diff.returncode:
            return Finding("review", "blocked", "Could not inspect resulting diff."), names
        raw = diff.stdout
        if len(raw.encode()) > MAX_PATCH_BYTES:
            return Finding("review", "blocked", "Repair exceeds patch-size limit."), names
        if "Binary files " in raw or "GIT binary patch" in raw:
            return Finding("review", "blocked", "Binary changes are not permitted."), names
        whitespace = run(["git", "diff", "--check", "HEAD"])
        if whitespace.returncode:
            return Finding("review", "blocked", "Patch contains whitespace errors."), names
        return Finding("review", "passed", f"Reviewed {len(names)} modified source file(s)."), names


def safe_path(path: str) -> bool:
    if not path or path.startswith("/") or "\\" in path or "\x00" in path:
        return False
    pure = PurePosixPath(path)
    return (
        pure.as_posix() == path
        and not pure.is_absolute()
        and not any(part in {"", ".", ".."} for part in path.split("/"))
        and (path.startswith(ALLOWED_PREFIXES) or path in ALLOWED_FILES)
    )


def get_event() -> dict:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as stream:
        return json.load(stream)


def valid_target_pr(
    pr: dict,
    repo: str,
    *,
    number: int | None = None,
    sha: str | None = None,
    branch: str | None = None,
) -> bool:
    """Accept only an open, same-repository PR targeting development."""
    head = pr.get("head") or {}
    base = pr.get("base") or {}
    head_repo = head.get("repo") or {}
    base_repo = base.get("repo") or {}
    current_sha = head.get("sha", "")
    current_branch = head.get("ref", "")
    return (
        pr.get("state") == "open"
        and isinstance(pr.get("number"), int)
        and pr["number"] > 0
        and (number is None or pr["number"] == number)
        and base.get("ref") == "development"
        and base_repo.get("full_name") == repo
        and head_repo.get("full_name") == repo
        and bool(re.fullmatch(r"[0-9a-f]{40}", current_sha))
        and bool(current_branch)
        and current_branch not in {"main", "development"}
        and (sha is None or current_sha == sha)
        and (branch is None or current_branch == branch)
    )


def collect_failure(repo: str, run_id: int, token: str) -> tuple[list[dict], str]:
    jobs_url = f"{API}/repos/{repo}/actions/runs/{run_id}/jobs?per_page=100"
    jobs = github(jobs_url, token).get("jobs", [])
    failed = [job for job in jobs if job.get("conclusion") == "failure"]
    chunks = []
    for job in failed:
        try:
            request = urllib.request.Request(
                f"{API}/repos/{repo}/actions/jobs/{job['id']}/logs",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                },
            )
            with urllib.request.urlopen(request, timeout=60) as response:
                archive = response.read()
            import io
            import zipfile

            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                raw = "\n".join(
                    bundle.read(name).decode("utf-8", errors="replace")
                    for name in bundle.namelist()
                    if name.endswith(".txt")
                )
        except Exception as exc:  # noqa: BLE001
            raw = f"Log retrieval failed ({type(exc).__name__})."
        safe = redact_logs(raw)
        if not safe:
            return failed, ""
        chunks.append(f"FAILED JOB: {job.get('name')}\n{safe}")
    return failed, "\n\n".join(chunks)[:20_000]


def write_summary(findings: list[Finding]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    content = "## Multi-agent CI repair report\n\n"
    content += "| Agent | Result | Detail |\n|---|---|---|\n"
    for finding in findings:
        detail = finding.detail.replace("|", "\\|").replace("\n", " ")
        content += f"| {finding.role} | {finding.status} | {detail} |\n"
    if path:
        with open(path, "a", encoding="utf-8") as stream:
            stream.write(content)
    print(content)


def open_draft_pr(
    repo: str,
    pr_number: int,
    base_branch: str,
    run_id: int,
    token: str,
    paths: list[str],
    findings: list[Finding],
) -> str:
    branch = f"agent-team/repair-pr-{pr_number}-run-{run_id}"
    run(["git", "checkout", "-b", branch], check=True)
    run(["git", "add", "--", *paths], check=True)
    if not run(["git", "diff", "--cached", "--quiet"]).returncode:
        return ""
    run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    run(
        ["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    commit_message = f"chore: propose deterministic CI repair for PR #{pr_number}"
    run(["git", "commit", "-m", commit_message], check=True)
    import base64

    basic = base64.b64encode(f"x-access-token:{token}".encode()).decode()
    run(
        ["git", "push", "--set-upstream", "origin", branch],
        check=True,
        env={
            **os.environ,
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": f"AUTHORIZATION: basic {basic}",
        },
    )
    diagnosis = "\n".join(f"- **{f.role}:** {f.detail}" for f in findings)
    result = github(
        f"{API}/repos/{repo}/pulls",
        token,
        "POST",
        {
            "title": f"Agent-team repair proposal for PR #{pr_number}",
            "head": branch,
            "base": base_branch,
            "draft": True,
            "maintainer_can_modify": True,
            "body": (
                "## Deterministic multi-agent repair proposal\n\n"
                f"Original PR: #{pr_number}\n\n"
                f"CI run: https://github.com/{repo}/actions/runs/{run_id}\n\n"
                f"### Agent report\n{diagnosis}\n\n"
                "No external model/API was used. CI must rerun on this draft PR. "
                "Human review is required; no auto-merge."
            ),
        },
    )
    return result.get("html_url", "")


def main() -> int:
    event = get_event()
    repo = os.environ["GITHUB_REPOSITORY"]
    token = os.environ["GH_TOKEN"]
    pr = event.get("pull_request", {})
    if event.get("workflow_dispatch") or not pr:
        inputs = event.get("inputs", {})
        raw_number = str(inputs.get("pr_number", "")).strip()
        if not raw_number.isdigit() or int(raw_number) < 1:
            print("A valid workflow_dispatch pr_number is required.")
            return 0
        pr = github(f"{API}/repos/{repo}/pulls/{int(raw_number)}", token)
    if not valid_target_pr(pr, repo):
        print("Skipping closed, fork, or non-development PR.")
        return 0
    number = pr["number"]
    sha = pr["head"]["sha"]
    branch = pr["head"]["ref"]

    failed_run = None
    for _ in range(80):
        runs = github(
            f"{API}/repos/{repo}/actions/runs?head_sha={sha}&event=pull_request&per_page=30", token
        ).get("workflow_runs", [])
        candidates = [
            item
            for item in runs
            if item.get("name") == "CI"
            and any(p.get("number") == number for p in item.get("pull_requests", []))
        ]
        if candidates and candidates[0].get("status") == "completed":
            if candidates[0].get("conclusion") == "failure":
                failed_run = candidates[0]
            else:
                print("Read-only CI passed; no repair required.")
            break
        time.sleep(15)
    if not failed_run:
        return 0

    current_pr = github(f"{API}/repos/{repo}/pulls/{number}", token)
    if not valid_target_pr(current_pr, repo, number=number, sha=sha, branch=branch):
        print("PR was closed, retargeted, or updated while CI was running; no repair proposed.")
        return 0

    failed_jobs, logs = collect_failure(repo, int(failed_run["id"]), token)
    findings = [TriageAgent().run(failed_jobs, logs)]
    security = SecurityAgent().run(logs, [])
    findings.append(security)
    if security.status != "passed":
        write_summary(findings)
        return 0

    # Fetch the candidate revision as Git data only. No candidate code is executed.
    run(["git", "fetch", "--no-tags", "origin", sha], check=True)
    run(["git", "checkout", "--detach", "FETCH_HEAD"], check=True)
    findings.append(RepairAgent().run())
    # Verify Ruff checks after autofix; do not run pytest/build in this privileged context.
    lint = run(["ruff", "check", "src"], check=False)
    fmt = run(["ruff", "format", "--check", "src"], check=False)
    if lint.returncode or fmt.returncode:
        findings.append(
            Finding("testing", "declined", "Ruff validation still fails; no PR created.")
        )
        write_summary(findings)
        return 0

    review, paths = ReviewAgent().run()
    findings.append(review)
    if review.status != "passed":
        write_summary(findings)
        return 0
    path_review = SecurityAgent().run(logs, paths)
    findings.append(Finding("security_path_review", path_review.status, path_review.detail))
    if path_review.status != "passed":
        write_summary(findings)
        return 0
    findings.append(TestAgent().run(failed_jobs))
    latest_pr = github(f"{API}/repos/{repo}/pulls/{number}", token)
    if not valid_target_pr(latest_pr, repo, number=number, sha=sha, branch=branch):
        findings.append(
            Finding(
                "orchestrator",
                "stale_pr",
                "PR changed or closed during repair; no draft PR was created.",
            )
        )
        write_summary(findings)
        return 0
    url = open_draft_pr(repo, number, branch, int(failed_run["id"]), token, paths, findings)
    findings.append(
        Finding(
            "orchestrator",
            "draft_pr_created" if url else "no_change",
            url or "No changes remained to propose.",
        )
    )
    write_summary(findings)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
