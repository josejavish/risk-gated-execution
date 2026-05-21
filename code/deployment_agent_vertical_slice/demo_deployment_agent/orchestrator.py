"""End-to-end deployment demo through RiskGate and the Rust stdio broker."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from .evidence_provider import collect_signed_evidence
from .riskgate_service import DeploymentRiskGate, default_deploy_intent


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT.parent
BROKER_DIR = LAB / "mcp_stdio_broker"
BROKER_BIN = Path(
    os.environ.get(
        "RGE_BROKER_BIN",
        str(BROKER_DIR / "target" / "release" / "mcp_stdio_broker"),
    )
)
POLICY_PATH = ROOT / "out" / "deployment-agent_riskgate.json"


def build_mcp_payload(intent: dict[str, Any], receipt: dict[str, Any] | None) -> dict[str, Any]:
    params: dict[str, Any] = {
        "name": intent["action_type"],
        "arguments": intent["arguments"],
    }
    if receipt:
        params["_receipt"] = receipt
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": params,
    }


def run_through_broker(payload: dict[str, Any], policy_path: Path = POLICY_PATH) -> tuple[dict[str, Any], str]:
    if not BROKER_BIN.exists():
        raise RuntimeError(f"Broker binary not found: {BROKER_BIN}. Run `make build-broker` first.")

    env = dict(os.environ)
    env["RGE_BROKER_POLICY_PATH"] = str(policy_path)
    proc = subprocess.Popen(
        [
            str(BROKER_BIN),
            "python3",
            str(ROOT / "demo_deployment_agent" / "deployment_tool.py"),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None
    proc.stdin.write(json.dumps(payload, sort_keys=True) + "\n")
    proc.stdin.flush()
    first_line = proc.stdout.readline().strip() or "{}"
    proc.terminate()
    try:
        _, stderr = proc.communicate(timeout=2)
    except subprocess.TimeoutExpired:
        proc.kill()
        _, stderr = proc.communicate(timeout=2)
    return json.loads(first_line), stderr


def run_demo(evidence_profile: str = "healthy") -> int:
    gate = DeploymentRiskGate()
    gate.write_broker_policy(POLICY_PATH)

    print("=== Agent Framework Initialization ===")
    print("Exporting RiskGate to Orchestrator (OpenAI Tool Calling Format):")
    print(json.dumps([gate.get_openai_tool_schema()], indent=2))
    print("\n=== Risk-Gated Deployment Demo (Middleware Flow) ===")

    intent = default_deploy_intent()
    signed_evidence = collect_signed_evidence(evidence_profile)
    decision = gate.evaluate(intent, signed_evidence)

    print(f"intent: {intent['action_type']} -> {intent['target']} {intent['arguments']['artifact']}")
    print(f"evidence_profile: {evidence_profile}")

    if not decision.allowed:
        print(f"riskgate: BLOCK ({decision.reason})")
        return 2

    print(f"riskgate: ALLOW ({decision.reason})")
    payload = build_mcp_payload(intent, decision.receipt)
    response, broker_logs = run_through_broker(payload)
    print(f"broker_response: {json.dumps(response, sort_keys=True)}")
    if broker_logs:
        print("broker_logs:")
        print(broker_logs.strip())
    return 0 if "result" in response else 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the risk-gated deployment demo.")
    parser.add_argument("--evidence-profile", default="healthy")
    args = parser.parse_args()
    raise SystemExit(run_demo(args.evidence_profile))


if __name__ == "__main__":
    main()
