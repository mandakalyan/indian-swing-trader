"""Tests for the zero-cost CI repair agent team."""

import pytest

from scripts.agent_team import (
    RepairAgent,
    ReviewAgent,
    SecurityAgent,
    TriageAgent,
    redact_logs,
    safe_path,
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
        stdout = ".github/workflows/ci.yml\n"

    monkeypatch.setattr("scripts.agent_team.run", lambda *args, **kwargs: Result())
    finding, paths = ReviewAgent().run()
    assert finding.status == "blocked"
    assert paths == [".github/workflows/ci.yml"]
