# Security demonstration scope

The demonstrated controls are tool allowlisting, typed arguments, role enforcement at execution, approval before sandbox writes, idempotency, and a small deterministic input-policy check.

Bind to localhost. Public demo credentials are not suitable for public deployment. Runs belong to roles, not individual users; a reviewer key can review any known run. There is no enterprise identity or multi-tenant authorization system.

Regex catches the included examples and similar strings, not arbitrary prompt injection. Stronger boundaries come from the restricted capabilities: tools cannot execute shell commands, contact arbitrary URLs, or change real accounts. The optional model cannot add capabilities.

Checkpoints and writes are in memory. Production use requires durable storage, per-user ownership, external reviewer identities, immutable audit events, key rotation, rate limits, and isolated workers.

Browser output uses `textContent`, so user-provided HTML does not execute. Model credentials remain in server environment variables and are omitted from errors/traces. Avoid submitting secrets: task text is retained in checkpoints.
