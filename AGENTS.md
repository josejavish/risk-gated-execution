# Agentic Instructions (AGENTS.md)

**Target Audience:** Autonomous Coding Agents (Claude Code, Codex, SWE-agent, Devin, etc.)
**Purpose:** This file defines the system invariants, execution boundaries, and architectural rules for this repository. If you are an AI agent analyzing or modifying this codebase, you must adhere strictly to these constraints.

## 1. System Invariants & Core Philosophy

- **Assume Hostility:** The core premise of this repository is that LLMs (including yourself) are probabilistic and cannot be trusted with direct write access to critical infrastructure.
- **Never Bypass the Gate:** Do not attempt to refactor the orchestration code to call actuators directly. All critical actions MUST pass through the `DeploymentRiskGate` or the Rust MCP `stdio` broker.
- **Cryptographic Sanctity:** The Ed25519 signature binding intent, target, payload, and evidence is the sole source of truth. Do not modify the signature generation logic to bypass validation.

## 2. Environment & Execution

- **Rust Broker (`code/mcp_stdio_broker/`):**
  - Build command: `cargo build --release`
  - Test command: `cargo test`
  - *Constraint:* The broker uses `serde_jcs` for RFC 8785 JSON canonicalization. Do not replace this with standard `serde_json` serialization, as it will introduce cryptographic malleability.

- **Python Demo (`code/deployment_agent_vertical_slice/`):**
  - Dependency: Requires the `jcs` and `cryptography` packages.
  - Test command: `make test`
  - Red Team validation: `make redteam`
  - *Constraint:* The Python `canonical_json` function must use `jcs`.

## 3. Strict Anti-Patterns

If tasked with extending this repository, **DO NOT**:
1. Implement "auto-approval" mechanisms for missing receipts.
2. Store Ed25519 private keys in plaintext environment files during production simulations (use the deterministic seed only for the demo).
3. Attempt to merge the RiskGate logic into the Actuator. They must remain physically separate components.
4. Modify `RED_TEAM_PUBLICATION_REVIEW.md` to remove listed vulnerabilities unless you provide mathematical/cryptographic proof of a fix.

## 4. Interaction Protocol
If you encounter a failing test in the Rust broker related to cryptographic validation, do not mutate the test to pass. Investigate the framing and canonicalization of the JSON-RPC payload in `src/crypto.rs`.

*End of Agentic Directives.*