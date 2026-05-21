"""Minimal MCP-style deployment tool used behind the Rust stdio broker."""

from __future__ import annotations

import json
import sys


def handle_tool_call(request: dict) -> dict:
    params = request.get("params") or {}
    arguments = params.get("arguments") or {}
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": {
            "status": "deployed",
            "target": params.get("name"),
            "artifact": arguments.get("artifact"),
            "dry_run": arguments.get("dry_run"),
        },
    }


def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if request.get("method") == "tools/call":
                response = handle_tool_call(request)
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {"status": "ignored"},
                }
            sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
            sys.stdout.flush()
        except Exception as exc:
            sys.stdout.write(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32099, "message": str(exc)},
                    },
                    sort_keys=True,
                )
                + "\n"
            )
            sys.stdout.flush()


if __name__ == "__main__":
    main()
