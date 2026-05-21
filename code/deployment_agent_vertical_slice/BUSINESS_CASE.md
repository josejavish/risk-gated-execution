# Business Case: Controlled Deployment Agents

## Situation

Enterprises want AI agents to move beyond read-only tasks. Deployment automation
is a natural target: agents can summarize incidents, propose changes, roll out
patches, and reduce operational toil.

The blocker is blast radius. A write-capable agent can deploy during an incident,
act on stale health data, target the wrong service, or execute without rollback.

## Risk

Without a runtime gate, the final control is usually a mix of prompt policy,
framework validation, and static credentials. That is weak for production writes:

- prompts influence behavior but do not enforce execution;
- IAM may authorize the agent broadly;
- tool payloads can be modified after planning;
- logs may not explain why the action was allowed.

## Control

Risk-Gated Execution adds a decision point before the deployment tool:

- signed operational evidence;
- pinned evidence-provider identity;
- explicit intent contract;
- target and action authorization;
- change-window and incident-freeze checks;
- rollback evidence;
- signed receipt bound to payload;
- broker-side verification before local tool execution.

## Business Value

The value is not "perfect AI safety." The value is controlled write access.

This lets a platform team move agents from advisory workflows toward bounded
production operations while preserving auditability and rollback discipline.

## Rollout Plan

1. **Audit-only:** observe proposed deployment intents and evidence needs.
2. **Low-regret blocks:** reject missing receipts, expired receipts, unauthorized targets, and incident freezes.
3. **Evidence enforcement:** require fresh health, change-window, and rollback evidence.
4. **Action tiering:** keep destructive or non-transactional actions behind human approval.
5. **Platform integration:** move keys, evidence, broker policy, and logs into managed infrastructure.

## Executive Summary

This pattern gives CTO/CIO/SRE/security stakeholders a concrete way to say:

> Agents may deploy only when operational evidence, policy, rollback, and auditability agree at runtime.

That is a more useful enterprise claim than "the model was instructed to be careful."
