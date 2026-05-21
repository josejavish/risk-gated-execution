# Risk-Gated Execution for Agentic Systems

*Moving safety from prompt policy to runtime enforcement*

*By José Javier Sánchez Hidalgo, Chief Technical Manager of IT Infrastructure*

Enterprise AI agents are crossing a line that traditional automation rarely crossed: they are moving from recommending actions to executing them. The moment an agent can call a deployment API, rotate a secret, issue a refund, change a firewall rule, or write to a production database, "the model was instructed not to do that" stops being an acceptable control.

This is not primarily a model-alignment problem. It is an infrastructure problem.

The core claim of this work is simple:

> Critical agentic actions should not reach actuators directly. They should pass through a runtime gate that validates intent, evidence, authorization, expiry, rollback posture, and auditability before execution.

I call this pattern **Risk-Gated Execution**.

The goal is not to replace IAM, policy-as-code, guardrails, approval workflows, or model-level defenses. The goal is to add the missing enforcement boundary between probabilistic planning and deterministic side effects.

---

## The Failure Mode

Most agent stacks still treat tool execution as a local implementation detail:

1. The LLM decides what tool to call.
2. The orchestration framework serializes a tool payload.
3. The tool server or API receives the call.
4. The action executes if the credentials are valid.

That is acceptable for low-impact read operations. It is not acceptable for critical writes.

There are three reasons.

First, prompts are not a security boundary. They influence model behavior, but they do not enforce execution. A prompt can be ignored, overridden, misinterpreted, or indirectly poisoned by untrusted context.

Second, static permissions are too coarse. IAM can say that a workload is allowed to deploy to a service, but it usually does not know whether this specific deployment has fresh health evidence, is inside a change window, has a rollback plan, or contradicts live incident state.

Third, many agent tools sit outside the network path. HTTP APIs can be intercepted by gateways and service meshes, but MCP-style local tools often communicate over `stdio`. A sidecar proxy will not see a local JSON-RPC call between an agent runner and a tool process.

The uncomfortable conclusion is that safe enterprise agents need a runtime execution boundary, not just better instructions.

---

## The Runtime Pattern

Risk-Gated Execution introduces five components.

**Intent Contract**

The agent or orchestration layer emits a structured statement of what it intends to do: action, target, risk level, expiry, payload, required evidence, and rollback posture.

**Evidence Provider**

The gate collects or receives operational evidence: service health, incident state, change-window status, approvals, dependency saturation, policy epoch, or other environment-specific facts.

**Risk Gate**

The gate evaluates the intent against policy and evidence. It checks target authorization, expiry, evidence freshness, contradictory state, rollback requirements, and known unsafe payload patterns.

**Gated Actuator**

The actuator refuses direct calls. It only executes actions that carry a valid gate decision or cryptographic receipt.

**Audit Ledger**

Each decision emits a reconstructable record linking intent, evidence, decision reason, target, execution outcome, and trace ID.

This pattern is intentionally close to infrastructure primitives SRE and platform teams already understand: admission control, service-mesh enforcement, deployment gates, policy engines, and audit receipts. The difference is that the policy decision is tied to an agentic intent and dynamic evidence at execution time.

---

## Minimal Benchmark

I built a small benchmark to test whether this pattern adds measurable value over direct execution and stronger baselines.

The benchmark uses 12 scenarios and four execution modes:

- **Direct execution:** the action reaches the actuator if the payload is structurally valid.
- **Static policy:** target authorization, wildcard destructive actions, and rollback requirements.
- **Evidence-aware policy:** static policy plus evidence presence and intent expiry.
- **Risk-gated runtime:** evidence presence, freshness, semantic contradiction checks, expiry, rollback, target authorization, and audit records.

The current generated run uses 100 iterations per scenario.

Key results:

- Direct execution allowed `700/700` unsafe actions.
- Static policy still allowed `400/700` unsafe actions.
- Evidence-aware policy still allowed `200/700` unsafe actions.
- Risk-gated execution allowed `0/700` unsafe actions.
- Risk-gated execution produced `0` false-positive blocks on safe scenarios in this fixture.
- The average gate decision time was about `9.31 ms`; P95 was about `15.16 ms`.
- The audit reconstructability score was `1.0` when the ledger was enabled and `0.0` when ablated.

The important part is not the absolute number. This is a synthetic benchmark, not an enterprise production trace. The useful result is the ablation shape: freshness checks, expiry checks, rollback requirements, target authorization, and audit records each contribute independently. Removing them makes specific unsafe scenarios pass.

That is the kind of result a platform team can reason about.

I then turned the pattern into a single vertical slice: a deployment agent for
`payment-service`. It includes a signed evidence provider, a RiskGate that
issues receipts only when health/change-window/rollback checks pass, a Rust
`stdio` broker that verifies the receipt, and a red-team suite covering missing
receipts, tampered payloads, stale evidence, expired receipts, unauthorized
targets, incident freeze, missing rollback, and the explicit poisoned-context
limitation.

---

## Making the Boundary Real

A Python benchmark proves the decision logic. It does not prove an enforcement boundary.

The next step was to move from "library in the agent process" to infrastructure.

### HTTP And Service-Mesh APIs

For network APIs, the natural enforcement point is the data plane: gateway, sidecar, service mesh, or admission controller.

I prototyped an Envoy/WASM direction in Rust:

- intercept the request before it reaches the actuator;
- extract the intent or receipt;
- verify an Ed25519 signature;
- reject unauthenticated or stale execution attempts;
- emit a decision trace.

The reason to use Envoy/WASM rather than eBPF for this part is practical. Intent contracts are L7 payloads. They require JSON parsing, policy context, and cryptographic verification. That belongs in a user-space L7 proxy, not in a kernel program.

### Local MCP And `stdio` Tools

Network enforcement still misses local tool execution.

Many MCP-style tools are spawned as local processes and communicate over standard input/output. A network proxy never sees that traffic. This is the `stdio` blind spot.

To address that, I built a Rust `stdio` broker:

- the agent runner spawns the broker instead of spawning the tool directly;
- the broker wraps the child process;
- JSON-RPC `tools/call` messages are intercepted before reaching the tool;
- receipts are verified with Ed25519;
- policy is hot-reloaded through an RCU-style `ArcSwap` snapshot;
- input and child-output frames are bounded with `tokio_util::codec::LinesCodec` to avoid unbounded buffer OOM;
- blocked calls return JSON-RPC errors instead of reaching the actuator.
- the child process is violently sandboxed using Linux Namespaces (`CLONE_NEWNET`, `CLONE_NEWIPC`), strict resource limits (`rlimit`), privilege dropping (`setuid`), and OS-enforced termination (`PDEATHSIG`).

The local broker is no longer just a boundary for tool-call authorization; it is a full cryptographic and kernel-level execution sandbox.

---

## Red Team Review

A useful architecture should survive more than one perspective.

### CTO / CIO View

The business objection is operational complexity.

Custom Rust brokers, Envoy filters, policy compilers, Cilium egress policies, and cryptographic receipts can easily become a bespoke platform that only one team understands. If it increases MTTR during an incident, the security gain may not justify the operational risk.

The design response is productization:

- shadow-mode profiling before enforcement;
- generated policies rather than hand-written YAML wherever possible;
- human-readable block reasons;
- clear break-glass paths;
- gradual rollout by action tier;
- observability that maps low-level blocks to business actions.

Security has to be operable at 03:00. Otherwise teams will bypass it.

### AI Engineer View

The AI engineering objection is that LLMs should not handle cryptographic material.

Expecting a model to copy a base64 Ed25519 signature into a tool payload is brittle and wastes context. It also fights existing frameworks that expect tool calls to be semantic, not cryptographic.

The design response is out-of-band receipt handling. The LLM should express intent. The runner or orchestration middleware should negotiate the receipt with the gate and attach it invisibly to the network request or IPC frame.

The model should not "speak crypto". The runtime should.

### Senior Software Engineer View

The software objection is protocol and serialization fragility.

JSON-RPC framing can change. Streaming can appear. JSON canonicalization across languages can fail. A broker that assumes too much about payload shape can become a fragile L7 parser.

The design response is to keep the architecture explicit about its assumptions:

- line-delimited JSON-RPC only;
- deterministic JSON serialization for the fixture;
- RFC 8785 canonical JSON or typed protobuf/gRPC required for production;
- exact action and target binding in the signed receipt;
- tests for tampered payloads, action mismatch, unauthorized targets, expired receipts, malformed signatures, and destructive payloads.

The boundary is only as strong as the bytes it signs.

### Security Engineer View

The security objection is that execution gating does not solve poisoned reasoning.

If a malicious document convinces the agent to produce a valid destructive intent, a runtime gate may still approve it if the evidence and policy match. That is the confused-deputy problem.

The design response is scope discipline. Risk-Gated Execution secures the transition from intent to action. It does not prove that the intent was ethically or semantically correct.

To reduce that gap, future systems need provenance controls: trust labels on context, source-aware tool policies, taint propagation into action payloads, and model/runtime support for explaining which inputs influenced a critical output.

That is a separate layer. It should not be hidden inside claims about the gate.

---

## Deployment Model

I would roll this out in tiers.

**Tier 0: Observe**

Run in audit-only mode. Collect intended actions, targets, evidence dependencies, latency, block candidates, and incident correlation.

**Tier 1: Enforce Low-Regret Blocks**

Block expired intents, missing receipts, unauthorized targets, wildcard destructive payloads, and actions during incident freezes.

**Tier 2: Require Evidence**

Require fresh operational evidence for higher-risk actions: service health, change window, rollback availability, and explicit approvals.

**Tier 3: Split By Action Semantics**

Transactional actions can use dry-runs, shadow state, or state diffs. Non-transactional side effects such as email, refunds, and external API calls need suspension, queues, human quorum, or compensating workflows.

**Tier 4: Move Enforcement Into The Platform**

Use Envoy/WASM for HTTP, local brokers for `stdio`, workload identity for agents and tools, and egress policy for network containment.

The production value is not one mechanism. It is the control plane that makes the mechanisms consistent and operable.

---

## What This Does Not Solve

Risk-Gated Execution does not solve:

- compromised evidence providers;
- prompt injection inside untrusted context;
- all possible tool protocol changes;
- arbitrary local privilege escalation;
- non-transactional side effects without a suspension model;
- governance quality if the underlying policy is wrong;
- business acceptance if the platform creates too much friction.

Those limitations are not footnotes. They are the next engineering agenda.

The oracle problem requires trustworthy evidence pipelines, signed telemetry, attestation, or independent verification. Reasoning provenance requires source-aware context and better runtime support. Operational adoption requires product thinking, not only security engineering.

---

## Why This Matters

The enterprise path for agents will not be "give every model a powerful token and hope the prompt is good." That path fails operationally, legally, and commercially.

The path is closer to how infrastructure teams already run production systems:

- explicit contracts;
- runtime gates;
- least privilege;
- fresh evidence;
- bounded side effects;
- auditability;
- incident reconstruction;
- progressive rollout.

Agentic AI does not remove the need for infrastructure discipline. It increases it.

The useful frontier is not only smarter agents. It is agents whose actions are governed by systems that senior platform, security, SRE, and business leaders can trust under pressure.

That is the work.
