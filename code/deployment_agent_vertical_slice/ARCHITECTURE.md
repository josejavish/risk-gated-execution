# Architecture

## Control Boundary

The vertical slice separates three responsibilities:

1. **Reasoning:** the agent proposes a semantic deployment intent.
2. **Authorization:** RiskGate validates policy and signed operational evidence.
3. **Execution:** the Rust `stdio` broker verifies the receipt before the local tool sees the call.

The deployment tool is deliberately simple. The architectural value is the
boundary before the tool, not the tool itself.

## Components

### Agent Intent

The demo intent is:

```json
{
  "action_type": "deploy",
  "target": "payment-service",
  "arguments": {
    "artifact": "payment-service:v43",
    "dry_run": true,
    "rollback_plan": "redeploy payment-service:v42"
  }
}
```

### Evidence Provider

`demo_deployment_agent/evidence_provider.py` emits a signed evidence envelope:

- service health;
- change window;
- incident freeze;
- rollback availability;
- timestamp and TTL;
- Ed25519 signature over the evidence document.

The RiskGate pins the trusted evidence provider public key. It does not accept
self-signed evidence envelopes.

### RiskGate

`demo_deployment_agent/riskgate_service.py` verifies evidence and checks:

- target authorization;
- allowed and forbidden actions;
- evidence freshness;
- trusted evidence signer;
- incident freeze;
- service health;
- change-window state;
- rollback availability;
- dry-run posture.

If checks pass, it emits a receipt signed over:

```text
intent_id | action | target | canonical payload | evidence digest | timestamp
```

### Broker

The existing Rust broker in `../mcp_stdio_broker` is used as the local execution
boundary. It verifies the receipt and blocks calls before forwarding them to the
tool process.

### Actuator

`demo_deployment_agent/deployment_tool.py` is a minimal MCP-style JSON-RPC tool.
It represents a deployment API without introducing cloud dependencies.

## Red-Team Matrix

| Case | Expected |
| --- | --- |
| safe deployment | allowed |
| missing receipt | broker block |
| tampered payload | broker block |
| expired receipt | broker block |
| unauthorized target | broker block |
| stale evidence | RiskGate block |
| incident freeze | RiskGate block |
| no rollback evidence | RiskGate block |
| self-signed evidence | RiskGate block |
| valid intent from poisoned context | allowed, documented limitation |

## Production Gaps

While the runtime enforces strict cryptographic verification (RFC 8785) and OS-level sandboxing (Namespaces, `CLONE_NEWNET`, `rlimit`), the next production-grade improvements for the surrounding ecosystem are:

- integrate the deterministic keys with KMS/SPIRE provisioning;
- ingest signed telemetry from Prometheus/OpenTelemetry or deployment systems;
- add integration with a real agent runner;
- add source-aware context provenance for prompt-injection resistance.
