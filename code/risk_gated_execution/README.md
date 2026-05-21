# Risk-Gated Execution Benchmark

Minimal benchmark for evaluating risk-gated execution in enterprise agentic workflows.

This benchmark compares direct execution against a runtime pattern where an agent must emit an intent contract and pass a risk gate before a critical action reaches an actuator.

## Why This Exists

Enterprise agentic systems cannot rely only on prompts, static permissions, or direct tool calls for critical actions. They need operational control points:

- intent contracts;
- evidence before execution;
- target authorization;
- expiration checks;
- rollback requirements;
- causal audit records.

This benchmark is intentionally small. Its purpose is to make the control
pattern inspectable, not to claim production-wide safety from synthetic data.

## Run

```bash
python3 run_benchmark.py
```

The command writes:

- `results/scenario_results.csv`
- `results/ablation_results.csv`
- `results/audit_ledger.json`
- `results/summary.json`
- `results/summary.md`

## Benchmark Shape

Baseline:

- the planner sends an action directly to the actuator;
- the actuator executes if the payload is structurally present.

Static policy baseline:

- rejects unauthorized targets;
- rejects wildcard destructive actions;
- requires rollback for high-risk actions;
- does not inspect dynamic evidence, evidence freshness, expiration, or contradictory runtime state.

Evidence-aware policy baseline:

- checks targets, wildcards, rollbacks, expiration, and evidence presence;
- does not check semantic contradiction or deep freshness;
- does not enforce strict causal audit reconstructability.

Gated:

- the planner emits an intent contract;
- the risk gate validates evidence, target, expiration and rollback requirements;
- the gated actuator executes only when the gate returns `ALLOW`;
- every decision is recorded in the audit ledger.

## Scenarios

- low-risk safe action;
- high-risk action with valid evidence;
- high-risk action with missing evidence;
- expired intent;
- unauthorized dangerous target;
- high-risk action without rollback;
- contradictory evidence;
- stale evidence;
- wildcard destructive action.

## Metrics

- unsafe actions executed by baseline;
- unsafe actions blocked by gated runtime;
- false positive blocks;
- false negative allows;
- audit records generated;
- records with evidence;
- rollback plan coverage;
- average gate decision time.

Current generated summary:

- direct baseline executes 700 unsafe actions across the checked-in 100-iteration run;
- static policy baseline executes 400 unsafe actions;
- evidence-aware baseline executes 200 unsafe actions;
- risk-gated runtime executes 0 unsafe actions;
- risk-gated runtime blocks 700 of 700 unsafe actions;
- incident reconstructability score is computed based on audit ledger detail.

## Ablations

The runner also disables one gate feature at a time:

- expiration check;
- rollback requirement;
- evidence freshness;
- target authorization;
- audit ledger.

This makes the benchmark harder to fake: if a component does not change behavior or evidence quality, it should not survive into the public thesis.

## Interpretation Limits

- The benchmark uses synthetic fixtures, not production traces.
- Evidence values are local fixtures, not signed telemetry.
- The Python gate validates decision logic, not deployment topology.
- HTTP enforcement and local `stdio` enforcement are separate artifacts in this repo.
- A real deployment still needs workload identity, network containment, incident procedures, and trustworthy evidence providers.

## Scope

This project provides a minimal, reproducible benchmark for evaluating **Risk-Gated Execution** in agentic systems. It serves as a proof-of-concept for engineering teams building secure control planes for autonomous LLM agents in production environments.

The project is maintained by engineers focused on AI reliability and infrastructure security.
