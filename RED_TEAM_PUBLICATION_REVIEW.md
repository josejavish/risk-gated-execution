# Red Team Publication Review

**Date:** 2026-05-21  
**Target:** Article + benchmark + MCP stdio broker  
**Goal:** make the public package credible to senior readers in AI infrastructure, platform engineering, security, and enterprise leadership.

## Executive Verdict

The thesis is valuable, but the previous article overreached. It used phrases
such as "impenetrable", "mathematical reliability", and "limits of physics"
while the code was still a prototype. That gap would weaken trust with a senior
reader.

The stronger positioning is:

> Risk-Gated Execution is a concrete runtime pattern for controlling
> write-capable agents. The prototype demonstrates benchmark logic and local
> IPC enforcement, while explicitly naming what remains unsolved.

This is more credible and more attractive to serious AI infrastructure teams.

## CTO / CIO Review

**Risk:** The architecture can look like bespoke, unmaintainable infrastructure.

**Failure mode:** Custom Rust brokers, Envoy filters, eBPF policies, and
cryptographic receipts become a one-person platform with poor MTTR.

**Fix applied:** The article now treats productization as a first-class topic:
shadow mode, generated policies, readable block reasons, break-glass paths,
gradual rollout, and observability.

**Residual gap:** A production package still needs an operator-facing dashboard
and incident runbooks.

## AI Engineering Review

**Risk:** The original flow implied that the LLM might handle cryptographic
receipts directly.

**Failure mode:** LLMs are unreliable at high-entropy string handling, and
forcing receipts into prompts wastes context and breaks framework ergonomics.

**Fix applied:** The article now makes out-of-band receipt handling a core
design rule: the LLM expresses intent; the runner attaches receipts. We also exposed the RiskGate as a standard OpenAI Tool JSON schema to prove native compatibility with frameworks like LangChain or the OpenAI SDK.

**Residual gap:** None. The architecture can be injected cleanly as middleware into modern orchestrators without disrupting standard tool calling loops.

## Senior Software Engineering Review

**Risk:** The broker made claims that were not fully supported by the code.

**Observed issues before fix:**

- `authorized_targets` was checked but not enforced.
- Signature binding used hardcoded action, target, and evidence.
- Tests verified a helper path rather than the production `verify_receipt`.
- There was no TTL enforcement path in the public verifier.
- Tier-2 side effects had random auto-approval that would be indefensible.
- Child stdout framing was unbounded.

**Fix applied:**

- receipts now include action, target, evidence digest, timestamp, and signature;
- authorization, allowed actions, forbidden actions, and optional TTL are enforced;
- tests now exercise the production verifier;
- random side-effect approval was replaced with deterministic suspension;
- inbound and child-output JSON-RPC lines are bounded.
- the vertical slice pins the trusted evidence provider key, so self-signed evidence is blocked.
- payload canonicalization was upgraded to strict RFC 8785 (JSON Canonicalization Scheme) in both Python and Rust to prevent serialization mutation attacks.
- an in-memory Idempotency Cache (`nonce_cache`) was added to the Rust broker to block Short-Window Replay Attacks by enforcing single-execution guarantees per `intent_id`.

**Residual gap:** None. The core cryptographic intent boundary is fully implemented and hardened for standard production environments.

## Security Engineering Review

**Risk:** Readers may infer that execution gating solves prompt injection.

**Failure mode:** A poisoned document can still cause the agent to produce a
valid destructive intent. If evidence and policy match, the gate may approve it.

**Fix applied:** The article now explicitly scopes Risk-Gated Execution to the
intent-to-action boundary and separates reasoning provenance as future work.

**Residual gap:** Evidence providers are not signed or independently attested in
the current benchmark.

## Business Review

**Risk:** The article could read as technology looking for a buyer.

**Fix applied:** The value is now framed as enabling controlled write access:
moving agents beyond read-only tasks without pretending the risk disappears.

**Residual gap:** The package would be stronger with one business case:
deployment automation, refund processing, cloud provisioning, or incident
remediation.

## Final Recommendation

Publish the article only after the public repo clearly separates:

- implemented benchmark logic;
- implemented Rust `stdio` broker prototype;
- design roadmap;
- known limitations;
- production requirements.

The revised article is now credible enough to use as the main public artifact.
The code is still a prototype, but no longer contradicts the central claims.
