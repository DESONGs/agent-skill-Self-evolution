from __future__ import annotations

import json
import sys


def main() -> int:
    payload = json.loads(sys.stdin.read() or "{}")
    summary = payload.get("task", "no-task")
    print(json.dumps({"summary": summary, "artifacts": []}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
