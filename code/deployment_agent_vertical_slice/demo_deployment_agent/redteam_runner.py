"""Run reproducible attacks against the deployment vertical slice."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .crypto_utils import receipt_binding, risk_gate_keypair, sign_json_document, sign_receipt_hash
from .evidence_provider import collect_signed_evidence
from .orchestrator import POLICY_PATH, build_mcp_payload, run_through_broker
from .riskgate_service import DEFAULT_POLICY, DeploymentRiskGate, default_deploy_intent


ROOT = Path(__file__).resolve().parents[1]
ATTACKS_DIR = ROOT / "attacks"


def load_attack_specs() -> list[dict[str, Any]]:
    """Loads the deterministic JSON adversarial payloads used to validate the RiskGate's attack surface."""
    return [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(ATTACKS_DIR.glob("*.json"))
    ]


def manual_receipt(
    *,
    intent: dict[str, Any],
    evidence_digest: str,
    timestamp: int | None = None,
) -> dict[str, Any]:
    """Manually constructs a cryptographic receipt for Red Team adversarial testing, bypassing the standard RiskGate evaluation."""
    timestamp = int(time.time()) if timestamp is None else timestamp
    keypair = risk_gate_keypair()
    binding = receipt_binding(
        intent_id=intent["intent_id"],
        action_type=intent["action_type"],
        target=intent["target"],
        payload=intent["arguments"],
        evidence_digest=evidence_digest,
        timestamp=timestamp,
    )
    return {
        "intent_id": intent["intent_id"],
        "action_type": intent["action_type"],
        "target": intent["target"],
        "evidence_digest": evidence_digest,
        "timestamp": timestamp,
        "signature": sign_receipt_hash(binding, keypair),
    }


def apply_intent_patch(intent: dict[str, Any], patch: dict[str, Any] | None) -> dict[str, Any]:
    """Mutates a valid intent payload with adversarial data to simulate prompt injection or compromised logic."""
    if not patch:
        return intent
    updated = json.loads(json.dumps(intent))
    for key, value in patch.items():
        if key == "arguments":
            updated["arguments"].update(value)
        else:
            updated[key] = value
    return updated


def classify_broker_response(response: dict[str, Any]) -> str:
    """Parses the JSON-RPC response from the Rust broker to determine if the execution was allowed, blocked, or suspended."""
    if "result" in response:
        return "ALLOW"
    message = (response.get("error") or {}).get("message", "")
    if "Suspended" in message:
        return "BROKER_SUSPEND"
    return "BROKER_BLOCK"


def run_attack(spec: dict[str, Any]) -> dict[str, Any]:
    """Executes a single Red Team attack scenario, verifying the end-to-end cryptographic and IPC enforcement."""
    policy = dict(DEFAULT_POLICY)
    policy.update(spec.get("policy_patch", {}))
    gate = DeploymentRiskGate(policy)
    gate.write_broker_policy(POLICY_PATH)

    intent = apply_intent_patch(default_deploy_intent(), spec.get("intent_patch"))
    signed_evidence = collect_signed_evidence(spec.get("evidence_profile", "healthy"))
    mutation = spec.get("mutation", "none")

    if mutation == "self_signed_evidence":
        fake_keypair = risk_gate_keypair()
        document = dict(signed_evidence["document"])
        document["service_state"] = "healthy"
        signed_evidence = {
            "document": document,
            "signature": sign_json_document(document, fake_keypair),
            "public_key_b64": fake_keypair.public_key_b64,
            "digest": signed_evidence["digest"],
        }
        mutation = "none"

    if mutation in {"none", "poisoned_context_valid_intent"}:
        decision = gate.evaluate(intent, signed_evidence)
        if not decision.allowed:
            return {"actual": "RISK_GATE_BLOCK", "reason": decision.reason}
        response, _ = run_through_broker(build_mcp_payload(intent, decision.receipt))
        return {"actual": classify_broker_response(response), "reason": json.dumps(response, sort_keys=True)}

    if mutation == "missing_receipt":
        response, _ = run_through_broker(build_mcp_payload(intent, None))
        return {"actual": classify_broker_response(response), "reason": json.dumps(response, sort_keys=True)}

    if mutation == "tamper_payload_after_receipt":
        decision = gate.evaluate(intent, signed_evidence)
        if not decision.allowed:
            return {"actual": "RISK_GATE_BLOCK", "reason": decision.reason}
        tampered_intent = json.loads(json.dumps(intent))
        tampered_intent["arguments"]["artifact"] = "payment-service:v99"
        response, _ = run_through_broker(build_mcp_payload(tampered_intent, decision.receipt))
        return {"actual": classify_broker_response(response), "reason": json.dumps(response, sort_keys=True)}

    if mutation == "expired_receipt":
        receipt = manual_receipt(
            intent=intent,
            evidence_digest=signed_evidence["digest"],
            timestamp=int(time.time()) - 120,
        )
        response, _ = run_through_broker(build_mcp_payload(intent, receipt))
        return {"actual": classify_broker_response(response), "reason": json.dumps(response, sort_keys=True)}

    if mutation == "signed_unauthorized_target":
        receipt = manual_receipt(intent=intent, evidence_digest=signed_evidence["digest"])
        response, _ = run_through_broker(build_mcp_payload(intent, receipt))
        return {"actual": classify_broker_response(response), "reason": json.dumps(response, sort_keys=True)}

    raise ValueError(f"Unknown attack mutation: {mutation}")


def expected_matches(expected: str, actual: str) -> bool:
    """Evaluates if the actual enforcement outcome matches the expected security posture."""
    if expected == actual:
        return True
    return expected == "OUT_OF_SCOPE_ALLOWED" and actual == "ALLOW"


def main() -> None:
    """Entry point for the Red Team execution suite."""
    specs = load_attack_specs()
    rows = []
    failures = 0
    for spec in specs:
        result = run_attack(spec)
        expected = spec["expected"]
        actual = result["actual"]
        ok = expected_matches(expected, actual)
        failures += 0 if ok else 1
        rows.append(
            {
                "id": spec["id"],
                "expected": expected,
                "actual": actual,
                "verdict": "PASS" if ok else "FAIL",
                "reason": result["reason"],
            }
        )

    print("| Attack | Expected | Actual | Verdict |")
    print("| --- | --- | --- | --- |")
    for row in rows:
        print(f"| {row['id']} | {row['expected']} | {row['actual']} | {row['verdict']} |")

    print("\nNotes:")
    for row in rows:
        print(f"- {row['id']}: {row['reason']}")

    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
