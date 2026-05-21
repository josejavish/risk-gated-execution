# Universal MCP Stdio Broker

A Rust enforcement boundary for MCP-style local tools that communicate over
`stdio`.

The broker wraps a child tool process, intercepts line-delimited JSON-RPC
`tools/call` messages, verifies a signed execution receipt, and only forwards
approved calls to the child process. It is a prototype for the local IPC
boundary described in the Risk-Gated Execution article.

## Features

- **Asynchronous Interception:** Uses `tokio` to intercept JSON-RPC messages over `stdio` in real-time.
- **Receipt Binding:** Verifies Ed25519 signatures over intent ID, action, target, payload, evidence digest, and timestamp.
- **Dynamic Policy:** Enforces authorized targets, allowed actions, forbidden actions, and optional receipt TTL from a hot-reloaded policy file.
- **OOM Protection:** Uses `tokio_util::codec::FramedRead` with a strict 10MB limit on inbound and child-output JSON-RPC lines.
- **Elite OS Isolation:** The child process is air-gapped from the network (`CLONE_NEWNET`), isolated from IPC/UTS namespaces, stripped of root privileges (`setuid`), restricted by strict `rlimit` boundaries, and linked to a kernel suicide pact (`PDEATHSIG`) to prevent zombie leaks.
- **Autonomous Control Loop:** Uses `notify` and `arc-swap` to hot-reload Kubernetes ConfigMap policy changes (RCU Epochs) in microseconds without restarting the broker or dropping connections.
- **API Tiering Hook:** Blocks obvious destructive transactional payloads without `dry_run: true` and returns `Suspend` for non-transactional side effects that lack human quorum fields.

## Security Model

The broker protects the transition from semantic tool intent to local tool
execution. It does not prove that the model's reasoning was correct.

Assumptions:

- the agent runner launches tools through this broker;
- the child tool cannot be reached through another path;
- the receipt public key is provisioned by trusted configuration;
- the JSON-RPC protocol is line-delimited JSON;
- the signed payload is serialized deterministically.

Production requirements outside this architecture:

- RFC 8785 canonical JSON or typed protobuf/gRPC for signature stability;
- seccomp, cgroups, and workload identity for stronger process containment;
- Cilium/eBPF or equivalent egress controls for network containment;
- trustworthy evidence pipelines and signed telemetry;
- operational dashboards and break-glass procedures.

## Performance

The cryptographic and serialization overhead of this broker is rigorously benchmarked.

- **Direct IPC Latency (P95):** ~24 µs
- **Broker IPC Latency (P95):** ~138 µs
- **Total Security Overhead:** **~114 µs**

The fixture shows that a local broker can add sub-millisecond overhead in a
simple IPC loop. Treat these numbers as local benchmark data, not a universal
production latency claim.

## Quick Start

### Build Locally
```bash
make build
```

### Run Unit Tests (Cryptographic Proofs)
```bash
make test
```

### Run IPC Benchmark
```bash
make bench
```

### Run End-to-End Orchestrator Pipeline
Executes the `orchestrator_middleware.py` which interfaces with the LLM, fetches the Ed25519 signature out-of-band, and passes it through the Rust broker successfully.
```bash
make run
```

The bundled demo policy sets `evidence_ttl_seconds` to `0` so the checked-in
receipt fixture remains replayable. Production policies should use a short
positive TTL, for example 30 seconds.

### Docker Deployment
Build the production container:
```bash
make docker-build
```

Run the container (listening on stdin):
```bash
make docker-run
```
*(Pass JSON-RPC payloads to stdin to see the broker in action).*
 in action).*
