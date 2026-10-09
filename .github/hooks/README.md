# Hooks

Hooks are intentionally not enabled by default because VS Code hook behavior depends on the selected agent harness (Local, Copilot Agent Host, Codex, Claude, etc.).

`audit.json.example` demonstrates the VS Code Local-hook format. Rename it to `audit.json` only after confirming that your selected harness supports the same hook format and reviewing the script it executes.

Recommended first hook: audit tool usage rather than auto-running broad formatters or security-sensitive commands.
