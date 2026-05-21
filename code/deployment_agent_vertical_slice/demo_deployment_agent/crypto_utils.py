"""Shared signing utilities for the deployment vertical slice.

The demo uses deterministic Ed25519 keys so the repository is reproducible.
Production systems should provision signing keys through KMS/SPIRE and rotate
them outside the application repository.
"""

from __future__ import annotations

import base64
import hashlib
import json
import jcs  # type: ignore
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


RISK_GATE_SEED = bytes.fromhex(
    "1f1e1d1c1b1a191817161514131211100f0e0d0c0b0a09080706050403020100"
)
EVIDENCE_SEED = bytes.fromhex(
    "000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f"
)


@dataclass(frozen=True)
class DemoKeyPair:
    private_key: Ed25519PrivateKey
    public_key: Ed25519PublicKey

    @property
    def public_key_b64(self) -> str:
        """Returns the raw Ed25519 public key encoded in Base64 for deterministic network transport."""
        return base64.b64encode(
            self.public_key.public_bytes(
                encoding=Encoding.Raw,
                format=PublicFormat.Raw,
            )
        ).decode("ascii")


def risk_gate_keypair() -> DemoKeyPair:
    """Generates the deterministic Ed25519 keypair for the RiskGate middleware. In production, this must be derived from a KMS/HSM."""
    private_key = Ed25519PrivateKey.from_private_bytes(RISK_GATE_SEED)
    return DemoKeyPair(private_key=private_key, public_key=private_key.public_key())


def evidence_keypair() -> DemoKeyPair:
    """Generates the deterministic Ed25519 keypair representing the external Evidence Provider (e.g., ServiceNow, Datadog)."""
    private_key = Ed25519PrivateKey.from_private_bytes(EVIDENCE_SEED)
    return DemoKeyPair(private_key=private_key, public_key=private_key.public_key())


def canonical_json(value: Any) -> str:
    """Returns RFC 8785 canonical JSON string."""
    return jcs.canonicalize(value).decode("utf-8")


def sha256_hex(value: str) -> str:
    """Computes the SHA-256 digest of a UTF-8 string, returning the hex representation for receipt binding."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def receipt_binding(
    *,
    intent_id: str,
    action_type: str,
    target: str,
    payload: dict[str, Any],
    evidence_digest: str,
    timestamp: int,
) -> str:
    payload_str = canonical_json(payload)
    return (
        f"intent:{intent_id}|action:{action_type}|target:{target}|"
        f"payload:{payload_str}|evidence:{evidence_digest}|ts:{timestamp}"
    )


def sign_receipt_hash(binding: str, keypair: DemoKeyPair) -> str:
    """Cryptographically signs the deterministic intent binding using Ed25519, proving RiskGate authorization."""
    digest = hashlib.sha256(binding.encode("utf-8")).digest()
    signature = keypair.private_key.sign(digest)
    return base64.b64encode(signature).decode("ascii")


def sign_json_document(document: dict[str, Any], keypair: DemoKeyPair) -> str:
    """Signs a JSON document strictly using RFC 8785 canonicalization to prevent serialization malleability attacks."""
    signature = keypair.private_key.sign(canonical_json(document).encode("utf-8"))
    return base64.b64encode(signature).decode("ascii")


def verify_json_signature(document: dict[str, Any], signature_b64: str, public_key_b64: str) -> bool:
    """Verifies an Ed25519 signature over an RFC 8785 canonicalized JSON document, enforcing strict cryptographic provenance."""
    public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
    signature = base64.b64decode(signature_b64)
    public_key.verify(signature, canonical_json(document).encode("utf-8"))
    return True
