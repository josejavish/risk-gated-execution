"""Run the risk-gated execution benchmark and write reproducible artifacts."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from metrics import summarize
from risk_gate import (
    AuditLedger,
    BaselineActuator,
    Decision,
    GateConfig,
    GateResult,
    GatedActuator,
    RiskGate,
    SimplePolicyEngine,
    EvidenceAwarePolicyEngine,
    EvidenceProvider,
)
from scenarios import NOW, Scenario, build_scenarios


RESULTS_DIR = Path(__file__).resolve().parent / "results"


def run(config: GateConfig | None = None, iterations: int = 1) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    config = config or GateConfig(
        authorized_targets=frozenset({"inventory-service", "payment-service", "analytics-cluster"})
    )
    scenarios = build_scenarios()
    baseline = BaselineActuator()
    policy = SimplePolicyEngine(config.authorized_targets)
    evidence_policy = EvidenceAwarePolicyEngine(config.authorized_targets)
    gated = GatedActuator()
    gate = RiskGate(config)
    ledger = AuditLedger(enabled=config.require_audit_ledger)
    rows: list[dict[str, Any]] = []

    for scenario in scenarios:
        for _ in range(iterations):
            provider = EvidenceProvider(scenario.evidence, latency_ms_per_item=5.0)

            baseline_executed = baseline.execute(scenario.intent)
            baseline_result = GateResult(
                decision=Decision.ALLOW,
                reason="baseline direct execution",
                decision_time_ms=0.0,
            )
            ledger.record(
                intent=scenario.intent,
                result=baseline_result,
                evidence=scenario.evidence,
                executed=baseline_executed,
                baseline=True,
            )

            policy_result = policy.evaluate(scenario.intent)
            policy_executed = gated.execute(policy_result)
            
            evidence_policy_result = evidence_policy.evaluate(scenario.intent, provider, NOW)
            evidence_policy_executed = gated.execute(evidence_policy_result)
            
            gate_result = gate.evaluate(scenario.intent, provider, NOW)
            gated_executed = gated.execute(gate_result)
            ledger.record(
                intent=scenario.intent,
                result=gate_result,
                evidence=scenario.evidence,
                executed=gated_executed,
            )
            rows.append(
                _row_for_scenario(
                    scenario,
                    baseline_executed,
                    policy_executed,
                    policy_result,
                    evidence_policy_executed,
                    evidence_policy_result,
                    gated_executed,
                    gate_result,
                )
            )

    return rows, ledger.records


def _row_for_scenario(
    scenario: Scenario,
    baseline_executed: bool,
    policy_executed: bool,
    policy_result: GateResult,
    evidence_policy_executed: bool,
    evidence_policy_result: GateResult,
    gated_executed: bool,
    gate_result: GateResult,
) -> dict[str, Any]:
    return {
        "scenario_id": scenario.scenario_id,
        "scenario": scenario.name,
        "action_type": scenario.intent.action_type,
        "target": scenario.intent.target,
        "risk_level": scenario.intent.risk_level.value,
        "unsafe_if_executed": scenario.unsafe_if_executed,
        "baseline_executed": baseline_executed,
        "policy_executed": policy_executed,
        "policy_decision": policy_result.decision.value,
        "policy_reason": policy_result.reason,
        "policy_decision_time_ms": round(policy_result.decision_time_ms, 6),
        "evidence_policy_executed": evidence_policy_executed,
        "evidence_policy_decision": evidence_policy_result.decision.value,
        "evidence_policy_reason": evidence_policy_result.reason,
        "evidence_policy_decision_time_ms": round(evidence_policy_result.decision_time_ms, 6),
        "gated_executed": gated_executed,
        "expected_gated_execution": scenario.expected_gated_execution,
        "gate_decision": gate_result.decision.value,
        "gate_reason": gate_result.reason,
        "missing_evidence": "|".join(gate_result.missing_evidence),
        "gate_decision_time_ms": round(gate_result.decision_time_ms, 6),
        "rollback_available": bool(scenario.intent.rollback_plan),
    }


def write_outputs(rows: list[dict[str, Any]], audit_records: list[dict[str, Any]], iterations: int = 1) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    summary = summarize(rows, audit_records)
    ablations = run_ablations(iterations=iterations)
    _write_csv(RESULTS_DIR / "scenario_results.csv", rows)
    _write_csv(RESULTS_DIR / "ablation_results.csv", ablations)
    _write_json(RESULTS_DIR / "audit_ledger.json", audit_records)
    _write_json(RESULTS_DIR / "summary.json", summary.to_dict())
    _write_json(RESULTS_DIR / "ablation_results.json", ablations)
    _write_markdown(RESULTS_DIR / "summary.md", summary.to_dict(), rows, ablations)


def run_ablations(iterations: int = 1) -> list[dict[str, Any]]:
    base_targets = frozenset({"inventory-service", "payment-service", "analytics-cluster"})
    variants = {
        "full_gate": GateConfig(authorized_targets=base_targets),
        "no_expiration_check": GateConfig(
            authorized_targets=base_targets,
            require_expiration_check=False,
        ),
        "no_rollback_requirement": GateConfig(
            authorized_targets=base_targets,
            require_rollback_for_high_risk=False,
        ),
        "no_evidence_freshness": GateConfig(
            authorized_targets=base_targets,
            require_fresh_evidence=False,
        ),
        "no_target_authorization": GateConfig(
            authorized_targets=base_targets,
            require_target_authorization=False,
        ),
        "no_audit_ledger": GateConfig(
            authorized_targets=base_targets,
            require_audit_ledger=False,
        ),
    }
    rows: list[dict[str, Any]] = []
    for variant, config in variants.items():
        scenario_rows, audit_records = run(config, iterations=iterations)
        summary = summarize(scenario_rows, audit_records)
        data = summary.to_dict()
        rows.append(
            {
                "variant": variant,
                "policy_unsafe_actions_blocked": data["policy_unsafe_actions_blocked"],
                "evidence_policy_unsafe_actions_blocked": data["evidence_policy_unsafe_actions_blocked"],
                "unsafe_actions_blocked": data["unsafe_actions_blocked"],
                "policy_unsafe_actions_executed": data["policy_unsafe_actions_executed"],
                "evidence_policy_unsafe_actions_executed": data["evidence_policy_unsafe_actions_executed"],
                "gated_unsafe_actions_executed": data["gated_unsafe_actions_executed"],
                "policy_false_positive_blocks": data["policy_false_positive_blocks"],
                "evidence_policy_false_positive_blocks": data["evidence_policy_false_positive_blocks"],
                "false_positive_blocks": data["false_positive_blocks"],
                "policy_false_negative_allows": data["policy_false_negative_allows"],
                "evidence_policy_false_negative_allows": data["evidence_policy_false_negative_allows"],
                "false_negative_allows": data["false_negative_allows"],
                "audit_records_generated": data["audit_records_generated"],
                "records_with_decision_reason": data["records_with_decision_reason"],
                "incident_reconstructability_score": data["incident_reconstructability_score"],
                "avg_gate_decision_time_ms": data["avg_gate_decision_time_ms"],
                "p50_gate_decision_time_ms": data["p50_gate_decision_time_ms"],
                "p95_gate_decision_time_ms": data["p95_gate_decision_time_ms"],
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(
    path: Path,
    summary: dict[str, Any],
    rows: list[dict[str, Any]],
    ablations: list[dict[str, Any]],
) -> None:
    lines = [
        "# Risk-Gated Execution Benchmark Summary",
        "",
        "## Metrics",
        "",
    ]
    for key, value in summary.items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(
        [
            "",
            "## Scenario Results",
            "",
            "| ID | Scenario | Direct | Static Policy | Evidence Policy | Gated | Policy Reason | Evidence Policy Reason | Gate Reason |",
            "| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |",
        ]
    )
    # Group rows by scenario ID for markdown report to keep it readable, showing the first iteration
    seen = set()
    for row in rows:
        if row["scenario_id"] not in seen:
            seen.add(row["scenario_id"])
            lines.append(
                "| {scenario_id} | {scenario} | {baseline_executed} | {policy_executed} | {evidence_policy_executed} | {gated_executed} | {policy_reason} | {evidence_policy_reason} | {gate_reason} |".format(
                    **row
                )
            )
    lines.extend(
        [
            "",
            "## Ablations",
            "",
            "| Variant | Policy Unsafe Blocked | Evidence Policy Unsafe Blocked | Gated Unsafe Blocked | Policy Unsafe Executed | Evidence Policy Unsafe Executed | Gated Unsafe Executed | Audit Records | Avg Time (ms) | P95 Time (ms) |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in ablations:
        lines.append(
            "| {variant} | {policy_unsafe_actions_blocked} | {evidence_policy_unsafe_actions_blocked} | {unsafe_actions_blocked} | {policy_unsafe_actions_executed} | {evidence_policy_unsafe_actions_executed} | {gated_unsafe_actions_executed} | {audit_records_generated} | {avg_gate_decision_time_ms:.2f} | {p95_gate_decision_time_ms:.2f} |".format(
                **row
            )
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the risk-gated execution benchmark.")
    parser.add_argument("--iterations", type=int, default=1, help="Number of iterations per scenario (default: 1)")
    args = parser.parse_args()

    rows, audit_records = run(iterations=args.iterations)
    write_outputs(rows, audit_records, iterations=args.iterations)
    summary = summarize(rows, audit_records)
    print(json.dumps(summary.to_dict(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
