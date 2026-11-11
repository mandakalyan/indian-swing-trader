# CI repair workflow smoke test

This documentation-only pull request verifies that the trusted CI repair workflow is activated for pull requests targeting `development`.

No application code, trading logic, workflow configuration, or tests are changed. The expected outcome is that the ordinary CI passes and the privileged repair workflow exits without proposing a repair.
