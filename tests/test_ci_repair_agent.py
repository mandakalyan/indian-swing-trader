"""Safety tests for the guarded CI repair agent."""

import pytest

from scripts.ci_repair_agent import _safe_patch_path, validate_patch


def _diff(path: str, body: str = "+value = 1") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        "-value = 0\n"
        f"{body}\n"
    )


@pytest.mark.parametrize(
    "path",
    [
        "src/package/module.py",
        "tests/test_module.py",
        "docs/guide.md",
        "pyproject.toml",
    ],
)
def test_safe_patch_path_accepts_allowlisted_paths(path: str) -> None:
    assert _safe_patch_path(path)


@pytest.mark.parametrize(
    "path",
    [
        "../.github/workflows/ci.yml",
        "src/../../.github/workflows/ci.yml",
        "/tmp/evil.py",
        r"src\\..\\secret.py",
        "scripts/ci_repair_agent.py",
        ".github/workflows/ci.yml",
    ],
)
def test_safe_patch_path_rejects_traversal_and_unapproved_paths(path: str) -> None:
    assert not _safe_patch_path(path)


def test_validate_patch_accepts_small_safe_diff() -> None:
    validate_patch(_diff("src/package/module.py"))


def test_validate_patch_rejects_test_assertion_removal() -> None:
    patch = _diff("tests/test_module.py", "-assert result == expected")
    with pytest.raises(RuntimeError, match="removes a test"):
        validate_patch(patch)


def test_validate_patch_rejects_file_deletion() -> None:
    patch = _diff("src/package/module.py") + "deleted file mode 100644\n"
    with pytest.raises(RuntimeError, match="creations, deletions"):
        validate_patch(patch)


def test_validate_patch_rejects_path_traversal() -> None:
    with pytest.raises(RuntimeError, match="unsafe or outside"):
        validate_patch(_diff("../.github/workflows/ci.yml"))


def test_validate_patch_rejects_too_many_files() -> None:
    patch = "".join(
        _diff(f"src/package/module_{index}.py") for index in range(6)
    )
    with pytest.raises(RuntimeError, match="more than 5 files"):
        validate_patch(patch)
