# Talk Proposal: Risk-Gated Execution for Enterprise AI Agents

**Proposed Title:** *Agents With Write Access: Runtime Gates for Enterprise AI Systems*

**Primary Track:** AI Engineering / Platform Engineering / SRE / Security

---

## Abstract

Enterprise agents are moving from read-only assistance to write-capable
automation: deployments, refunds, ticket actions, database changes, and cloud
operations. Prompts and static IAM are not enough once a probabilistic planner
can trigger deterministic side effects.

This talk presents **Risk-Gated Execution**, a runtime pattern that places an
enforcement boundary between agent intent and critical actuators. The pattern
uses intent contracts, fresh operational evidence, target authorization,
expiry, rollback requirements, and reconstructable audit records before an
action is allowed to execute.

I will walk through a minimal benchmark comparing direct execution, static
policy, evidence-aware policy, and a risk-gated runtime across adversarial and
safe scenarios. Then I will show where the boundary belongs in real systems:
Envoy/WASM for HTTP APIs, a Rust `stdio` broker for local MCP-style tools, and
platform controls such as workload identity and egress policy for containment.

The talk is intentionally practical: what this pattern prevents, what it does
not prevent, and how to roll it out without creating an unmaintainable security
platform.

---

## Audience

- Platform engineers building internal AI platforms.
- SREs responsible for production blast radius.
- Security engineers evaluating agent tool execution.
- AI engineers integrating LLM tool calls with enterprise systems.
- Engineering leaders deciding when agents can move beyond read-only use cases.

---

## Takeaways

1. Why prompts and IAM are insufficient as the final control for write-capable agents.
2. How to structure intent contracts, evidence checks, rollback posture, and audit records.
3. Where enforcement belongs for HTTP APIs versus local `stdio` tool servers.
4. How to red-team the architecture from CTO, AI engineer, SRE, and security perspectives.
5. What must remain outside the claim: poisoned reasoning, compromised evidence providers, and operational complexity.

---

## 30-Minute Outline

**0-5 min: The New Failure Mode**

- Agents are gaining write access.
- Tool execution creates deterministic side effects.
- Prompt policy is not an execution boundary.

**5-12 min: The Risk-Gated Pattern**

- Intent contracts.
- Evidence providers.
- Risk gates.
- Gated actuators.
- Audit ledgers.

**12-18 min: Benchmark**

- Direct execution baseline.
- Static policy baseline.
- Evidence-aware baseline.
- Full gate and ablations.
- What the numbers mean and what they do not mean.

**18-24 min: Enforcement Topology & Sandboxing**

- Envoy/WASM for HTTP and service-mesh APIs.
- Rust `stdio` broker for local MCP-style tools.
- Out-of-band receipts so the LLM does not handle cryptography.
- Kernel-Level Isolation: Why authorization must be paired with Air-Gapping (`CLONE_NEWNET`), privilege dropping (`setuid`), and resource limits (`rlimit`) to form a true execution sandbox.

**24-28 min: Red Team**

- CTO/CIO: operability and MTTR.
- AI engineering: tokenization and framework integration.
- Senior software engineering: serialization and protocol fragility.
- Security: confused deputy and oracle problem.

**28-30 min: Deployment Path**

- Audit-only rollout.
- Low-regret enforcement.
- Evidence requirements.
- Action tiering.
- Platform ownership.

---

## Speaker Bio

José Javier Sánchez Hidalgo is a Chief Technical Manager of IT Infrastructure focused on
governable, reliable, and operable AI infrastructure. His work sits at the
intersection of platform engineering, SRE, security controls, and enterprise AI
systems. He is interested in moving agent safety from prompt convention into
runtime infrastructure that production teams can measure, operate, and audit.
