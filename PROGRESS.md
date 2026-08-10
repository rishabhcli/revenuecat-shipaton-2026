# Progress Journal

This file is append-only. Each entry records delivered behavior, exact verification commands, regenerable evidence, risks, rollback, blockers, and the next item selected by `GOAL.md` section 10.1.

## 2026-08-10T05:27:00Z — Tier 0 executable contract and isolated development surfaces

### Behavior delivered

- Added a strict Swift 6 package with framework-neutral typed contracts for runtime configuration and the Camera, Analysis, Metal, Purchases, Export, Evaluation, and UI ownership areas. The types encode live-frame provenance, non-green unsupported confidence, record-first backpressure, bounded detail loss, analytics-safe attributes, free proof before paywall, purchase-failure camera preservation, and four-axis compatibility evidence.
- Added 25 deterministic XCTest methods with 20,992 declared property iterations, 40 Python repository/dev-contract tests, and four Playwright browser tests.
- Added the exclusive `127.0.0.1:4220-4223` lifecycle with semantic readiness, exact PID ownership, foreign-listener refusal, bounded rotating logs, truthful empty states, authenticated/idempotent sandbox webhook handling, and original generated test patterns.
- Added the canonical Make command surface, pinned npm/Playwright dependency graph, SHA-pinned least-privilege CI workflow, dependency register, development SBOM command, ADRs, support/assumption/blocker registers, MIT license, and clean-checkout verifier.
- Installed the Xcode Metal Toolchain component required by the approved technical direction. This changed the machine toolchain only; no product result is inferred from installation.
- Synchronized authoritative documentation so it no longer says implementation has not started and explicitly says the repository is not yet in production.

### Commands and observed evidence

- `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcodebuild -downloadComponent MetalToolchain` — installed Metal Toolchain build `27A5228f`; `xcrun --find metal` resolved inside Xcode.
- `make bootstrap` — Swift 6.4, Xcode 27 beta, Metal toolchain, Node 26.5.1, npm 11.17.0 and lock consistency passed; npm reported zero known vulnerabilities at the configured audit threshold.
- `make dev:preflight && make dev:up && make dev:health` — all four owned services passed semantic readiness on ports 4220-4223; readiness explicitly reports local scope and `production_verified=false`.
- `make test` — 6 repository-tool tests, 34 dev-contract tests, and 25 Swift tests passed; Swift property methods declare 20,992 deterministic iterations.
- `make test-integration` — all four real loopback surfaces passed; absent evaluation data remained `not_yet_available`; invalid flicker frequency returned the stable 400 refusal; unconfigured webhook authentication failed closed with 503.
- `make test-e2e` — Playwright-managed Chromium 151 from the pinned Playwright graph ran four tests; all passed, including non-production readiness and calibration-limit copy.
- `make build`, `make typecheck`, `make eval`, `make dependency-audit`, `make sbom`, `make lint`, `actionlint .github/workflows/verify.yml`, and `git diff --check` passed with their declared foundation-only scopes.
- `make verify-all` — passed from the current working tree and proved generated status stability plus ownership-scoped service cleanup. Exact ignored log: `.dev/logs/verify-all-working.txt`. This is working-tree evidence only and is not represented as clean-checkout or CI evidence.
- Final `make dev:health` — green after restarting the standing services.

### Current truth, risk, migration, and rollback

- The local executable/domain/dev-harness foundation is working. No signed iOS application, AVFoundation capture, Metal correction pipeline, RevenueCat provider integration, physical-device evaluation, TestFlight/App Store artifact, real-user usage, release-gate pass, or production deployment exists yet.
- The current local Xcode is 27 beta while CI targets the stable `macos-26` runner. Cross-toolchain clean-checkout CI remains unverified until the first pushed run is green.
- No persistent product schema or user data was introduced. Local state is isolated under ignored `.dev/` and contains synthetic/test metadata only.
- Rollback is `make dev:down` followed by reverting the coherent foundation commit; it signals only ownership-validated PIDs and requires no data migration.
- Active blockers: none for Tier 0. Hardware/provider/release gates are not misclassified as achieved.

### Next item selected by GOAL.md section 10.1

- Tier 0 is not exited until the exact committed revision passes `make verify-all` from a detached clean checkout and the SHA-pinned GitHub Actions workflow produces a green run URL. Commit the reviewed foundation, execute `make verify-clean`, archive its regenerable evidence, push the branch, and verify CI before selecting Tier 1.

## 2026-08-10T08:54:00Z — Hostile-review correction and fail-closed Tier 0 hardening

### Correction to the preceding entry

- The preceding entry's counts and broad invariant-enforcement description were an intermediate working-tree observation, not release evidence. Independent hostile review subsequently found forgeable live evidence, entitlement, free-proof, moire/export approval, and compatibility-claim construction; duplicated rather than distinct property inputs; unsafe local lifecycle/log/evidence boundaries; and canonical verification paths that could false-green. Its figures of 25 Swift tests, 20,992 declared property iterations, 40 Python tests, and four Playwright tests are superseded by the results below.
- Tier 1 has **not** exited. I1-I8 now have stronger type encodings and property attacks, but none yet has the required component-failure injection or production alert/runbook, and current boundary behavior remains portable-foundation behavior rather than a real AVFoundation, Metal, RevenueCat, or shipped-UI adapter.

### Behavior delivered

- Made live frames, measured correction, provider entitlement, free proof, bounded moire approval, authorized export, purchase attributes, and performance claims issuable only through package-owned validated paths. Artifact/session identities are structural, numeric and Unicode inputs are bounded, mark-only compatibility labels refuse, and evaluation claims retain four-axis plus manifest provenance.
- Replaced record-derived PID signaling with authenticated self-shutdown, descriptor-safe PID reads, proxy-disabled/redirect-refusing exact-loopback requests, fail-closed `lsof` ownership inspection, sanitized child environments, and an all-four-service Playwright coordinator that refuses reuse and has a 45-second bounded cleanup allowance.
- Made local observability bounded and fail-closed: logs rotate at 1 MiB with exactly three backups, request logs use allowlisted route IDs rather than caller paths, logger failure latches readiness unhealthy, and a webhook receipt is not acknowledged before its privacy-minimised audit event is persisted.
- Replaced the append webhook receipt file with an exact-schema, bounded, fsynced, atomic snapshot. Duplicate IDs are payload-bound; partial writes, file/directory fsync failure, restart reconciliation, malformed snapshots, and conflicting replay are refusal-tested.
- Quarantined any committed evaluation matrix until a committed replay verifier exists. The dashboard exposes zero empirical rows, statuses, or metrics for unreplayed bytes, so arbitrary committed JSON cannot become a compatibility claim. Artifact inventory now traverses only retained no-follow directory descriptors and refuses swap races, symlinks, non-regular entries, and traversal/file limits.
- Hardened the canonical gate to reinstall from `package-lock.json`, keep all writable caches under a symlink-refusing repository namespace, enforce the exact Swift dependency graph/import allowlist, hash the index plus tracked/untracked content before and after verification, inventory only allowlisted ignored artifacts under explicit resource limits, and bound detached clean-check process groups plus independent service cleanup.

### Commands and observed evidence

- `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer xcrun swift-format lint --recursive --strict Sources Tests/FoundationPropertyTests Package.swift` and strict release build passed after the Swift hostile-review fixes.
- `python3 -m unittest discover -s Tests/python -p 'test_*.py' -v` — 70/70 dev-contract tests passed, including proxy/redirect/PID binding, log refusal/redaction, atomic-ledger failure/restart, evaluation quarantine, artifact swap, invalid token, and missing-`lsof` attacks.
- `make --no-print-directory test-tools` — 24/24 repository policy/state/clean-check tests passed.
- `make verify-all` — passed from the hardened working tree: lock-derived npm install and zero-vulnerability audit; strict format/lint/policy/typecheck/release build; 24 tool tests; 70 dev tests; 52 XCTest methods; all-four-service integration; five Playwright tests; evaluation policy; dependency audit; SBOM; content/index stability; and authenticated service cleanup. The ignored working log is `.dev/logs/verify-all-hardening-working.txt`; it is explicitly not clean-checkout or CI evidence.
- The 21 named Swift property methods now declare 60,019 genuinely distinct cases. Independent external-client review confirmed package-only issuers cannot be called by an ordinary consumer, and a final read-only hostile re-audit reported no remaining P1/P2 in the reviewed Tier 0 Swift or local-service surfaces.
- `make dev:preflight && make dev:up && make dev:health` — restored the standing gate after canonical cleanup; all four owned services again returned identity-bound semantic readiness on 4220-4223.

### Current truth, risk, migration, and rollback

- The executable foundation and local harness are green from the current working tree only. Detached clean-checkout evidence and GitHub Actions evidence for an exact committed revision are still pending, so Tier 0 has not exited.
- No signed iOS target, real capture or correction adapter, provider SDK integration, physical evaluation cell, supported device/source combination, TestFlight/App Store artifact, or production deployment exists. The repository remains not in production.
- The webhook snapshot migration deliberately refuses the obsolete isolated `.dev/tmp/revenuecat-webhook-receipts.jsonl`; that synthetic local-only file was removed before the hardened service restart. No product or user data was migrated.
- Rollback remains ownership-safe `make dev:down` followed by reverting the foundation commit. A failed authenticated shutdown retains PID/worktree evidence rather than escalating to an unchecked signal.

### Next item selected by GOAL.md section 10.1

- The lowest failing release gate is still Tier 0 clean/CI evidence. Stage and review the exact 60-file foundation, commit it, run `make verify-clean` against committed `HEAD`, commit the regenerable evidence, push the branch, and require the SHA-pinned workflow to pass before starting the Tier 1 I2 fail-closed live-correction boundary.
