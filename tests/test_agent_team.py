"""Tests for the zero-cost CI repair agent team."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.agent_team as agent_team

from scripts.agent_team import (
    RepairAgent,
    ReviewAgent,
    SecurityAgent,
    TriageAgent,
    redact_logs,
    safe_path,
    valid_target_pr,
)


@pytest.mark.parametrize(
    "path",
    [
        "src/indian_swing_trader/core.py",
        "docs/architecture.md",
        "README.md",
        "pyproject.toml",
    ],
)
def test_safe_path_allows_scoped_paths(path):
    assert safe_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "../.github/workflows/ci.yml",
        ".github/workflows/ci.yml",
        "scripts/agent_team.py",
        "tests/test_agent_team.py",
        "/tmp/file.py",
        r"src\\..\\secrets.py",
    ],
)
def test_safe_path_rejects_privileged_or_traversal_paths(path):
    assert not safe_path(path)


def test_redact_logs_masks_common_tokens():
    logs = (
        "Authorization: Bearer abcdefghijklmnop\n"
        "token=ghp_abcdefghijklmnopqrstuvwxyz123456\n"
        "https://user:password@example.com/private"
    )
    cleaned = redact_logs(logs)
    assert "abcdefghijklmnop" not in cleaned
    assert "ghp_abcdefghijklmnopqrstuvwxyz123456" not in cleaned
    assert "user:password" not in cleaned


def test_redact_logs_masks_api_key_assignment():
    cleaned = redact_logs("api_key=unusuallylongsecretvalue")
    assert "unusuallylongsecretvalue" not in cleaned
    assert "[REDACTED]" in cleaned


def test_triage_agent_classifies_lint_failure():
    finding = TriageAgent().run(
        [{"name": "Lint and formatting"}],
        "ruff format --check failed",
    )
    assert finding.status == "classified"
    assert finding.detail == "Failure category: lint_or_format"


def test_security_agent_blocks_unsanitised_logs():
    finding = SecurityAgent().run("", [])
    assert finding.status == "blocked"


def test_security_agent_blocks_out_of_scope_paths():
    finding = SecurityAgent().run("safe logs", [".github/workflows/ci.yml"])
    assert finding.status == "blocked"


def test_repair_agent_uses_only_source_tree(monkeypatch):
    calls = []

    def fake_run(command, check=False, env=None):
        calls.append(command)

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr("scripts.agent_team.run", fake_run)
    finding = RepairAgent().run()
    assert finding.status == "completed"
    assert calls == [
        ["ruff", "check", "--fix", "src"],
        ["ruff", "format", "src"],
    ]


def test_review_agent_rejects_out_of_scope_changes(monkeypatch):
    class Result:
        returncode = 0
        stdout = "M\t.github/workflows/ci.yml\n"

    monkeypatch.setattr("scripts.agent_team.run", lambda *args, **kwargs: Result())
    finding, paths = ReviewAgent().run()
    assert finding.status == "blocked"
    assert paths == [".github/workflows/ci.yml"]


@pytest.mark.parametrize(
    "status_line",
    [
        "A\tsrc/indian_swing_trader/new_module.py",
        "D\tsrc/indian_swing_trader/old_module.py",
        "R100\tsrc/indian_swing_trader/old.py\tsrc/indian_swing_trader/new.py",
    ],
)
def test_review_agent_rejects_structural_changes(monkeypatch, status_line):
    class Result:
        returncode = 0
        stdout = status_line

    monkeypatch.setattr("scripts.agent_team.run", lambda *args, **kwargs: Result())
    finding, _ = ReviewAgent().run()
    assert finding.status == "blocked"
    assert "Only modifications" in finding.detail


def test_review_agent_rejects_binary_diff(monkeypatch):
    class Result:
        returncode = 0

        def __init__(self, stdout):
            self.stdout = stdout

    calls = 0

    def fake_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return Result("M\tsrc/indian_swing_trader/module.py\n")
        if calls == 2:
            return Result("Binary files differ")
        return Result("")

    monkeypatch.setattr("scripts.agent_team.run", fake_run)
    finding, _ = ReviewAgent().run()
    assert finding.status == "blocked"
    assert "Binary" in finding.detail


REPOSITORY = "mandakalyan/indian-swing-trader"
TARGET_SHA = "a" * 40


def make_target_pr(
    *,
    state="open",
    base_ref="development",
    base_repo=REPOSITORY,
    head_repo=REPOSITORY,
    head_sha=TARGET_SHA,
    head_branch="feature/ci-test",
):
    return {
        "number": 7,
        "state": state,
        "base": {"ref": base_ref, "repo": {"full_name": base_repo}},
        "head": {
            "ref": head_branch,
            "sha": head_sha,
            "repo": {"full_name": head_repo},
        },
    }


def test_valid_target_pr_accepts_open_same_repo_development_pr():
    assert valid_target_pr(
        make_target_pr(),
        REPOSITORY,
        number=7,
        sha=TARGET_SHA,
        branch="feature/ci-test",
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"state": "closed"},
        {"base_ref": "main"},
        {"base_repo": "another/repository"},
        {"head_repo": "fork/indian-swing-trader"},
        {"head_sha": "b" * 40},
        {"head_branch": "renamed/branch"},
    ],
)
def test_valid_target_pr_rejects_stale_or_untrusted_pr(changes):
    assert not valid_target_pr(
        make_target_pr(**changes),
        REPOSITORY,
        number=7,
        sha=TARGET_SHA,
        branch="feature/ci-test",
    )


def test_valid_target_pr_rejects_malformed_head_sha():
    assert not valid_target_pr(
        make_target_pr(head_sha="not-a-commit"),
        REPOSITORY,
    )


def test_privileged_workflow_uses_trusted_pull_request_target_boundary():
    workflow = Path(".github/workflows/ci-repair.yml").read_text(encoding="utf-8")
    assert "pull_request_target:" in workflow
    assert "types: [opened, synchronize, reopened]" in workflow
    assert "branches: [development]" in workflow
    assert "ref: development" in workflow
    assert "persist-credentials: false" in workflow
    assert "actions: read" in workflow
    assert "contents: write" in workflow
    assert "pull-requests: write" in workflow
    assert workflow.count("uses: actions/checkout@") == 1
    assert "ref: ${{ github.event.pull_request.head.sha }}" not in workflow
    assert "secrets." not in workflow


def test_main_runs_controlled_repair_flow_without_executing_candidate_code(
    monkeypatch, tmp_path
):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": make_target_pr()}),
        encoding="utf-8",
    )
    summary_path = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_path))
    monkeypatch.setattr(agent_team.time, "sleep", lambda *_: None)

    api_calls = []
    repair_pr_payloads = []

    def fake_github(url, token, method="GET", payload=None):
        api_calls.append((url, method))
        if "/actions/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "CI",
                        "status": "completed",
                        "conclusion": "failure",
                        "id": 123,
                        "pull_requests": [{"number": 7}],
                    }
                ]
            }
        if url.endswith("/pulls/7") and method == "GET":
            return make_target_pr()
        if url.endswith("/pulls") and method == "POST":
            repair_pr_payloads.append(payload)
            return {"html_url": "https://github.com/mandakalyan/indian-swing-trader/pull/99"}
        raise AssertionError(f"Unexpected GitHub API call: {method} {url}")

    commands = []

    def fake_run(args, *, check=False, env=None):
        commands.append(args)
        stdout = ""
        returncode = 0
        if args == ["git", "diff", "--name-status", "--no-renames", "HEAD"]:
            stdout = "M\\tsrc/indian_swing_trader/core.py\\n"
        elif args == ["git", "diff", "--no-ext-diff", "--no-color", "HEAD"]:
            stdout = (
                "diff --git a/src/indian_swing_trader/core.py "
                "b/src/indian_swing_trader/core.py\\n"
                "--- a/src/indian_swing_trader/core.py\\n"
                "+++ b/src/indian_swing_trader/core.py\\n"
                "@@ -1 +1 @@\\n-value = 0\\n+value = 1\\n"
            )
        elif args == ["git", "diff", "--cached", "--quiet"]:
            returncode = 1
        return SimpleNamespace(returncode=returncode, stdout=stdout, stderr="")

    monkeypatch.setattr(agent_team, "github", fake_github)
    monkeypatch.setattr(agent_team, "collect_failure", lambda *args: (
        [{"name": "Lint and formatting", "conclusion": "failure"}],
        "ruff check failed",
    ))
    monkeypatch.setattr(agent_team, "run", fake_run)

    assert agent_team.main() == 0
    assert len(repair_pr_payloads) == 1
    assert repair_pr_payloads[0]["draft"] is True
    assert repair_pr_payloads[0]["base"] == "feature/ci-test"
    assert any(command[:3] == ["git", "fetch", "--no-tags"] for command in commands)
    assert ["ruff", "check", "--fix", "src"] in commands
    assert ["ruff", "format", "src"] in commands
    assert not any(
        command and command[0] in {"pytest", "python", "pip"} for command in commands
    )
    assert summary_path.exists()
    assert "draft_pr_created" in summary_path.read_text(encoding="utf-8")
    assert len([call for call in api_calls if call[0].endswith("/pulls/7")]) == 2


def test_main_aborts_when_pr_head_changes_after_ci(monkeypatch, tmp_path):
    event_path = tmp_path / "event.json"
    event_path.write_text(
        json.dumps({"pull_request": make_target_pr()}),
        encoding="utf-8",
    )
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event_path))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPOSITORY)
    monkeypatch.setenv("GH_TOKEN", "test-token")
    monkeypatch.setattr(agent_team.time, "sleep", lambda *_: None)

    api_calls = []

    def fake_github(url, token, method="GET", payload=None):
        api_calls.append((url, method))
        if "/actions/runs?" in url:
            return {
                "workflow_runs": [
                    {
                        "name": "CI",
                        "status": "completed",
                        "conclusion": "failure",
                        "id": 123,
                        "pull_requests": [{"number": 7}],
                    }
                ]
            }
        if url.endswith("/pulls/7"):
            return make_target_pr(head_sha="b" * 40)
        raise AssertionError(f"Unexpected GitHub API call: {method} {url}")

    commands = []
    monkeypatch.setattr(agent_team, "github", fake_github)
    monkeypatch.setattr(agent_team, "run", lambda args, **kwargs: commands.append(args))

    assert agent_team.main() == 0
    assert commands == []
    assert not any(url.endswith("/pulls") and method == "POST" for url, method in api_calls)
