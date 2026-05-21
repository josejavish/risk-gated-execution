# Security Policy

## Supported Versions

Currently, this repository is maintained as a **Hardened Reference Architecture** and is considered experimental/research-grade.

| Version | Supported          |
| ------- | ------------------ |
| v1.0.x  | :white_check_mark: |
| < v1.0  | :x:                |

## Reporting a Vulnerability

**DO NOT OPEN PUBLIC ISSUES FOR SECURITY VULNERABILITIES.**

If you discover a security vulnerability within this project (particularly related to IPC boundaries, cryptographic bypasses, or kernel namespace escapes), please report it responsibly.

### How to report
1. Send an email directly to `josejavish@gmail.com`.
2. Include the word `[SECURITY]` in the subject line.
3. Provide a clear description of the vulnerability, the attack vector, and (if possible) a minimal reproducible PoC.

### Expected Response
- You will receive an initial acknowledgment within 48 hours.
- We will work with you to triage the issue and develop a mitigation strategy.
- You will be fully credited in the release notes and the `RED_TEAM_PUBLICATION_REVIEW.md` document for any validated findings.

### Scope
We are particularly interested in:
- Bypasses of the `RFC 8785` Ed25519 signature verification.
- Time-of-Check to Time-of-Use (TOCTOU) concurrency races in the Rust broker.
- Privilege escalation vectors escaping the `setuid` drop.
- Container/Namespace escapes bypassing `CLONE_NEWNET` or `CLONE_NEWIPC`.
- Resource exhaustion vectors defeating the `rlimit` enforcement.

We ask that you do not perform active DoS testing or disruptive scanning against live production infrastructure using this codebase.