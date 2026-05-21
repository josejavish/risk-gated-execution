"""Metric aggregation for the risk-gated execution benchmark."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Any


@dataclass(frozen=True)
class BenchmarkSummary:
    total_scenarios: int
    baseline_executed: int
    policy_executed: int
    evidence_policy_executed: int
    gated_executed: int
    baseline_unsafe_actions_executed: int
    policy_unsafe_actions_executed: int
    evidence_policy_unsafe_actions_executed: int
    gated_unsafe_actions_executed: int
    policy_unsafe_actions_blocked: int
    evidence_policy_unsafe_actions_blocked: int
    unsafe_actions_blocked: int
    policy_false_positive_blocks: int
    evidence_policy_false_positive_blocks: int
    false_positive_blocks: int
    policy_false_negative_allows: int
    evidence_policy_false_negative_allows: int
    false_negative_allows: int
    audit_records_generated: int
    records_with_evidence: int
    records_with_decision_reason: int
    records_with_trace_id: int
    incident_reconstructability_score: float
    rollback_plan_coverage: float
    avg_gate_decision_time_ms: float
    p50_gate_decision_time_ms: float
    p95_gate_decision_time_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize(results: list[dict[str, Any]], audit_records: list[dict[str, Any]]) -> BenchmarkSummary:
    unsafe = [row for row in results if row["unsafe_if_executed"]]
    safe = [row for row in results if not row["unsafe_if_executed"]]
    gate_times = [float(row["gate_decision_time_ms"]) for row in results]
    high_risk = [row for row in results if row["risk_level"] == "HIGH"]
    high_risk_with_rollback = [row for row in high_risk if row["rollback_available"]]

    reconstructible = 0
    for row in audit_records:
        if row.get("trace_id") and row.get("intent_id") and row.get("decision") and row.get("decision_reason") and "executed" in row and "rollback_available" in row and row.get("evidence_names") is not None:
            reconstructible += 1
    
    incident_reconstructability_score = (reconstructible / len(audit_records)) if audit_records else 0.0

    if gate_times:
        if len(gate_times) >= 2:
            from statistics import quantiles
            q = quantiles(gate_times, n=100, method='inclusive')
            p50 = q[49]
            p95 = q[94]
        else:
            p50 = gate_times[0]
            p95 = gate_times[0]
    else:
        p50 = 0.0
        p95 = 0.0

    return BenchmarkSummary(
        total_scenarios=len(results),
        baseline_executed=sum(1 for row in results if row["baseline_executed"]),
        policy_executed=sum(1 for row in results if row["policy_executed"]),
        evidence_policy_executed=sum(1 for row in results if row["evidence_policy_executed"]),
        gated_executed=sum(1 for row in results if row["gated_executed"]),
        baseline_unsafe_actions_executed=sum(1 for row in unsafe if row["baseline_executed"]),
        policy_unsafe_actions_executed=sum(1 for row in unsafe if row["policy_executed"]),
        evidence_policy_unsafe_actions_executed=sum(1 for row in unsafe if row["evidence_policy_executed"]),
        gated_unsafe_actions_executed=sum(1 for row in unsafe if row["gated_executed"]),
        policy_unsafe_actions_blocked=sum(1 for row in unsafe if not row["policy_executed"]),
        evidence_policy_unsafe_actions_blocked=sum(1 for row in unsafe if not row["evidence_policy_executed"]),
        unsafe_actions_blocked=sum(1 for row in unsafe if not row["gated_executed"]),
        policy_false_positive_blocks=sum(1 for row in safe if not row["policy_executed"]),
        evidence_policy_false_positive_blocks=sum(1 for row in safe if not row["evidence_policy_executed"]),
        false_positive_blocks=sum(1 for row in safe if not row["gated_executed"]),
        policy_false_negative_allows=sum(1 for row in unsafe if row["policy_executed"]),
        evidence_policy_false_negative_allows=sum(1 for row in unsafe if row["evidence_policy_executed"]),
        false_negative_allows=sum(1 for row in unsafe if row["gated_executed"]),
        audit_records_generated=len(audit_records),
        records_with_evidence=sum(1 for row in audit_records if row["evidence_names"]),
        records_with_decision_reason=sum(1 for row in audit_records if row["decision_reason"]),
        records_with_trace_id=sum(1 for row in audit_records if row["trace_id"]),
        incident_reconstructability_score=incident_reconstructability_score,
        rollback_plan_coverage=(
            len(high_risk_with_rollback) / len(high_risk) if high_risk else 1.0
        ),
        avg_gate_decision_time_ms=mean(gate_times) if gate_times else 0.0,
        p50_gate_decision_time_ms=p50,
        p95_gate_decision_time_ms=p95,
    )
