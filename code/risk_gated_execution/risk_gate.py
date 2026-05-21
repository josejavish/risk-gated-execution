"""Runtime primitives for the risk-gated execution benchmark."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from time import perf_counter
from typing import Any


class Decision(str, Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    DEGRADE = "DEGRADE"
    REQUIRE_MORE_EVIDENCE = "REQUIRE_MORE_EVIDENCE"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Evidence:
    name: str
    value: Any
    source: str
    timestamp: int
    confidence: float = 1.0


@dataclass(frozen=True)
class Intent:
    intent_id: str
    action_type: str
    target: str
    risk_level: RiskLevel
    created_at: int
    expires_at: int
    required_evidence: tuple[str, ...]
    rollback_plan: str | None
    payload: dict[str, Any]
    expected_state: str = "healthy"


@dataclass(frozen=True)
class GateConfig:
    authorized_targets: frozenset[str]
    evidence_ttl_seconds: int = 120
    require_fresh_evidence: bool = True
    require_rollback_for_high_risk: bool = True
    require_target_authorization: bool = True
    require_expiration_check: bool = True
    require_audit_ledger: bool = True


@dataclass(frozen=True)
class GateResult:
    decision: Decision
    reason: str
    decision_time_ms: float
    missing_evidence: tuple[str, ...] = ()


@dataclass
class AuditLedger:
    enabled: bool = True
    records: list[dict[str, Any]] = field(default_factory=list)

    def record(
        self,
        *,
        intent: Intent,
        result: GateResult,
        evidence: dict[str, Evidence],
        executed: bool,
        baseline: bool = False,
    ) -> None:
        if not self.enabled:
            return
        self.records.append(
            {
                "trace_id": intent.intent_id,
                "baseline": baseline,
                "intent_id": intent.intent_id,
                "action_type": intent.action_type,
                "target": intent.target,
                "risk_level": intent.risk_level.value,
                "decision": result.decision.value,
                "decision_reason": result.reason,
                "executed": executed,
                "rollback_available": bool(intent.rollback_plan),
                "evidence_names": sorted(evidence),
                "missing_evidence": list(result.missing_evidence),
            }
        )


class EvidenceProvider:
    def __init__(self, evidence_by_name: dict[str, Evidence], latency_ms_per_item: float = 5.0) -> None:
        self._evidence_by_name = evidence_by_name
        self.latency_ms_per_item = latency_ms_per_item

    def collect(self, names: tuple[str, ...]) -> dict[str, Evidence]:
        import time
        if names:
            time.sleep((len(names) * self.latency_ms_per_item) / 1000.0)
        return {name: self._evidence_by_name[name] for name in names if name in self._evidence_by_name}


class RiskGate:
    def __init__(self, config: GateConfig) -> None:
        self.config = config

    def evaluate(self, intent: Intent, provider: EvidenceProvider, now: int) -> GateResult:
        started = perf_counter()
        evidence = provider.collect(intent.required_evidence)
        decision, reason, missing = self._evaluate(intent, evidence, now)
        elapsed_ms = (perf_counter() - started) * 1000
        return GateResult(decision=decision, reason=reason, decision_time_ms=elapsed_ms, missing_evidence=missing)

    def _evaluate(
        self, intent: Intent, evidence: dict[str, Evidence], now: int
    ) -> tuple[Decision, str, tuple[str, ...]]:
        if self.config.require_expiration_check and now > intent.expires_at:
            return Decision.BLOCK, "intent expired", ()

        if self.config.require_target_authorization and intent.target not in self.config.authorized_targets:
            return Decision.BLOCK, "target is not authorized", ()

        if (
            self.config.require_rollback_for_high_risk
            and intent.risk_level == RiskLevel.HIGH
            and not intent.rollback_plan
        ):
            return Decision.BLOCK, "high-risk action requires rollback plan", ()

        missing = tuple(name for name in intent.required_evidence if name not in evidence)
        if missing:
            return Decision.REQUIRE_MORE_EVIDENCE, "required evidence missing", missing

        if self.config.require_fresh_evidence:
            stale = tuple(
                name
                for name in intent.required_evidence
                if now - evidence[name].timestamp > self.config.evidence_ttl_seconds
            )
            if stale:
                return Decision.BLOCK, "evidence is stale", stale

        system_state = evidence.get("system_state")
        if system_state and system_state.value != intent.expected_state:
            return Decision.DEGRADE, "evidence contradicts expected system state", ()

        if intent.action_type == "delete_resource" and intent.payload.get("resource_id") == "*":
            return Decision.BLOCK, "wildcard destructive action is not allowed", ()

        return Decision.ALLOW, "all risk checks satisfied", ()


class BaselineActuator:
    def execute(self, intent: Intent) -> bool:
        return bool(intent.action_type and intent.target and intent.payload is not None)


class SimplePolicyEngine:
    """Static-rule baseline without dynamic evidence checks."""

    def __init__(self, authorized_targets: frozenset[str]) -> None:
        self.authorized_targets = authorized_targets

    def evaluate(self, intent: Intent) -> GateResult:
        started = perf_counter()
        decision, reason = self._evaluate(intent)
        elapsed_ms = (perf_counter() - started) * 1000
        return GateResult(decision=decision, reason=reason, decision_time_ms=elapsed_ms)

    def _evaluate(self, intent: Intent) -> tuple[Decision, str]:
        if intent.target not in self.authorized_targets:
            return Decision.BLOCK, "static policy rejected unauthorized target"
        if intent.action_type == "delete_resource" and intent.payload.get("resource_id") == "*":
            return Decision.BLOCK, "static policy rejected wildcard destructive action"
        if intent.risk_level == RiskLevel.HIGH and not intent.rollback_plan:
            return Decision.BLOCK, "static policy requires rollback for high-risk action"
        return Decision.ALLOW, "static policy allowed action"


class EvidenceAwarePolicyEngine:
    """Stronger baseline that checks evidence presence but lacks deep semantic checks."""

    def __init__(self, authorized_targets: frozenset[str]) -> None:
        self.authorized_targets = authorized_targets

    def evaluate(self, intent: Intent, provider: EvidenceProvider, now: int) -> GateResult:
        started = perf_counter()
        evidence = provider.collect(intent.required_evidence)
        decision, reason, missing = self._evaluate(intent, evidence, now)
        elapsed_ms = (perf_counter() - started) * 1000
        return GateResult(decision=decision, reason=reason, decision_time_ms=elapsed_ms, missing_evidence=missing)

    def _evaluate(self, intent: Intent, evidence: dict[str, Evidence], now: int) -> tuple[Decision, str, tuple[str, ...]]:
        if intent.target not in self.authorized_targets:
            return Decision.BLOCK, "target is not authorized", ()
        
        if intent.action_type == "delete_resource" and intent.payload.get("resource_id") == "*":
            return Decision.BLOCK, "wildcard destructive action is not allowed", ()
            
        if intent.risk_level == RiskLevel.HIGH and not intent.rollback_plan:
            return Decision.BLOCK, "high-risk action requires rollback plan", ()

        if now > intent.expires_at:
            return Decision.BLOCK, "intent expired", ()

        missing = tuple(name for name in intent.required_evidence if name not in evidence)
        if missing:
            return Decision.REQUIRE_MORE_EVIDENCE, "required evidence missing", missing

        return Decision.ALLOW, "evidence-aware policy allowed action", ()


class GatedActuator:
    def execute(self, result: GateResult) -> bool:
        return result.decision == Decision.ALLOW
