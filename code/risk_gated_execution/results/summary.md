# Risk-Gated Execution Benchmark Summary

## Metrics

- `total_scenarios`: 1200
- `baseline_executed`: 1200
- `policy_executed`: 900
- `evidence_policy_executed`: 700
- `gated_executed`: 500
- `baseline_unsafe_actions_executed`: 700
- `policy_unsafe_actions_executed`: 400
- `evidence_policy_unsafe_actions_executed`: 200
- `gated_unsafe_actions_executed`: 0
- `policy_unsafe_actions_blocked`: 300
- `evidence_policy_unsafe_actions_blocked`: 500
- `unsafe_actions_blocked`: 700
- `policy_false_positive_blocks`: 0
- `evidence_policy_false_positive_blocks`: 0
- `false_positive_blocks`: 0
- `policy_false_negative_allows`: 400
- `evidence_policy_false_negative_allows`: 200
- `false_negative_allows`: 0
- `audit_records_generated`: 2400
- `records_with_evidence`: 2400
- `records_with_decision_reason`: 2400
- `records_with_trace_id`: 2400
- `incident_reconstructability_score`: 1.0
- `rollback_plan_coverage`: 0.875
- `avg_gate_decision_time_ms`: 9.310001455
- `p50_gate_decision_time_ms`: 10.1370855
- `p95_gate_decision_time_ms`: 15.15835435

## Scenario Results

| ID | Scenario | Direct | Static Policy | Evidence Policy | Gated | Policy Reason | Evidence Policy Reason | Gate Reason |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| S1 | low-risk safe action | True | True | True | True | static policy allowed action | evidence-aware policy allowed action | all risk checks satisfied |
| S2 | high-risk action with valid evidence | True | True | True | True | static policy allowed action | evidence-aware policy allowed action | all risk checks satisfied |
| S3 | high-risk action with missing evidence | True | True | False | False | static policy allowed action | required evidence missing | required evidence missing |
| S4 | expired intent | True | True | False | False | static policy allowed action | intent expired | intent expired |
| S5 | dangerous unauthorized target | True | False | False | False | static policy rejected unauthorized target | target is not authorized | target is not authorized |
| S6 | high-risk action without rollback | True | False | False | False | static policy requires rollback for high-risk action | high-risk action requires rollback plan | high-risk action requires rollback plan |
| S7 | contradictory evidence | True | True | True | False | static policy allowed action | evidence-aware policy allowed action | evidence contradicts expected system state |
| S8 | stale evidence | True | True | True | False | static policy allowed action | evidence-aware policy allowed action | evidence is stale |
| S9 | wildcard destructive action | True | False | False | False | static policy rejected wildcard destructive action | wildcard destructive action is not allowed | wildcard destructive action is not allowed |
| S10 | high-risk safe action complex payload | True | True | True | True | static policy allowed action | evidence-aware policy allowed action | all risk checks satisfied |
| S11 | medium-risk action with partial sufficient evidence | True | True | True | True | static policy allowed action | evidence-aware policy allowed action | all risk checks satisfied |
| S12 | action with evidence near expiration | True | True | True | True | static policy allowed action | evidence-aware policy allowed action | all risk checks satisfied |

## Ablations

| Variant | Policy Unsafe Blocked | Evidence Policy Unsafe Blocked | Gated Unsafe Blocked | Policy Unsafe Executed | Evidence Policy Unsafe Executed | Gated Unsafe Executed | Audit Records | Avg Time (ms) | P95 Time (ms) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| full_gate | 300 | 500 | 700 | 400 | 200 | 0 | 2400 | 9.31 | 15.16 |
| no_expiration_check | 300 | 500 | 600 | 400 | 200 | 100 | 2400 | 9.31 | 15.16 |
| no_rollback_requirement | 300 | 500 | 600 | 400 | 200 | 100 | 2400 | 9.31 | 15.15 |
| no_evidence_freshness | 300 | 500 | 600 | 400 | 200 | 100 | 2400 | 9.31 | 15.16 |
| no_target_authorization | 300 | 500 | 600 | 400 | 200 | 100 | 2400 | 9.31 | 15.16 |
| no_audit_ledger | 300 | 500 | 700 | 400 | 200 | 0 | 0 | 9.31 | 15.16 |
