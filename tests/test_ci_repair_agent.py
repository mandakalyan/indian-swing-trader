"""Unit tests for CI repair patch safety boundaries."""

from types import SimpleNamespace

import pytest

import scripts.ci_repair_agent as agent


@pytest.mark.parametrize(
    "path",
    [
        "src/indian_swing_trader/module.py",
        "docs/architecture.md",
        "pyproject.toml",
        "README.md",
    ],
)
def test_safe_path_accepts_allowlisted_files(path):
    assert agent.safe_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "../.github/workflows/ci.yml",
        "src/../../.github/workflows/ci.yml",
        "/tmp/evil.py",
        r"src\\..\\secret.py",
        "tests/test_module.py",
        ".github/workflows/ci.yml",
        "scripts/ci_repair_agent.py",
    ],
)
def test_safe_path_rejects_untrusted_locations(path):
    assert not agent.safe_path(path)


def valid_patch(path="src/indian_swing_trader/module.py"):
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-value = 0\n"
        "+value = 1\n"
    )


def test_validate_accepts_small_patch(monkeypatch):
    monkeypatch.setattr(agent, "cmd", lambda *a, **k: SimpleNamespace(returncode=0))
    assert agent.validate(valid_patch()) == ["src/indian_swing_trader/module.py"]


@pytest.mark.parametrize(
    "marker",
    [
        "deleted file mode 100644\n",
        "new file mode 100644\n",
        "GIT binary patch\n",
        "rename from old.py\n",
    ],
)
def test_validate_rejects_destructive_patch_metadata(monkeypatch, marker):
    monkeypatch.setattr(agent, "cmd", lambda *a, **k: SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError):
        agent.validate(valid_patch() + marker)


def test_validate_rejects_unsafe_path(monkeypatch):
    monkeypatch.setattr(agent, "cmd", lambda *a, **k: SimpleNamespace(returncode=0))
    with pytest.raises(RuntimeError):
        agent.validate(valid_patch("../.github/workflows/ci.yml"))


def test_validate_rejects_header_path_mismatch(monkeypatch):
    monkeypatch.setattr(agent, "cmd", lambda *a, **k: SimpleNamespace(returncode=0))
    patch = (
        valid_patch()
        .replace(
            "--- a/src/indian_swing_trader/module.py",
            "--- a/.github/workflows/ci.yml",
        )
        .replace(
            "+++ b/src/indian_swing_trader/module.py",
            "+++ b/.github/workflows/ci.yml",
        )
    )
    with pytest.raises(RuntimeError, match="headers do not match"):
        agent.validate(patch)


def test_validate_rejects_patch_that_does_not_apply(monkeypatch):
    monkeypatch.setattr(agent, "cmd", lambda *a, **k: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="does not apply"):
        agent.validate(valid_patch())
