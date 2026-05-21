# Risk-Gated Deployment Agent Vertical Slice

This is the hiring-grade vertical slice for the Risk-Gated Execution thesis.

It demonstrates a single enterprise use case: an AI deployment agent wants to
deploy `payment-service`. The action is allowed only if a RiskGate verifies
fresh signed evidence, emits a signed receipt, and the Rust MCP `stdio` broker
verifies that receipt before forwarding the tool call to the deployment tool.

## Run

```bash
make demo
```

Expected result: a valid deployment intent passes through RiskGate and the Rust
broker, then reaches the dummy deployment tool.

```bash
make redteam
```

Expected result: unsafe or tampered attempts are blocked, while the
`poisoned_context_valid_intent` case is explicitly reported as an out-of-scope
reasoning-provenance limitation.

## Flow

```text
agent intent
  -> signed evidence provider
  -> RiskGate policy and evidence evaluation
  -> signed execution receipt
  -> Rust MCP stdio broker
  -> deployment tool actuator
  -> JSON-RPC result or block
```

## What Is Implemented

- signed evidence envelope using Ed25519;
- RiskGate evidence verification;
- RiskGate policy checks for trusted evidence signer, target, action, health, change window, rollback, incident freeze, and dry-run posture;
- signed execution receipt bound to intent, action, target, payload, evidence digest, and timestamp;
- Rust broker verification before local `stdio` tool execution;
- red-team cases for missing receipt, tampered payload, expired receipt, unauthorized target, stale evidence, incident freeze, no rollback, self-signed evidence, and poisoned reasoning.

## What Is Not Implemented

- production key management;
- signed telemetry from real monitoring systems;
- RFC 8785 canonical JSON across arbitrary payloads;
- real agent framework integration;
- complete process sandboxing;
- prompt-injection provenance tracking.

The point is to show a concrete end-to-end control boundary, not to claim full
agent safety.
