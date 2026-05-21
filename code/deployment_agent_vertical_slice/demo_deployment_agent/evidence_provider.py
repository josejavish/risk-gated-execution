"""Signed evidence provider for the deployment vertical slice."""

from __future__ import annotations

import time
from typing import Any

from .crypto_utils import (
    canonical_json,
    evidence_keypair,
    sha256_hex,
    sign_json_document,
)


PROFILES: dict[str, dict[str, Any]] = {
    "healthy": {
        "service_state": "healthy",
        "change_window": True,
        "incident_freeze": False,
        "rollback_available": True,
        "context_trust": "trusted_internal_ticket",
    },
    "stale": {
        "service_state": "healthy",
        "change_window": True,
        "incident_freeze": False,
        "rollback_available": True,
        "context_trust": "trusted_internal_ticket",
        "timestamp_offset_seconds": -600,
    },
    "incident_freeze": {
        "service_state": "healthy",
        "change_window": True,
        "incident_freeze": True,
        "rollback_available": True,
        "context_trust": "trusted_internal_ticket",
    },
    "no_rollback": {
        "service_state": "healthy",
        "change_window": True,
        "incident_freeze": False,
        "rollback_available": False,
        "context_trust": "trusted_internal_ticket",
    },
    "degraded": {
        "service_state": "degraded",
        "change_window": True,
        "incident_freeze": False,
        "rollback_available": True,
        "context_trust": "trusted_internal_ticket",
    },
}


def collect_signed_evidence(profile: str = "healthy", ttl_seconds: int = 60) -> dict[str, Any]:
    if profile not in PROFILES:
        raise ValueError(f"Unknown evidence profile: {profile}")

    keypair = evidence_keypair()
    profile_data = dict(PROFILES[profile])
    timestamp_offset = int(profile_data.pop("timestamp_offset_seconds", 0))
    document = {
        "schema": "riskgate.evidence.v1",
        "source": "demo-evidence-provider",
        "subject": "payment-service",
        "timestamp": int(time.time()) + timestamp_offset,
        "ttl_seconds": ttl_seconds,
        **profile_data,
    }
    signature = sign_json_document(document, keypair)
    return {
        "document": document,
        "signature": signature,
        "public_key_b64": keypair.public_key_b64,
        "digest": sha256_hex(canonical_json(document)),
    }
