# Risk-Gated Execution for Agentic Systems

An architectural pattern and Rust IPC broker to move LLM agent safety from probabilistic prompt policies to deterministic runtime enforcement.

> **Status: Architectural Prototype.** This repository demonstrates the core concepts of out-of-band cryptographic receipts and IPC authorization boundaries for LLM agents. It is intended for research, platform engineering design, and red-team review, not as a drop-in production binary.

## The Problem
Enterprise AI agents are moving from recommending actions to executing them. Most current agent frameworks rely on instructions ("do not delete the database") or static IAM roles. Both are insufficient for critical write operations. Safe enterprise agents require a runtime execution boundary that evaluates intent against dynamic, real-time evidence (service health, change windows, human approvals) *before* the payload reaches the actuator.

## The Architecture
This repository implements the **Risk-Gated Execution** pattern:
1. **The Intent:** The LLM generates an intent.
2. **The RiskGate (Python):** A middleware that evaluates the intent against a policy and dynamic evidence, emitting a cryptographically signed receipt (using RFC 8785 JSON Canonicalization).
3. **The Broker (Rust):** An out-of-process `stdio` interceptor that wraps the execution tool. It verifies the Ed25519 signature, the TTL, and the authorization policy before allowing the payload to pass.

## Repository Structure

- `code/deployment_agent_vertical_slice/`: A complete Python demo of a deployment agent integrating the RiskGate. Includes a red-team suite demonstrating mitigated attacks.
- `code/mcp_stdio_broker/`: The Rust broker that intercepts local tool execution via `stdio` and enforces the cryptographic receipts.
- `ARTICLE_DRAFT.md`: The full thesis on why software fails and cryptography is required for agent safety.
- `RED_TEAM_PUBLICATION_REVIEW.md`: The security and architectural audit of this implementation, explicitly listing mitigated attacks and remaining out-of-scope vulnerabilities.

## Quick Start (Demo)

You need Rust (`cargo`) and Python 3 installed.

```bash
cd code/deployment_agent_vertical_slice
make demo
```

To run the adversarial red-team suite (which tests expired receipts, tampered payloads, unauthorized targets, etc.):

```bash
make redteam
```

## Integrating with OpenAI / Agent Frameworks
The RiskGate is designed to reduce adoption friction. It exports a standard OpenAI Tool JSON schema, allowing you to inject it as middleware into existing orchestrators like LangChain or the OpenAI SDK.

## Authors & Review
Designed by Jose Javier. 
Read the `RED_TEAM_PUBLICATION_REVIEW.md` for a candid assessment of the architecture's current limits.

## License

This project is dual-licensed under either the [MIT License](LICENSE-MIT) or the [Apache License, Version 2.0](LICENSE-APACHE), at your option. This is the standard licensing model for the Rust ecosystem, designed to provide maximum freedom for individual developers while offering explicit patent protections for enterprise adoption.
