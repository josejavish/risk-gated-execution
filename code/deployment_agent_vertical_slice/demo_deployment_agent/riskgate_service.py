"""RiskGate service for the deployment vertical slice."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crypto_utils import (
    evidence_keypair,
    receipt_binding,
    risk_gate_keypair,
    sign_receipt_hash,
    verify_json_signature,
)


DEFAULT_POLICY = {
    "agent_id": "deployment-agent",
    "authorized_targets": ["payment-service"],
    "allowed_actions": ["deploy"],
    "forbidden_actions": ["delete_repo", "rotate_root_ca", "drop_database"],
    "evidence_ttl_seconds": 60,
    "require_receipt": True,
    "trusted_evidence_public_key_b64": evidence_keypair().public_key_b64,
}


class RiskGateBlocked(Exception):
    """Raised when the gate refuses to issue a receipt."""


@dataclass(frozen=True)
class GateDecision:
    allowed: bool
    reason: str
    receipt: dict[str, Any] | None = None


class DeploymentRiskGate:
    def __init__(self, policy: dict[str, Any] | None = None) -> None:
        self.policy = {**DEFAULT_POLICY, **(policy or {})}
        self.keypair = risk_gate_keypair()

    @property
    def broker_policy(self) -> dict[str, Any]:
        return {
            **self.policy,
            "public_key_b64": self.keypair.public_key_b64,
        }

    def get_openai_tool_schema(self) -> dict[str, Any]:
        """Returns the OpenAI Tool Calling JSON schema for the secure deploy action."""
        return {
            "type": "function",
            "function": {
                "name": "secure_deploy",
                "description": (
                    "Deploys an artifact to a target service. "
                    "Execution is strictly risk-gated. The intent will be evaluated against "
                    "cryptographic evidence of service health, change windows, and rollback plans "
                    "before generating an execution receipt."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "target": {
                            "type": "string",
                            "description": "The target service to deploy to (e.g., 'payment-service').",
                        },
                        "artifact": {
                            "type": "string",
                            "description": "The artifact version to deploy (e.g., 'payment-service:v43').",
                        },
                        "dry_run": {
                            "type": "boolean",
                            "description": "Must be true for initial deployment validation.",
                        },
                        "rollback_plan": {
                            "type": "string",
                            "description": "The exact command or artifact to deploy if this deployment fails.",
                        },
                    },
                    "required": ["target", "artifact", "dry_run", "rollback_plan"],
                },
            },
        }

    def write_broker_policy(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.broker_policy, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def evaluate(self, intent: dict[str, Any], signed_evidence: dict[str, Any]) -> GateDecision:
        try:
            self._validate_intent_shape(intent)
            evidence = self._validate_evidence(signed_evidence)
            self._validate_policy(intent, evidence)
            receipt = self._issue_receipt(intent, signed_evidence)
            return GateDecision(allowed=True, reason="risk checks satisfied", receipt=receipt)
        except RiskGateBlocked as exc:
            return GateDecision(allowed=False, reason=str(exc), receipt=None)

    def _validate_intent_shape(self, intent: dict[str, Any]) -> None:
        required = {"intent_id", "action_type", "target", "arguments"}
        missing = sorted(required - set(intent))
        if missing:
            raise RiskGateBlocked(f"intent missing fields: {', '.join(missing)}")
        if not isinstance(intent["arguments"], dict):
            raise RiskGateBlocked("intent arguments must be an object")

    def _validate_evidence(self, signed_evidence: dict[str, Any]) -> dict[str, Any]:
        document = signed_evidence.get("document")
        signature = signed_evidence.get("signature")
        public_key_b64 = signed_evidence.get("public_key_b64")
        if not isinstance(document, dict) or not signature or not public_key_b64:
            raise RiskGateBlocked("evidence envelope is incomplete")
        if public_key_b64 != self.policy["trusted_evidence_public_key_b64"]:
            raise RiskGateBlocked("evidence signer is not trusted")
        try:
            verify_json_signature(document, signature, public_key_b64)
        except Exception as exc:  # cryptography raises InvalidSignature without useful text
            raise RiskGateBlocked("evidence signature verification failed") from exc

        now = int(time.time())
        ttl = int(document.get("ttl_seconds", self.policy["evidence_ttl_seconds"]))
        age = now - int(document.get("timestamp", 0))
        if age < -30:
            raise RiskGateBlocked("evidence timestamp is in the future")
        if ttl > 0 and age > ttl:
            raise RiskGateBlocked(f"evidence is stale: age={age}s ttl={ttl}s")
        return document

    def _validate_policy(self, intent: dict[str, Any], evidence: dict[str, Any]) -> None:
        action = intent["action_type"]
        target = intent["target"]
        args = intent["arguments"]

        if target not in self.policy["authorized_targets"]:
            raise RiskGateBlocked(f"target is not authorized: {target}")
        if action in self.policy["forbidden_actions"]:
            raise RiskGateBlocked(f"action is forbidden: {action}")
        if action not in self.policy["allowed_actions"]:
            raise RiskGateBlocked(f"action is not allowed: {action}")
        if evidence.get("subject") != target:
            raise RiskGateBlocked("evidence subject does not match target")
        if evidence.get("incident_freeze"):
            raise RiskGateBlocked("incident freeze is active")
        if evidence.get("service_state") != "healthy":
            raise RiskGateBlocked("service state is not healthy")
        if not evidence.get("change_window"):
            raise RiskGateBlocked("change window is closed")
        if action == "deploy" and not evidence.get("rollback_available"):
            raise RiskGateBlocked("deployment requires rollback evidence")
        if action == "deploy" and not args.get("dry_run"):
            raise RiskGateBlocked("deployment requires dry_run=true before commit")

    def _issue_receipt(self, intent: dict[str, Any], signed_evidence: dict[str, Any]) -> dict[str, Any]:
        timestamp = int(time.time())
        evidence_digest = signed_evidence["digest"]
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
            "signature": sign_receipt_hash(binding, self.keypair),
        }


def default_deploy_intent() -> dict[str, Any]:
    return {
        "intent_id": f"deploy-{int(time.time())}",
        "action_type": "deploy",
        "target": "payment-service",
        "arguments": {
            "artifact": "payment-service:v43",
            "dry_run": True,
            "rollback_plan": "redeploy payment-service:v42",
        },
    }
