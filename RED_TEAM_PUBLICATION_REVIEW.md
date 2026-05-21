# Security & Architecture Audit: Risk-Gated Execution

**Date:** 2026-05-21  
**Target:** Risk-Gated Execution Architecture & Rust IPC Broker  
**Auditor:** José Javier Sánchez Hidalgo ([ORCID: 0009-0007-3062-3574](https://orcid.org/0009-0007-3062-3574))

## Executive Summary

This document serves as the formal architectural and security audit for the Risk-Gated Execution pattern. The architecture successfully shifts the security boundary for autonomous LLM agents from probabilistic prompt guardrails to deterministic, kernel-level and cryptographic runtime enforcement. 

The implementation achieves severe isolation between the untrusted agent reasoning environment and the host execution environment, satisfying requirements for highly sensitive enterprise deployments (e.g., Financial Services, SRE Automation).

## 1. Cryptographic Intent Boundary

**Status:** Secured & Hardened.

- **Payload Canonicalization:** Upgraded to strict RFC 8785 (JSON Canonicalization Scheme) in both Python (RiskGate) and Rust (Broker) to prevent serialization mutation and parsing ambiguity attacks.
- **Out-of-Band Validation:** The LLM actuator never handles the cryptographic receipt. The receipt is negotiated and attached transparently by the orchestration middleware, preserving agent prompt context and preventing signature manipulation.
- **Pinning:** The vertical slice explicitly pins the trusted Evidence Provider public key. Self-signed or unauthenticated evidence envelopes are deterministically rejected.

## 2. Concurrency & State Management

**Status:** Secured & Hardened.

- **Replay Attack Prevention:** A bounded LRU/BTreeMap Idempotency Cache (`nonce_cache`) enforces strict single-execution guarantees per `intent_id`.
- **TOCTOU Elimination:** A Time-of-Check to Time-of-Use (TOCTOU) concurrency vulnerability was sealed using a Two-Phase Commit / Optimistic Locking strategy. Concurrent replay attacks are blocked at the exact nanosecond of ingestion.
- **Memory Exhaustion (OOM DoS):** The Idempotency Cache is bounded and prunes expired nonces in $O(\log N)$ time, guaranteeing a constant memory footprint regardless of transaction volume.

## 3. Kernel-Level Isolation (Linux Namespaces)

**Status:** Secured & Hardened.

- **Fail-Closed Isolation:** The broker strictly requires `CAP_SYS_ADMIN` to construct isolated Linux namespaces. If namespace creation fails, the broker hard-crashes (`std::process::exit(1)`) rather than degrading into a fail-open execution state.
- **Network Isolation:** The untrusted LLM actuator is spawned inside an isolated Network Namespace (`CLONE_NEWNET`), preventing network access from the child process and mitigating data exfiltration via reverse shells or malicious API calls.
- **Privilege Abdication (Confused Deputy):** The broker explicitly drops root privileges (`setuid`/`setgid`) inside the `pre_exec` hook. The child actuator never inherits `root` permissions.
- **Environment Scrubbing:** All environment variables are purged (`env_clear()`) before spawning the child process, preventing the leak of infrastructure credentials (e.g., `AWS_ACCESS_KEY_ID`).

## 4. Process Lifecycle & Resource Limits

**Status:** Secured & Hardened.

- **Zombie Process Elimination:** Configured the Linux kernel with `prctl(PR_SET_PDEATHSIG, SIGKILL)`. If the security broker is killed (e.g., OOM Killer, SIGTERM), the untrusted LLM actuator is guaranteed to die instantly.
- **Fork Bomb Prevention:** Resource exhaustion attacks initiated by a compromised LLM are blocked by enforcing strict `rlimit` constraints (max 100 processes, max 2GB RAM) at the OS kernel boundary prior to actuator spawn.
- **Async I/O Resilience:** Tokio asynchronous I/O operations are strictly handled without `unwrap()`. Broken pipes from a crashing child actuator will not cause the parent broker to panic, preventing DoS.

## 5. Residual Risks & Future Work

While the execution boundary is secure, organizations deploying this pattern must account for the following upstream and downstream risks:

1. **Reasoning Provenance:** Execution gating does not solve prompt injection. A poisoned document can still cause the agent to produce a valid, albeit destructive, intent. This architecture secures the *intent-to-action* boundary, but ensuring the intent is ethically correct requires upstream provenance tracking and taint analysis.
2. **Evidence Provider Integrity:** The security of the RiskGate relies entirely on the integrity of the external Evidence Providers (e.g., PagerDuty, Datadog). Compromised evidence systems can emit valid signatures for false states. Production deployments require independent attestation for all evidence sources.
3. **Production Telemetry:** While the Rust broker emits structured `tracing` logs suitable for OpenTelemetry, a full production deployment requires an operator-facing dashboard to correlate low-level IPC blocks with high-level business intents.
