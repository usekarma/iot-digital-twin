"""Example VS Code Local-agent hook: record tool names without storing tool inputs."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    event = json.load(sys.stdin)
    tool_name = str(event.get("tool_name", "unknown"))
    log_path = Path(".agent-tool-audit.log")
    timestamp = datetime.now(UTC).isoformat()
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{timestamp} {tool_name}\n")


if __name__ == "__main__":
    main()
