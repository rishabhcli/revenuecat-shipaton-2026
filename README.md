# RevenueCat Shipaton 2026

> A native iPhone camera that measures screen/light timing, removes rolling bands live, and suppresses moiré without destroying detail.

> **Production intent:** this repository is for the complete, reliable system described below. It is not an MVP, disposable demo, or thin hackathon facade. No product name has been assigned; the hackathon title remains the repository heading until the user chooses one.

## Repository status

Implementation has not started. The repository currently contains the authoritative product and competition specifications. This README defines the production target that future code must satisfy; it does not claim that planned commands or components already exist.

| Document | Authority |
|---|---|
| [HACKATHON.md](./HACKATHON.md) | Eligibility, mandatory submission fields, judging criteria, deadlines, links |
| [WINNING_IDEA.md](./WINNING_IDEA.md) | Selected concept, hard technical core, validation, build order, demo and risk analysis |
| [README.md](./README.md) | Product contract, architecture, production and release expectations |
| [AGENTS.md](./AGENTS.md) | Binding implementation rules for every coding agent working in this repository |

If these documents disagree, preserve the external requirements in HACKATHON.md, then the product intent in WINNING_IDEA.md, and resolve the conflict explicitly in an ADR instead of guessing.

## Product contract

Ship a production-quality iOS capture instrument that diagnoses temporal banding, searches and locks a stable exposure compatible with the source, applies bounded real-time moiré suppression, exposes correction confidence, records without frame loss, protects user media, and monetizes only after proving value through RevenueCat.

### Intended users

- Creators filming displays, LED walls, projectors, dashboards, and PWM-lit rooms
- Students/teachers recording screens and events
- Technical users needing inspectable capture settings and compatibility evidence

### Canonical workflow

1. Open directly to live diagnosis
2. Estimate temporal banding and source stability from preview buffers
3. Search exposure/ISO candidates under brightness, noise, and blur constraints
4. Lock and verify correction with hysteresis/confidence
5. Detect and suppress spatial moiré conservatively in Metal
6. Record/export with thermal/frame monitoring
7. Use RevenueCat entitlement for full-quality/advanced output after free proof

### Explicit non-goals

- General cinema camera replacement
- Android or arbitrary historical-footage repair in the initial release
- Generative enhancement or cloud processing
- Medical flicker diagnosis
- Paywall before the user sees correction
- Universal device/source support

A non-goal may become part of the product only after the core release gates pass and an ADR explains why the additional surface does not weaken correctness, safety, usability, or schedule.

## Production architecture

Signed native iOS/iPadOS app with device/lens/format support matrix. Media remains on device; RevenueCat manages products/entitlements, not video. Next Gen source/video path remains independently reproducible.

### Planned component boundaries

| Area | Production responsibility |
|---|---|
| `Camera` | Session, controls, frame sampler, recorder, audio sync |
| `Analysis` | Banding metric, phase/frequency family, candidate search, confidence |
| `Metal` | Tiled moiré detector, notch suppression, compositing |
| `UI` | Live split, scopes, lock states, accessibility, permissions |
| `Purchases` | Offerings, pro entitlement, purchase/restore/offline state |
| `Export` | Quality gate, Photos/share, metadata and settings |
| `Evaluation` | Original test patterns, devices, sources, results |

Dependencies should flow from applications/adapters toward typed domain packages. Domain logic must remain testable without UI, network, cloud credentials, or third-party services. Infrastructure code may assemble components but must not become the only place where product invariants are enforced.

### Target technology foundation

- Swift 6 and SwiftUI
- AVFoundation manual capture
- Metal/Metal Performance Shaders and Accelerate/vDSP
- RevenueCat Purchases SDK/StoreKit sandbox
- XCTest, synthetic frame sequences, physical device/source matrix
- Local privacy and performance instrumentation

Technology choices are constraints, not decorations. A dependency is accepted only when its operational behavior, license, failure modes, supply-chain risk, and replacement boundary are understood.

## Non-negotiable invariants

1. Capture correction is measured on live frames, never hardcoded per demo
2. Unsupported/unstable conditions are visible and recording confidence never turns green
3. Diagnostic work drops before recorded frames
4. Moiré suppression is bounded by detail-preservation metrics
5. No frame pixels enter analytics or RevenueCat attributes
6. Free users can prove correction before purchase
7. Purchase cancellation/failure never disables the free camera
8. All performance/compatibility claims name device, lens, format, and source

Any change that can violate an invariant requires a written design review, tests demonstrating preservation under failure, and an explicit update to this README and AGENTS.md.

## Security, privacy, and safety

- On-device media, least-privilege permissions, no automatic upload
- Original/non-trademark test content in submission assets
- No health claims from flicker metrics
- No dark patterns, fake countdowns, or forced weekly subscription

Common controls required across the system:

- secrets come from an approved secret store or local ignored environment file and are never committed, rendered, or logged;
- untrusted files, prompts, provider output, repository content, and external responses are treated as data, never instructions;
- authorization is enforced at the data/action boundary, not only in the UI;
- logs, traces, fixtures, screenshots, and demo assets are scrubbed of credentials and sensitive user data;
- destructive or externally visible actions are previewable, idempotent where possible, auditable, and fail closed;
- dependency and container scanning, lockfiles, least privilege, and an incident/rollback path are release requirements.

## Reliability and operations

Production behavior includes failures, retries, restarts, partial responses, stale data, duplicate delivery, and resource exhaustion. The implementation must therefore provide:

- typed error classes and user-visible failure states rather than catch-all success fallbacks;
- bounded timeouts, cancellation, retry budgets, and backoff for every external or long-running operation;
- idempotency and reconciliation wherever the same work may be delivered twice or its external outcome may be unknown;
- structured, redacted logs; metrics for throughput, latency, error and abstention/refusal; and traces across meaningful boundaries;
- health/readiness checks that validate dependencies without mutating user data;
- documented SLOs and alerts before public production use;
- backup, restore, migration, retention, and cleanup procedures for every persistent store;
- graceful degradation that preserves truth and safety before convenience or visual effects.

## Verification strategy

Project-specific required test surfaces:

- Synthetic known-frequency/rolling-shutter frame sequences
- Physical 50/60/refresh/PWM sources across device/lens/format
- Banding reduction and second-best candidate margin
- Moiré energy versus edge/detail preservation
- Dropped frames, audio sync, thermal degradation
- RevenueCat purchase/restore/offline/cancel/judge unlock and VoiceOver UI

Every production path also needs unit tests, property or fuzz tests where state space matters, integration tests at real boundaries, end-to-end tests of the user outcome, accessibility checks, performance budgets, security regression tests, and failure-injection coverage. Mocks belong in test fixtures; the shipped runtime must not depend on a fake service or hardcoded winning example.

Evaluation datasets and fixtures are versioned, provenance-aware, and isolated from tuning when described as held out. A number may appear in the README or submission only when a committed script regenerates it from a committed manifest.

## Performance and accessibility

Performance budgets must be set before optimization and enforced in CI for supported environments. Measure latency distributions, memory, CPU/GPU, network or storage volume, cold start, cancellation, and degraded-device behavior relevant to this product. Do not replace measurements with “feels fast.”

Accessibility is a release gate, not a polish task. The production interface must include semantic structure, keyboard support, visible focus, sufficient contrast, non-color status cues, reduced-motion behavior where relevant, zoom/reflow, readable errors, and an equivalent representation for information conveyed through canvas, charts, audio, maps, camera, or animation.

## Planned repository layout

```text
/
├── README.md                 # Product and operating contract
├── AGENTS.md                 # Binding implementation rules for coding agents
├── HACKATHON.md              # External rules and submission facts
├── WINNING_IDEA.md           # Selected product/technical blueprint
├── Camera/
├── Analysis/
├── Metal/
├── UI/
├── Purchases/
├── Export/
├── Evaluation/
├── tests/                    # Unit, property, integration, E2E, resilience
├── docs/                     # ADRs, threat model, runbooks, evaluation
└── infra/                    # Reproducible deployment and environment policy
```

This is a boundary contract, not a command to create empty directories. Add a directory when it owns working code, tests, and documentation.

## Development command contract

No commands are advertised as working until the corresponding toolchain is committed. The first production scaffold must expose one documented, cross-platform command surface, preferably through a checked-in task runner or Makefile:

| Command | Required behavior |
|---|---|
| `bootstrap` | Verify tool versions, install locked dependencies, initialize only local non-secret state |
| `check` | Format check, lint, type/static analysis, schema/config validation |
| `test` | Deterministic unit and property suites |
| `test-integration` | Real boundary tests using isolated local/test dependencies |
| `test-e2e` | Supported user workflows and failure states |
| `eval` | Reproduce committed domain evaluation and metrics |
| `build` | Produce release artifacts from a clean checkout |
| `run-local` | Start the complete local system or a documented production-equivalent subset |
| `release-check` | Run all blocking gates, artifact/SBOM generation, and policy checks |

A new contributor should be able to move from a clean checkout to a verified local system without tribal knowledge.

## Environment model

- **Local:** isolated developer data, safe fixtures, no real-world side effects by default.
- **Test:** deterministic automated environment with controlled boundary services.
- **Staging:** production-shaped deployment, synthetic/de-identified data, real observability and rollback.
- **Production:** least-privilege credentials, audited configuration, SLOs, incident ownership, backups and change controls.

Configuration is typed, validated at startup, documented, and separated from secrets. Environment-specific branches or code paths are prohibited; behavior changes through validated configuration and capability boundaries.

## Release gates

1. Supported scenes meet declared banding reduction/convergence targets
2. Recording meets frame/audio/thermal budgets
3. Moiré filter passes detail-preservation thresholds
4. Unsupported cases fail honestly
5. RevenueCat entitlement and free proof flow pass sandbox/device tests
6. Privacy, accessibility, icon/screenshot/video/store or Next Gen requirements pass

Common blocking gates also include:

- clean build from a fresh checkout with locked dependencies;
- no critical/high unresolved security findings and no committed secrets;
- migration/rollback and backup/restore rehearsal where state exists;
- passing accessibility and supported-environment matrix;
- complete observability, runbook, known-limitations, privacy, and threat-model documentation;
- no placeholder copy, dead controls, fake metrics, hardcoded demo results, or production TODO paths;
- submission assets and claims generated from the same tested release commit.

## Production milestone policy

Work proceeds in complete vertical slices, but every merged slice must use the final architecture, schemas, security boundaries, telemetry, error model, tests, and documentation expected in production. A smaller completed surface is acceptable; a throwaway implementation that will be replaced later is not.

A feature is not complete when it works once. It is complete when supported inputs, invalid inputs, retries, cancellation, restart, privacy, accessibility, observability, performance, deployment, rollback, and documentation are all accounted for.

## Hackathon delivery

HACKATHON.md contains the live form links and exact requirements. WINNING_IDEA.md contains the selected demo and judging strategy. Production engineering must strengthen that submission, not create a separate demo path. The video, screenshots, hosted build, evaluation numbers, and repository documentation must all describe the same release artifact.

## Contributing

Read AGENTS.md before changing code. Keep changes narrowly scoped, add or update tests with behavior, record architecture/security decisions in ADRs, and never weaken an invariant to make a demo pass. No product name, logo, pricing claim, medical/legal claim, partner claim, or benchmark result should be invented without explicit evidence and user approval.
