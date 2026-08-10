# RevenueCat Shipaton 2026

> A native iPhone camera that measures screen/light timing, removes rolling bands live, and suppresses moiré without destroying detail.

> **Production intent:** this repository is for the complete, reliable system described below. It is not an MVP, disposable demo, or thin hackathon facade. No product name has been assigned; the hackathon title remains the repository heading until the user chooses one.

## Repository status

**Not in production yet.** The worktree now contains an early Tier 0 foundation: a strict Swift 6 package with portable domain/policy modules under `Sources/`, deterministic foundation tests under `Tests/`, repository-local loopback development-harness code, and verification/CI policy files. The portable package build, tests, and strict format check, plus the local harness lifecycle, have been exercised in the current worktree. Those are construction surfaces, not a signed iOS application or proof of the capture workflow.

No app target, working AVFoundation/Metal/RevenueCat provider adapters, physical-device evaluation, TestFlight/App Store distribution, production RevenueCat configuration, or production deployment is established by this foundation. A local package check or healthy loopback harness proves only that local foundation surface; it does not establish app, device, provider, release-gate, or production readiness.

Read the authoritative documents in this order:

| Document | Authority |
|---|---|
| [HACKATHON.md](./HACKATHON.md) | Eligibility, mandatory submission fields, judging criteria, deadlines, links |
| [WINNING_IDEA.md](./WINNING_IDEA.md) | Selected concept, hard technical core, validation, build order, demo and risk analysis |
| [README.md](./README.md) | Product contract, architecture, production and release expectations |
| [AGENTS.md](./AGENTS.md) | Binding implementation rules for every coding agent working in this repository |
| [GOAL.md](./GOAL.md) | Standing goal-mode contract: port isolation, production definition, tier order, ratchets, and work selection |

If these documents disagree, preserve the external requirements in HACKATHON.md, then the product intent in WINNING_IDEA.md, and resolve the conflict explicitly in an ADR instead of guessing. AGENTS.md governs how the system is built; GOAL.md governs how long work continues and in what order. Neither overrides HACKATHON.md.

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

The target is a signed native iOS/iPadOS app with a device/lens/format support matrix. Media remains on device; RevenueCat manages products/entitlements, not video. The Next Gen source/video path remains independently reproducible.

### Component boundaries

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

ADR-0001 places the portable domain and policy layer in `Sources/<Area>Domain`. Future working Apple-framework and provider adapters belong in `App/<Area>/` and depend inward on those modules. The presence of a domain module does not mean its production area is complete, and `App/` must not be created as an empty progress scaffold.

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

## Repository layout

The current foundation and future application boundary follow ADR-0001:

```text
/
├── README.md                 # Product and operating contract
├── AGENTS.md                 # Binding implementation rules for coding agents
├── GOAL.md                   # Standing execution, production, and verification contract
├── HACKATHON.md              # External rules and submission facts
├── WINNING_IDEA.md           # Selected product/technical blueprint
├── Package.swift
├── Sources/
│   ├── CaptureDomain/
│   ├── RuntimeConfiguration/
│   └── <Area>Domain/         # Camera, Analysis, Metal, UI, Purchases, Export, Evaluation
├── Tests/                    # root package/property tests; later integration and app tests
├── App/                      # future working Apple/provider adapters under App/<Area>/
│   └── <Area>/
├── adr/                      # root architecture decisions
├── docs/                     # threat models, runbooks, evaluation documentation
├── evidence/                 # regenerable verification artifacts
├── scripts/                  # repository-local development harness
└── tools/                    # verification and policy tooling
```

`Sources/`, `Tests/`, `adr/`, `docs/`, `evidence/`, `scripts/`, and `tools/` exist in the Tier 0 worktree. `App/` is intentionally future-facing until a working signed application or adapter slice exists. This is a boundary contract, not a command to create empty directories.

## Development command contract

The root `Makefile` now defines the repository's canonical, non-divergent command surface. Target existence is not a passing claim: except where the status column says otherwise, a target remains **defined but not verified by this documentation change** until its output is captured from the appropriate clean-checkout or intended-environment run.

| Command | Required behavior | Current evidence boundary |
|---|---|---|
| `make help` | List the canonical contributor-facing commands and their scopes | Exercised successfully in this worktree |
| `make bootstrap` | Verify toolchain contracts, recreate Node dependencies from the lockfile, and keep npm/browser cache and scratch under symlink-refusing `.dev/` paths | Defined; clean-checkout result not claimed here |
| `make check` | Aggregate format, lint, policy, and strict type checks | Defined; aggregate result not claimed here |
| `make build` | Compile the portable Swift package in release mode with warnings blocking | Defined; package build is not app/device evidence |
| `make test` | Run deterministic Swift and Python unit/property suites | Defined; test success is not release-gate evidence |
| `make lint` / `make format-check` | Enforce formatting, text, policy, boundary, and repository checks | Defined; result not claimed here |
| `make format` | Apply the deterministic Swift formatting contract | Defined; mutating helper, not a verification gate by itself |
| `make typecheck` | Run the strict Swift 6 debug build | Defined; package-only scope |
| `make verify-all` | Run the single canonical local verification contract, recreate the locked Node tree, hash source/index state, and inventory only allowlisted ignored outputs | Defined; a clean-checkout pass is not claimed here |
| `make dev:preflight` / `make dev:up` / `make dev:health` / `make dev:down` | Manage only the loopback services in ports 4220-4229 and verify semantic readiness | Exercised successfully in this worktree on `127.0.0.1:4220-4223` |
| `make test-integration` | Exercise all four real isolated loopback services | Defined; local harness scope only |
| `make test-e2e` | Own and health-check all four local services, then browser-test the original-pattern outcome through allocated port 4222 without reusing a listener | Defined; local harness E2E only, not an iOS app E2E test |
| `make eval` | Run the current typed compatibility-evidence policy oracle | Defined; no physical result or compatibility claim |
| `make dependency-audit` / `make sbom` | Audit locked development dependencies and generate development-harness dependency artifacts | Defined; not an iOS release SBOM |
| `make verify-clean` | Refuse dirty/staged source, then run only `verify-all` from detached `HEAD` with a 30-minute default hard deadline and process-group cleanup; a cold run installs the pinned browser inside the detached checkout | Defined; passing output not claimed here |
| `make full-verify` / `make release-check` | Alias the canonical `verify-all` contract without divergent behavior | Defined; not proof that product release gates pass |
| `make run-local` | Start the four owned loopback services and require semantic readiness | Defined; same local-only boundary as `dev:*` |

The successful local `dev:*` lifecycle establishes local harness readiness only. It does not establish a signed app, physical-device behavior, a RevenueCat provider integration, release-gate success, clean-checkout success, or production readiness.

All redirectable verification writes are repository-local: npm cache and Playwright browsers use `.dev/cache/`, temporary files use `.dev/tmp/`, and logs use `.dev/logs/`. Initialization rejects symlinked or non-directory path components before any npm or browser command. `verify-all` requires tracked, staged, and non-ignored untracked content to remain byte-stable; changing ignored build/cache output is permitted only within the explicit inventory enforced by `tools/repository_state.py`.

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
