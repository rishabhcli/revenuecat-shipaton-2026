# ADR-0002: Loopback development services and threat analysis

- **Status:** Accepted for local/test use only
- **Date:** 2026-08-09
- **Owners:** Repository maintainers

## Context and assets

`GOAL.md` section 0A requires four health-checked development services on ports 4220–4223. They expose evaluation metadata, a RevenueCat sandbox webhook test boundary, original test patterns, and artifact metadata. Assets at risk are repository files, local process ownership, synthetic evaluation results, future sandbox payloads, secrets, and the integrity of readiness evidence. Sixteen repository sessions share the host process table and loopback interface.

## Threats and required controls

| Threat | Control | Failure behavior |
|---|---|---|
| Network exposure beyond the host | Bind literal `127.0.0.1`; reject configuration with any other host | Refuse startup |
| Proxy or redirect escapes from loopback | Lifecycle and integration clients disable proxy discovery, reject redirects, and require the exact owned loopback URL | Refuse the response; never contact the redirect target |
| Collision with a sibling process | Required `lsof` preflight identifies listeners across the complete numeric block and treats any unowned PID as foreign | Refuse startup; never kill it; fail closed if ownership inspection is unavailable |
| PID reuse or forged PID file | Record service identity and command metadata; validate ownership before signaling | Refuse to signal and retain evidence |
| Broad process termination | Request authenticated self-shutdown from an identity-matched service; retain `Popen` ownership only while reconciling a just-spawned child | Report nonzero; never send a record-derived signal and never sweep |
| Path traversal or arbitrary file reads | Fixed routes, descriptor-relative no-follow reads, and descriptor-owned artifact traversal inside fixed repository roots | 404/400 with stable error code |
| Oversized or malformed webhook body | Enforced content length, content type, schema envelope, and read deadline | 413/415/400; no persistence |
| Forged webhook interpreted as RevenueCat truth | Optional bounded local bearer authentication gates the test receiver, while every receipt remains explicitly unverified as provider delivery | Refuse when authentication is absent/invalid; never promote a local receipt to provider truth |
| Partial or conflicting webhook receipt | Rewrite the bounded privacy-minimised ledger through a same-directory fsynced temporary file and atomic replacement; bind each event-id digest to its event type | Preserve the prior complete ledger or reconcile the complete replacement; reject same-ID/different-type delivery |
| Unreplayed empirical evidence shown as a result | Quarantine committed matrix bytes until a committed replay verifier exists; expose no rows, metrics, or support status | Report `quarantined_unreplayed_evidence`, never a device result |
| Secret or frame-pixel leakage | Structured allowlisted metadata only; payloads and media never enter logs or health output | Reject unsafe fields and emit redacted error metadata |
| Fake readiness | Each service checks its own route/config/storage/logging prerequisites and owned identity, not only socket acceptance | `/ready` returns non-2xx with reasons |
| Persistent test data confusion | Store only under git-ignored `.dev/`, prefix records with repository/service/test provenance | Refuse non-test mode |
| Resource exhaustion | Bounded body size, request concurrency, timeouts, and log size/retention | 429/413/503 without crash |

## Decision

Implement the services using the Python standard library, a typed fixed configuration derived from committed `ports.env`, repository-local `.dev/` state, and an explicit lifecycle controller. In addition to the complete-block integration gate, Playwright's explicit `webServer` invokes `devctl e2e-server`: it performs ownership-aware preflight, refuses any already-running owned service or foreign listener, starts and semantically health-verifies the other three services before starting the browser-facing test-pattern service on 4222, and then keeps all four under one coordinator lifecycle. The readiness URL is deliberately 4222, but it cannot turn green until the preceding services passed readiness. Startup and semantic readiness use one 30-second total budget rather than multiplying a timeout per service. Authenticated self-shutdown uses one 10-second total budget per service, including the loopback request and exit wait, and never escalates to a PID signal. `reuseExistingServer` is false; Playwright's 45-second outer/graceful bound covers the four-service 40-second worst-case cleanup plus five seconds of coordinator margin, and Make performs a second ownership-safe `devctl down` on success, failure, or cancellation. No endpoint is a production webhook, deployment, provider, or device-verification surface.

## Observability

Use newline-delimited structured JSON with stable event names, service identity, UTC timestamp, request/correlation ID, an allowlisted route identifier (or `unmatched`), duration, status, and refusal code. Never log caller-controlled paths, query strings, request bodies, signatures, credentials, or media. Logging failure is sticky for the process and makes readiness fail; a webhook receipt is not acknowledged until its required audit event has been written.

## Reversal

Replace a service only after contract tests prove the same ports, loopback binding, readiness semantics, process ownership, limits, logging redaction, and failure behavior. Delete only repository-owned `.dev/` state during rollback.
