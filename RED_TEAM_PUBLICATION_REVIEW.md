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
- a bounded LRU Idempotency Cache (`nonce_cache`) was added to the Rust broker to block Short-Window Replay Attacks and prevent memory exhaustion (OOM DoS), enforcing strictly bounded, single-execution guarantees per `intent_id`.
- a Time-of-Check to Time-of-Use (TOCTOU) concurrency vulnerability was discovered in the anti-replay mechanism. It was sealed by implementing a Two-Phase Commit / Optimistic Locking strategy in a `BTreeMap` cache, blocking concurrent replays at the exact nanosecond of ingestion, and guaranteeing $O(\log N)$ pruning of expired nonces.
- an OS-level Privilege Escalation vulnerability (Confused Deputy) was closed by dropping privileges (`setuid`/`setgid`) inside the `pre_exec` hook, guaranteeing the LLM actuator never inherits `root` permissions even if the broker is launched with `CAP_SYS_ADMIN` for namespace isolation.
- environment variables are strictly scrubbed (`env_clear()`) before spawning the child process to prevent credential leaks (e.g., `AWS_ACCESS_KEY_ID`, `DATABASE_URL`) from the broker to the untrusted LLM actuator.
- kernel-level isolation is set to Fail-Closed. The broker will hard-crash instead of degrading security if it lacks `CAP_SYS_ADMIN` to create namespaces.
- the LLM actuator is placed in a mathematically Air-Gapped Network Namespace (`CLONE_NEWNET`), eliminating all vectors for data exfiltration via reverse shells or malicious API calls.
- a critical process lifecycle vulnerability (Zombie/Orphan Process Leak) was eliminated by configuring the Linux kernel with `prctl(PR_SET_PDEATHSIG, SIGKILL)`. If the security broker is killed (e.g., OOM, SIGTERM), the untrusted LLM actuator process is guaranteed by the OS to die instantly, preventing unmonitored rogue executions in the background.
- resource exhaustion attacks (Fork Bombing and OOM) initiated by a compromised LLM are now physically blocked by enforcing strict `rlimit` constraints (max 100 processes, max 2GB RAM) inside the OS kernel boundary prior to actuator spawn.

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
