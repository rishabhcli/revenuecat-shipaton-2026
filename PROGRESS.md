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

## 2026-08-10T10:19:19Z — Detached clean-check identity failure and bounded repair

### Failure observed without a false green

- The first `make verify-clean` run against foundation commit `ee83f823120995a7370102a69bf4de2685815c91` correctly exited non-zero during detached `dev:preflight`. The detached worktree's generated basename was not the repository identity required by `devctl`, which returned `[repository_mismatch]` rather than starting services under ambiguous ownership.
- The failed detached worktree was removed by the existing bounded cleanup path, `git worktree list` returned only the source checkout, the failed `evidence/tier0/verify-all-clean.txt` was deleted rather than archived as success evidence, and `make dev:preflight && make dev:up && make dev:health` restored all four standing services.

### Repair and verification

- Changed clean-check allocation to create a unique private container while preserving the exact child basename `revenuecat-shipaton-2026`. Allocation is relative to a held `O_DIRECTORY | O_NOFOLLOW` parent descriptor, refuses symlinked or identity-swapped parents, verifies the bound and lexical container identities, and removes failed allocation remnants through the held descriptor.
- A detached shutdown failure or failed/raised `git worktree remove` now retains the worktree and available PID/diagnostic evidence without pathname deletion or pruning. The unique container is removed only after the child worktree is safely absent.
- `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer make test-tools` passed 28/28 tests, including exact-basename uniqueness, parent symlink refusal, live parent-swap refusal, bounded process termination, authenticated detached cleanup, and worktree-removal failure retention. `make policy-check`, `python3 tools/check_text.py`, `actionlint .github/workflows/verify.yml`, `python3 -m py_compile tools/verify_clean_checkout.py tools/tests/test_contract_tools.py`, and `git diff --check` passed.
- Independent hostile re-review reported no remaining P1/P2 in the repair. No detached clean-check success or CI success is claimed by this entry.

### Current truth and next item selected by GOAL.md section 10.1

- The repository remains not in production, and Tier 0 remains open because detached clean and GitHub Actions evidence are still absent. Commit this bounded repair, rerun `make verify-clean` against that committed revision, restore the standing services, archive only a successful evidence artifact, then push and require the exact SHA-pinned workflow revision to pass.

## 2026-08-10T11:14:04Z — Cold clean-check deadline calibration

### Failure observed and cleanup verified

- `make verify-clean` against commit `6e12491c65d549fee187910ebd038968dd39172a` preserved repository identity and progressed through bootstrap, the owned four-service lifecycle, strict lint/typecheck/release build, 29 repository-tool tests, 70 dev-contract tests, 52 Swift tests, and all-four integration. The cold Swift stages reported 82.86, 50.55, and 454.46 seconds; the run then reached the pinned 178.7 MiB Chromium installation and truthfully exited 124 at the declared 1,200-second harness deadline rather than overrunning or reporting success.
- Process-group termination and the independent authenticated service cleanup succeeded. `git worktree list` showed only the source checkout, the failed evidence file contained `harness_timeout_seconds=1200` and `exit_code=124` and was deleted rather than archived, and the standing `make dev:preflight && make dev:up && make dev:health` gate was restored green.

### Bounded calibration implemented

- Increased the detached clean default deadline from 1,200 to 1,800 seconds based on the observed cold path, while retaining the parser's 1,800-second maximum. Increased the GitHub Actions job envelope from 25 to 40 minutes and bounded the canonical verification step itself at 35 minutes, reserving five minutes for failure-log upload and runner cleanup.
- Documented that `make verify-clean` has a 30-minute default and cold-installs the pinned browser inside the detached checkout. Added contract assertions that 1,800 is the direct-tool/default Make value, 1,801 is refused, and CI retains the larger bounded envelopes.
- `make test-tools` passed 29/29 tests. `make policy-check`, `python3 tools/check_text.py`, `actionlint .github/workflows/verify.yml`, Python bytecode compilation, `git diff --check`, and semantic `dev:health` passed. Independent timing review found the 30-minute local and 40-minute CI bounds sufficient without an unmeasured further expansion.

### Current truth and next item selected by GOAL.md section 10.1

- No detached clean pass or CI pass is claimed. The repository is still not in production and Tier 0 remains open. Commit this measured deadline calibration, rerun the cold detached gate, restore the standing services, and archive evidence only if the complete canonical contract exits zero.
- Count correction for the first bullet of this entry: the timed-out `6e12491` run executed 28 repository-tool tests; the 29th timeout-contract test was added and passed afterward as part of the calibration change.

## 2026-08-10T14:09:29Z — Loaded-host lifecycle deadline repair

### Failures observed without unsafe fallback

- The 1,800-second `make verify-clean` run against commit `736dc8f5997932bbb401f96cf6c0c8ec97c43477` passed bootstrap, the initial four-service gate, strict debug/release builds, 29 tool tests, 70 dev-contract tests, 52 Swift tests, and all-four integration setup. A second integration startup then truthfully exited 2 because evaluation and artifact readiness had not become available inside the prior shared 10-second startup budget. The harness did not time out, did not false-green, authenticated cleanup succeeded, `git worktree list` returned only the source checkout, and the failed evidence artifact was deleted.
- While exercising the startup repair, the first ownership-safe `devctl down` stopped three services but refused success when test-patterns had not exited inside the prior five-second post-request wait. It never sent an unchecked PID signal. Immediate inspection found no listener and an exited process; a second ownership-validated `devctl down` reconciled only that same PID record.

### Bounded lifecycle behavior delivered

- Set one explicit 30-second total startup/readiness budget for canonical Make and the direct controller default. Playwright's coordinator uses one decreasing 30-second budget across all four services, still verifies the three non-browser services before spawning port 4222, and retains its separate 45-second outer bound.
- Set authenticated self-shutdown to one 10-second total per-service budget that includes the loopback request and remaining exit wait. Retained child cleanup passes only the remaining time to `Popen.wait`; the four-service coordinator worst case remains 40 seconds inside Playwright's 45-second graceful bound. Detached cleanup has an independent 50-second process bound and still retains worktree/PID evidence on failure.
- Added fake-clock tests proving E2E budgets decrease across services and cross the old 10-second boundary without multiplying the timeout, a loaded owned process may exit after five but before ten seconds without signalling, retained-child wait receives only the remaining deadline, CLI defaults and all six canonical Make calls use 30 seconds, and the 40-second complete-block bound fits both outer cleanup envelopes.

### Commands and current truth

- `make test-tools` passed 29/29; `make test-python` passed 73/73; `make lint`, Python bytecode compilation, `make test-integration`, and `make test-e2e` passed. Playwright ran all five browser tests in the ownership-scoped lifecycle. `python3 tools/check_text.py`, `make policy-check`, `actionlint .github/workflows/verify.yml`, `git diff --check`, and semantic `dev:health` passed.
- This remains local harness evidence only. No clean-check success, CI success, signed iOS target, device/provider evidence, or production state is claimed.

### Next item selected by GOAL.md section 10.1

- Commit the measured lifecycle repair, rerun `make verify-clean` from the exact clean revision, restore the standing services, and archive evidence only if every canonical stage and cleanup exits zero; then push and verify the exact SHA-pinned workflow run.

## 2026-08-10T15:29:05Z — Repository-wide progress audit and next-agent handoff

### How to read this snapshot

- This entry audits committed `main` at `ade5bbcb8c211dc57764781e9486e638c87e0423`. It does not replace the append-only history above; where an older entry says clean verification or CI was pending, the current evidence below supersedes that status.
- Progress is reported by the `GOAL.md` ladder and release gates, not by an invented percentage. The end goal requires a signed app, real camera/provider/device evidence, production cutover, and continuously ratcheted verification; none of those may be inferred from portable package or loopback-harness success.
- **Current classification: not in production; Tier 0 remains open.** The Tier 0 implementation is substantial and the exact commit passes the canonical contract from a local detached clean checkout, but the same commit's required GitHub Actions run is red.
- Product name remains unassigned. Do not create one. No active external blocker is recorded in `BLOCKED.md`.

### Evidence observed in this audit

- `make dev:preflight && make dev:up && make dev:health` passed on the source checkout. The four identity-bound local services were ready on `127.0.0.1:4220-4223`; this is local harness evidence only.
- `make verify-clean` passed against the exact clean source commit `ade5bbcb8c211dc57764781e9486e638c87e0423` in 58.42 seconds on the local Apple-silicon host. Its detached `make verify-all` run passed strict format/policy/type/build checks, 29 repository-tool tests, 84 local-service contract tests, 52 Swift XCTest methods, all-four-service integration, five Playwright tests, the typed evaluation-policy oracle, dependency audit, development SBOM generation, repository-state stability, and ownership-safe cleanup.
- The 52 Swift methods include 21 named property attacks declaring 60,019 distinct cases. These counts describe the portable foundation tests; they are not physical camera, GPU, provider, accessibility, performance, or release evidence.
- GitHub Actions run [31402791964](https://github.com/rishabhcli/revenuecat-shipaton-2026/actions/runs/31402791964) for the same commit failed. Bootstrap and locked dependency installation passed, then `dev:up` exhausted its single 30-second total deadline with stable code `up_timeout`; cleanup reported that three authenticated self-shutdown endpoints were unavailable and correctly sent no PID signals. The failure was truthful and fail-closed, but it means the clean CI requirement is not green.
- The successful local clean artifact generated during this audit was not added to this documentation-only commit. Regenerate and commit release evidence only after the CI failure is repaired and the exact replacement commit passes both local clean verification and CI.

### Progress against the ladder

| Tier | State | What the repository proves now | What prevents exit |
|---|---|---|---|
| **0 — executable contract** | **In progress; current priority** | Strict Swift 6 package; pinned Node/Playwright graph; canonical Make commands; SHA-pinned CI; isolated four-service harness; policy, dependency, ADR, assumption, blocker, support, and evidence registers; detached clean verifier. Local clean `verify-all` passes. | Exact-commit GitHub Actions verification is red. No green CI URL or committed clean/CI evidence exists. |
| **1 — domain invariants** | **Partial portable encodings only** | All eight invariants have typed policy foundations and property attacks listed below. | No real adapter boundary, component-failure injection, production alert, or runbook exists for any invariant; therefore Tier 1 has not exited. |
| **2 — hard technical core** | **Not started** | Only policy/data contracts exist. | No AVFoundation capture, signal extraction, exposure search/lock, Accelerate/vDSP analysis, Metal detector/filter, recorder, RevenueCat adapter, or real export. The physical kill test has not run. |
| **3 — adapters/trust boundaries** | **Local-harness subset only** | Loopback services have typed config, bounded requests, fail-closed readiness, structured logs, webhook idempotency, and an ADR threat model. | No Apple-framework, RevenueCat SDK, Photos, media-file, or device adapter exists; no provider contract fixture corpus exists. |
| **4 — first vertical slice** | **Not started** | Original browser test patterns exercise only the development surface. | There is no signed app or end-to-end camera user outcome. Browser E2E is explicitly not app E2E. |
| **5 — refusal/abstention** | **Domain-policy partial** | Closed refusal states exist for correction, moiré, export, configuration, evidence, and local services. | The designed visuals/copy and failure behavior have not been exercised in a SwiftUI app, on device, or through real providers. |
| **6 — ownership-area build-out** | **Not started as production surfaces** | Each area has a portable domain module. | A module's existence is not area completion; every real Camera, Analysis, Metal, UI, Purchases, Export, and Evaluation surface is absent. |
| **7 — verification lattice** | **Foundation subset** | Unit/property, local integration, browser E2E, policy/security, and dependency checks cover the current foundation. | No app/device/provider contract and E2E tests, physical evaluation, VoiceOver audit, frame/thermal profiling, mutation report, or release coverage exists. |
| **8 — regenerable evaluation** | **Policy only** | Typed claims require four-axis context and immutable-manifest/run provenance; unreplayed dashboard data is quarantined. | `evidence/` contains only its README. There are no immutable frame manifests, correctness oracles, physical results, baselines, or publishable numbers. |
| **9 — performance/resilience** | **Harness deadlines only** | Local service time/size/concurrency/log limits and cleanup paths are tested. | No capture frame, audio-sync, GPU, memory, thermal, bundle, or sustained-recording budget has been measured. |
| **10 — security/privacy/supply chain** | **Foundation subset** | Internal-only Swift graph, dependency register, locked development graph, secret checks, loopback threat model, and development SBOM command exist. | No shipped-app threat model, privacy/runtime media audit, RevenueCat boundary review, iOS release SBOM, signing, or authorization matrix exists. |
| **11 — operational readiness** | **Local harness only** | Semantic local readiness and bounded redacted logs exist. | No staging/production environment, SLO/dashboard/alert/runbook set, rollback drill, emergency disable, support surface, or applicable restore drill exists. |
| **12 — production/real usage** | **Not started** | Nothing in the repository establishes production. | No TestFlight external tester, App Store submission, CI-built tagged deployment, production RevenueCat configuration, soak, real user, incident drill, dependency upgrade, or rollback exercise. |
| **13 — submission** | **Concept and draft only** | The concept, award strategy, draft Devpost identifiers, form requirements, build order, and demo storyboard are documented. | No product name, app icon, screenshot, public two-minute device video, try-it-out/release URL, judge unlock, final claims/evidence audit, or final submission. |

### Domain-invariant coverage and exact remaining boundary

| Invariant | Portable encoding and tests already present | Missing production proof |
|---|---|---|
| **I1 — correction comes from live frames** | `CameraDomain/LiveFrameEvidence.swift` uses package-issued session/source/frame provenance; `AnalysisDomain/CorrectionAssessment.swift` issues verified correction only from chronological one-to-one live evidence. `CameraAdmissionPropertyTests` and `CorrectionConfidencePropertyTests` attack provenance, ordering, evidence count, session/source, algorithm, and numeric failures. | No AVFoundation adapter issues frames, no live luma/banding measurement exists, and no component-failure injection, runtime boundary assertion, alert, or runbook proves hardcoded demo values cannot enter. |
| **I2 — unsupported/unstable is never green** | `SourceCondition`, `CorrectionConfidence`, and `UIDomain/CorrectionIndicator` make verified, caution, and refusal states distinct; property tests cover all declared unsupported reasons and unstable measurement pairs. | No SwiftUI rendering, actual camera-source classification, accessibility/device screenshot, loss-of-lock path, fault injection, alert, or runbook. |
| **I3 — diagnostics drop before recorded frames** | `CaptureAdmissionPolicy` admits recorded frames first; arithmetic and 32,768-case priority attacks pass. | No capture callback, recorder queue, audio path, backpressure instrumentation, diagnostic cancellation, or dropped-frame device test. |
| **I4 — moiré suppression preserves detail** | `DetailPreservationLimits`, package-issued measurements, `BoundedSuppression`, export artifact matching, and 6,561-case policy attacks refuse missing/exceeded metrics. | No tiled detector, FFT/notch Metal kernel, real-edge metric, calibrated threshold, GPU frame budget, or physical detail-preservation evidence. |
| **I5 — no pixels in analytics/RevenueCat attributes** | `OperationalEvent` and `PurchaseAttributeSnapshot` are closed scalar-only types; package dependency/import policy keeps frame/provider types out of portable telemetry boundaries. | No real analytics or RevenueCat serialization adapter, compile-time app-boundary enforcement, runtime payload audit, or privacy test against captured buffers. |
| **I6 — free proof before purchase** | `VerifiedFreeProof`, `PaywallPresentationPolicy`, and proof-preview export authorization require a verified correction before a locked user's paywall may present; tests cover unverified/unstable/refused paths. | No live preview/proof clip, UI navigation, RevenueCat offering, output-quality implementation, or on-device paywall ordering test. |
| **I7 — purchase failure preserves free camera** | `EntitlementPolicy` has no unavailable free-camera state and preserves previous verified access through cancellation/failure; purchase/export state-transition tests pass. | No RevenueCat/StoreKit adapter, restore/offline/refund/expiry reconciliation, sandbox/device state matrix, or user-visible provider failure flow. |
| **I8 — claims name device/lens/format/source** | `CompatibilityContext`, typed metric/unit pairs, immutable-manifest/run provenance, Unicode-bounded labels, and evaluation tests require all four axes; the local dashboard withholds unreplayed empirical rows. | No committed replay verifier, immutable evaluation corpus, device/source matrix row, physical result, publication pipeline, or support claim. |

### Ownership-area handoff

| Area | Keep/reuse | Build next; do not mistake the left column for completion |
|---|---|---|
| **Camera** | Issued session/source/frame identities, chronological windows, record-first admission policy. | Signed iOS target, permissions, `AVCaptureSession`, device/lens/format enumeration, manual exposure/ISO/focus/WB, bounded frame sampler, recorder and audio sync. |
| **Analysis** | Normalized banding evidence, thresholds, refusal/confidence types, live-evidence assessment. | Linear-luma row extraction, detrending/windowing, vDSP frequency/phase estimation, 50/60/100/120/PWM families, candidate scoring, settling, hysteresis, uncertainty, and convergence instrumentation. |
| **Metal** | Detail-preservation limits and authorization token. | Offline oracle first, then tiled spectral detector, conservative orientation-aware notch suppression, overlap-add, edge/text protection, temporal smoothing, and measured GPU budget. Do not start this before the temporal kill test succeeds. |
| **UI** | Framework-neutral status shape/text and paywall-order policy. | SwiftUI camera-first experience, live split, sync action, scopes, permissions and all designed states; VoiceOver, non-color cues, reduced motion, Dynamic Type/reflow, focus, and contrast. |
| **Purchases** | Canonical `pro_capture` entitlement policy and failure-preserving access state. | RevenueCat SDK adapter, remote offerings, anonymous identity, purchase/restore/offline/expiry/refund, sandbox fixtures, judge unlock, and provider observability without media attributes. |
| **Export** | Privacy disposition and entitlement/detail-bound authorization. | `AVAssetWriter` or approved recorder integration, quality gate, Photos/share, settings metadata, cancellation/recovery, storage pressure, frame/audio/thermal accounting. |
| **Evaluation** | Four-axis evidence schema, typed units, provenance issuer, original browser pattern generator, quarantine behavior. | Synthetic known-frequency rolling-shutter sequences, immutable manifests, deterministic oracle/baselines, committed replay verifier, physical device/source rig, held-out results, and support-matrix publication. |

### Release-gate status

| Gate | Status | Evidence required before green |
|---|---|---|
| **G1 banding reduction/convergence** | Red — no algorithm or physical measurement. | Regenerable per-device/lens/format/source results meeting declared thresholds. |
| **G2 recording frame/audio/thermal budgets** | Red — no recorder. | Sustained device recordings with exact frame accounting, audio offset, thermal state, and declared envelope. |
| **G3 moiré detail preservation** | Red — policy only. | Real filter output versus deterministic/physical edge and interference oracles within threshold. |
| **G4 unsupported cases fail honestly** | Red — typed policy exists, app path absent. | App/device E2E for unsupported, unstable, low-light, uncalibrated, drift, and recovery states, never falsely green. |
| **G5 RevenueCat/free-proof flow** | Red — provider absent. | Sandbox and device tests for offering, purchase, cancel, failure, restore, offline, expiry/refund, judge unlock, and free-camera continuity. |
| **G6 privacy/accessibility/submission** | Red — foundation only. | Shipped-app privacy audit, accessibility matrix, icon/screenshot/video/source disclosures, support surface, and store or confirmed Next Gen path. |

### Documentation and claim-drift notes

- `HACKATHON.md` is the external-requirements dossier, `WINNING_IDEA.md` selects the concept, `README.md` defines the product contract, `AGENTS.md` defines implementation discipline, and `GOAL.md` defines work order. This journal is the current evidence/status source; do not copy its provisional status backward into external rules or product requirements.
- `HACKATHON.md` still contains the originally captured unchecked item “Decide the project concept,” while `WINNING_IDEA.md` clearly records a selected concept. Treat this as checklist drift, not permission to revisit the concept or invent a product name.
- The deadline/countdown and live Devpost/Next Gen facts in the dossier were captured on August 9. Re-verify external rules before submission decisions; do not silently update them from memory.
- `SUPPORT_MATRIX.md` is truthfully empty. Do not add a row until physical, regenerable evidence names device, OS, lens, format, source, algorithm/calibration, metrics, command, manifest, seed, timestamp, and release commit.
- `evidence/` has no product evidence beyond its policy README. Local logs under ignored `.dev/` are observations, not committed release evidence.

### Risks, migration, rollback, and blockers

- The immediate risk is environment-sensitive lifecycle behavior: local clean verification is green, but the identical commit times out starting services on the `macos-26` CI runner. Blindly raising deadlines would hide the failure mode; broad PID signalling remains prohibited.
- The repository has no product persistence or user-media migration. The local webhook ledger is synthetic/test-only under ignored `.dev/`; it is not RevenueCat provider truth.
- This handoff changes documentation only. Rollback is a revert of this single append-only journal commit; no runtime or data rollback is required.
- No active external blocker is recorded. Hardware, signing, provider, and real-user needs become blockers only when they are the first physically impossible action and no safe parallel work exists.

### Next item selected by `GOAL.md` section 10.1

1. **Keep Tier 0 as the only current priority.** Reproduce and diagnose GitHub Actions run `31402791964` without weakening the one-budget lifecycle contract or introducing unchecked process termination. Preserve per-service startup and shutdown diagnostics on CI failure so the exact unavailable phase is observable.
2. Add a regression that models the discovered CI startup failure, then make startup/readiness succeed within a measured explicit budget or document an evidence-based replacement budget of equal or greater safety. Do not multiply a timeout per service and do not report socket acceptance as readiness.
3. Run the targeted lifecycle tests, `make test-integration`, `make test-e2e`, `make verify-clean`, and restore `make dev:health`. Commit regenerable clean evidence only for the replacement commit that passes.
4. Push and require the exact replacement SHA's GitHub Actions verification to be green; record its run URL and artifact. Only then may Tier 0 exit.
5. After Tier 0 is green, resume the lowest incomplete Tier 1 work, beginning with the I2 fail-closed live-correction boundary because preventing a false green protects the user from the highest-impact wrong result. Add its real boundary assertion, component-failure attack, structured operational event, production alert contract, and runbook before moving to the physical Tier 2 camera-control kill test.

## 2026-08-10T19:45:00Z — Observable lifecycle failure diagnostics and a bounded loopback bind

### Why this was the selected item

- `GOAL.md` section 10.1 item 2 selects the failing release gate. Tier 0 cannot exit while the exact-commit GitHub Actions verification is red, and the previous handoff selected "reproduce and diagnose run 31402791964 ... preserve per-service startup and shutdown diagnostics on CI failure so the exact unavailable phase is observable" as the first step.
- The CI failure was truthful but opaque. `dev:up failed [up_timeout]` named no phase and no service; `dev:down` then reported three unavailable shutdown endpoints with no state for the fourth. Only `.dev/logs/verify-all.log` was archived, so every per-service log died with the runner. No further diagnosis was possible from committed evidence.

### Behavior delivered

- `scripts/devctl.py` gained `LifecycleTrace`, an observation-only recorder that never changes control flow, never extends a deadline, and is never the reason an operation reports success. It records phase start/elapsed/status, the last readiness detail per service, and the retained `Popen` child of each spawned service.
- `command_up`, `command_health`, `command_down`, and `command_e2e_server` now record their phases (`controller-lock-acquired`, `preflight`, `reconcile`, `spawn:<service>`, `readiness`, `stop:<service>`, `cleanup-started`, `cleanup-finished`). `wait_for_health` and `wait_for_record_health` publish each observed readiness detail into the trace instead of discarding it on timeout.
- On any `up`/`down`/`health`/`e2e-server` failure the CLI prints a bounded `diagnostic:` block to stderr after the original failure line: every phase with its elapsed seconds and status, then per service its record presence, PID, port, liveness, ownership proof, listener ownership, retained-child exit status, and last readiness detail. The block runs under its own independent 10-second deadline and reports `diagnostic:incomplete` rather than masking, replacing, or downgrading the original failure.
- A bounded 4 KiB / 12-line / 512-character-per-line tail of a service log is printed only for services that were not healthy on every observed signal, and every occurrence of that service's instance token is structurally replaced with `[redacted]` before printing. The partial first line of a truncated tail is dropped rather than shown as a record.
- `scripts/dev_service.py` emits `local_service_binding` before the socket is bound, so a startup stall is now observable as a phase that began and never completed rather than as silence.
- `BoundedThreadingHTTPServer.server_bind` no longer inherits `http.server.HTTPServer.server_bind`. That inherited implementation calls `socket.getfqdn` between `bind` and `listen`: an unbounded resolver call placed directly in the startup path of a loopback-only service. A slow or unreachable resolver leaves the socket bound but never listening, which the controller can only observe as a live process refusing connections. The override binds through `socketserver.TCPServer.server_bind` and uses the literal bind host as the server identity. This is a bounded-boundary defect fixed on its own merits; **no claim is made that it is the cause of the CI failure.**
- `.github/workflows/verify.yml` archives `.dev/logs/verify-all.log`, `.dev/logs/*.log`, and the rotated `.dev/logs/*.log.[1-3]` on every result, so per-service logs survive the runner. `tools/check_policy.py` now parses the archive block scalar with `workflow_archive_paths` and refuses any archived path outside `.dev/logs/`, which is strictly stronger than the previous single-literal check.
- `README.md` documents the diagnostic block, the two service startup events, and the CI log archive.

### Commands run and evidence

- `make test-python` passed 93/93 (up from 92) and `make test-tools` passed 31/31 (up from 29). New tests: the `up` timeout names the consuming phase and reports the services that were never spawned; a live process with no listener is distinguished from an exited one; a healthy service contributes no log tail; the tail is bounded and never reveals the instance token; a crashed retained child reports `child=exited(2)`; diagnostics report their own failure instead of masking it; every diagnosed command emits diagnostics; bind performs no reverse-DNS lookup and still listens; the bind event is logged before construction; CI archives the service logs; and the archive-path parser reads every block-scalar entry.
- The reverse-DNS guard was proven load-bearing by confirming that a stock `http.server.ThreadingHTTPServer` raises when `socket.getfqdn` is patched to fail during bind, while the repository server binds and accepts a real loopback connection.
- The diagnostic block was exercised against a real failure: one owned service was stopped through its authenticated shutdown endpoint and `devctl health --timeout 2` reported `phase name=readiness ... status=failed` plus `name=artifacts record=present pid=78178 alive=no ownership=process-exited listener=absent readiness="process exited"` with the matching 202 shutdown record in its log tail. The service was then restored by `make dev:up`.
- `make lint`, `make test-integration`, `make test-e2e` (five Playwright tests), and `make verify-all` all passed locally; `verify-all` reported `tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped`. `make dev:preflight && make dev:up && make dev:health` was restored green afterwards.

### What is now true that was not true before

- A lifecycle failure in this repository names the phase that consumed the deadline and the exact per-service state at failure, on the local host and on CI, and the per-service logs that explain it are archived rather than discarded.
- The loopback services no longer perform any name resolution between binding and listening.

### What is still not true

- No clean-checkout CI pass is claimed. This change makes the next CI failure diagnosable; it does not by itself prove the failure is fixed. The repository remains not in production and Tier 0 remains open.

### Next item selected by `GOAL.md` section 10.1

- Push this commit and read the exact SHA-pinned GitHub Actions run for it. If it is green, archive the regenerable clean/CI evidence and Tier 0 may exit. If it is red, the new `diagnostic:` block and archived service logs identify the failing phase and service directly; repair that specific cause without weakening the one-budget lifecycle contract and without any unchecked process termination.

## 2026-08-10T20:30:00Z — Diagnosed and repaired the real CI startup failure

### What the new diagnostics proved

- GitHub Actions run [31427302701](https://github.com/rishabhcli/revenuecat-shipaton-2026/actions/runs/31427302701) for commit `94cdac1` moved the failure and named its cause. `dev:up` now completed on the `macos-26` runner in **1.28 seconds** (20:05:46.22 to 20:05:47.50) where the identical step previously exhausted its full 30-second budget. That is consistent with the removal of the `socket.getfqdn` call from `server_bind`, though the previous runs carry no phase evidence, so this is an observation about the new run and not a retrospective proof about the old one.
- The run then failed later, inside `make test-e2e`, and the archived `diagnostic:` block stated the cause exactly: `diagnostic:log name=evaluation record={"error":"[Errno 48] Address already in use","event":"local_service_start_failed"}` at 20:07:07.995, eleven seconds after that service had answered `devctl_shutdown` with 202 at 20:06:56.486. The service line read `name=evaluation record=absent pid=none alive=unknown ownership=unknown listener=not-applicable child=exited(2) readiness="process ownership could not be proven"`.

### Two real defects this identified

1. **A correct shutdown produced a false "port already held" startup failure.** `BoundedThreadingHTTPServer` set `allow_reuse_address = False`. The controller's readiness and shutdown clients send `Connection: close`, so the service is the active closer and its own loopback address is left in TIME_WAIT. `verify-all` runs `test-integration` and then `test-e2e`, which restarts the same services on the same allocated ports inside that window, and the second bind was refused. It passed locally only because the interval between the two stages happened to be longer.
2. **An exited child was waited on until the deadline instead of failing by cause.** A child that exits without being reaped still answers signal 0, so `wait_for_record_health` saw a live PID whose `ps` command line no longer matched and reported `process ownership could not be proven` for the full budget, hiding `exit status 2` behind a timeout.

### Behavior delivered

- `BoundedThreadingHTTPServer` now sets `allow_reuse_address = True` and explicitly keeps `allow_reuse_port = False`. This was verified empirically on this platform before it was adopted, not assumed: with `SO_REUSEADDR` set on both sockets, a second live listener on the identical loopback address is still refused with `EADDRINUSE`, while a rebind over the service's own TIME_WAIT residue succeeds; without it that rebind is refused. Port ownership therefore still fails closed, and it remains additionally guarded by `dev:preflight` listener refusal, PID-record ownership proof, and the instance-token digest in every readiness response.
- `_refuse_exited_child` makes `wait_for_health` and `wait_for_record_health` raise the stable code `service_exited` immediately when a retained child has exited, naming the exit status and the log file that records the cause. `command_up` passes the children it spawned and `command_e2e_server` passes the child it is waiting on.

### Commands run and evidence

- `make test-python` passed 97/97 (up from 93) and `make test-tools` passed 31/31. New tests: address reuse never admits a second live listener and never enables `SO_REUSEPORT`; a service closed exactly as `Connection: close` closes it can restart on the same port; an exited child fails with `service_exited` naming status and log file without consuming any of the deadline, through both waiters; and a running or absent child never short-circuits a readiness wait.
- The suite was run three times back to back, inside the TIME_WAIT window, to prove it is no longer order- or timing-dependent. The three socket-level bind tests were moved to reserved unallocated port 4226 so they cannot collide with the fixtures that deliberately model a non-reusing foreign listener on 4227-4229.
- `make lint`, `make test-integration` immediately followed by `make test-e2e` (the exact sequence that failed on CI, five Playwright tests passing), and `make verify-all` all passed locally, with `tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped`.

### What is now true that was not true before

- The harness can restart an owned service on its allocated port immediately after a correct shutdown, and a service that cannot start reports its exit status and log location at once instead of after a 30-second timeout.

### What is still not true

- No clean-checkout CI pass is claimed yet. Tier 0 remains open and the repository remains not in production.

### Next item selected by `GOAL.md` section 10.1

- Push this repair and read the exact SHA-pinned GitHub Actions run. Only a green run for the exact committed revision, together with a `make verify-clean` pass for that same revision, allows Tier 0 to exit and its evidence to be archived.

## 2026-08-10T20:35:00Z — Tier 0 gate reached: both clean-checkout gates green for one exact commit

### Evidence

- `make verify-clean` passed for commit `e1e420727b12d2b182cf6a20f014d9e61afc6de1` in 2 minutes 30 seconds on the local Apple-silicon host and wrote `evidence/tier0/verify-all-clean.txt`, which records `source_commit`, `source_precondition=clean`, `command=make verify-all`, `timeout_seconds=1800`, the complete detached output, and `exit_code=0`.
- GitHub Actions run [31428035078](https://github.com/rishabhcli/revenuecat-shipaton-2026/actions/runs/31428035078) for the **same commit** concluded `success`, ending in `verify-all:ok dependency-install=lock-derived tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped`. This is the first green hosted verification for this repository; the previous two runs, `31402791964` and `31404123335`, were red.
- Both hosted and local runs exercise the same canonical `verify-all` contract but on different toolchains: the runner reported `python=3.14.6 swift=6.3.3 xcode=26.6.0`, the local clean checkout reported `python=3.13.15 swift=6.4.0 xcode=27.0.0`. The contract therefore holds across two independent toolchain sets rather than on one machine.

### Behavior delivered

- Added `tools/ci_evidence.py` and the committed command `make ci-evidence COMMIT=<sha>` so the hosted result is regenerable rather than pasted. It resolves the commit, asks GitHub for the workflow runs with that exact `head_sha`, keeps only runs whose `path` and `name` match `.github/workflows/verify.yml`, and writes an artifact **only** when at least one matching run exists and every matching run completed with `success`. Absent, incomplete, and unsuccessful states are separate refusals with the stable codes `run_absent`, `run_incomplete`, and `run_not_successful`; malformed, oversized, timed-out, and unavailable responses are refused as `response_invalid`, `response_too_large`, `command_timeout`, and `command_unavailable`. The artifact labels its own scope as hosted repository verification only, never app, device, provider, or production evidence.
- Generated `evidence/tier0/ci-verify.txt` for `e1e4207` with that command.
- `README.md` now states the measured status of `verify-clean` and `ci-evidence` instead of "result not claimed here", naming the exact commit and artifact for each.

### Commands run and evidence

- `make ci-evidence COMMIT=e1e420727b12d2b182cf6a20f014d9e61afc6de1` printed `ci-evidence:ok commit=e1e4207... run=31428035078`.
- `make test-tools` passed 37/37 (up from 31). New tests: only the required workflow for the exact commit is considered, with runs for other workflows, other names, and other commits excluded; absent, incomplete, failed, cancelled, and mixed-result run sets are each refused with their stable code; the latest successful attempt is selected and rendered with its scope label; malformed, missing-array, and oversized responses are refused; a non-commit reference is resolved or refused; and the committed Make target matches the tool invocation.
- `make lint` and `make verify-all` passed after the change.

### What is now true that was not true before

- One exact commit has passed the complete canonical verification contract from a clean checkout both locally and on hosted CI, and both results are recorded as artifacts regenerable by committed commands.

### What is still not true, stated precisely

- This is Tier 0 evidence about the repository's own verification contract. It is not evidence about the product. There is still no signed iOS target, no AVFoundation capture, no Metal filter, no RevenueCat provider integration, no device or physical-source measurement, and no production deployment. Tiers 1 through 13 remain open and every release gate G1-G6 remains red.
- The commit that carries these artifacts is necessarily a later commit than the one they measure. Each artifact names the commit it measured, and `make ci-evidence COMMIT=<sha>` regenerates the hosted claim for any commit on demand.

### Next item selected by `GOAL.md` section 10.1

- With the dev harness healthy and no failing gate that the repository can currently turn green, section 10.1 selects item 7, the lowest-numbered incomplete tier: **Tier 1**. Begin with invariant I2, "unsupported/unstable conditions are visible and recording confidence never turns green", because a false green is the highest-impact wrong result a user can be shown. I2 currently has typed policy and property attacks but no boundary assertion under component failure, no structured operational event, no alert contract, and no runbook. Deliver those, then continue through the remaining invariants by the same standard.

## 2026-08-10T21:05:00Z — Tier 1, invariant I2: recording confidence cannot be falsely green

### Why this was the selected item

- Section 10.1 found no failing `dev:health`, no failing release gate the repository can currently turn green, and no violated invariant, so it selected item 7: the lowest-numbered incomplete tier. Tier 1 had typed policy and property attacks for all eight invariants but no boundary assertion under component failure, no operational event, no alert contract, and no runbook for any of them. I2 was taken first because a false green is the highest-impact wrong result a user of this product can be shown: it costs them a shoot they only discover was ruined later.

### The gap this closed

- `CorrectionConfidence` describes frames that were **already measured**. It says nothing about whether measurement is still happening. Nothing in the repository prevented a user interface from holding a `.verified` value and rendering it green indefinitely after the analysis component stalled, after the source drifted, or after the scene changed. That is the exact false-green failure mode I2 exists to prevent, and it was reachable.

### Behavior delivered

- `Sources/AnalysisDomain/RecordingConfidence.swift` introduces `RecordingConfidence`, whose only green case `readyToRecord` carries a `VerifiedCorrection` that only `CorrectionAssessment.evaluate` can mint, and `RecordingConfidenceGate` as its sole producer.
- `AnalysisAvailability` models the health of the analysis component itself as `measuring`, `degraded` (four named causes), or `stalled` (three named causes), so a component failure withdraws green without the assessment changing at all.
- `RecordingFreshnessPolicy` bounds how old an assessment may be and still back a green state, validated at construction to 1 ms through 2 s and refused with `analysis.freshness.outside_supported_range` outside it.
- The gate fails closed in a fixed order: another session, another source, an observation older than the assessment, a stalled component, an aged-out assessment, an unavailable correction, then drift or degradation. There is no fallback branch and no default-to-green path.
- `postconditionHolds` independently re-derives every condition a green state requires and is deliberately **not** factored out of the decision path, because a guard that shares its implementation with the code it guards cannot detect that the implementation changed. If it rejects a green decision, the gate returns `refused(.invariantGuardTripped)` and emits `OperationalEvent.invariantViolated`.
- `CaptureDomain` gained `DomainInvariant` (I1-I8, so a violation is a named alertable signal), `InvariantGuard`, `InvariantViolationEvent`, and the scalar-only `RecordingConfidenceEvent`. The event carries an outcome, a closed reason, and a clamped millisecond age; it is constructed from an unsigned duration so it cannot fail and cannot carry a frame, pixel, identifier, or timestamp. Every decision ships its telemetry with it as `RecordingConfidenceDecision`.
- `CorrectionIndicator.init(recording:)` is now the only initializer, so a positive tone is unreachable from a correction assessment alone. Each tone keeps a distinct shape, visible text, and accessibility label, so state is never carried by colour alone. `FreeProofIssuer` now requires `.readyToRecord`, which removes the second path to a "verified" user-facing state and tightens I6 as a side effect.
- `docs/runbooks/recording-confidence.md` records the encodings, the attacking tests with their declared case counts, the fail-closed boundary order, and two alerts: `recording_confidence_invariant_violated` at severity 1 with a threshold of one event and an explicit instruction never to silence or rate-limit it, and `recording_confidence_withheld_rate` at severity 3 with **no threshold declared, because none has been measured**. The runbook states in its first paragraph that it is not wired to a live destination and may not be cited as evidence that alerting is operational.

### Commands run and evidence

- `xcrun swift test` passed 62/62 XCTest methods, up from 52, including 10 new `RecordingConfidencePropertyTests`. The repository now declares 27 named property attacks, up from 21.
- The new attacks and their declared case counts: `testGreenRequiresVerifiedStableMeasuringAndFreshEvidence_2520DistinctCases` and `testThePostconditionGuardAgreesOnEveryCell_2520DistinctCases` (15 assessments x 7 source conditions x 8 availability states x 3 ages, each asserting the guard and the decision path agree), `testAComponentFailureWithdrawsGreenWithoutChangingTheAssessment_7DistinctFailures`, `testAnAgeingAssessmentLosesGreenAtTheDeclaredBoundary_4DistinctAges`, `testFreshnessBudgetRefusesValuesOutsideTheDeclaredRange_4DistinctBounds`, `testEveryInvariantIsIdentifiedForAlerting_8DistinctInvariants`, plus session-splice, source-splice, clock-skew, and telemetry-shape tests. Exactly two of the 2,520 cells are green, and the test asserts that count.
- Two real test-harness defects were found and fixed while building this: `TestLiveEvidenceFactory.issueFrame` left its timestamp cursor on the value it had just issued, so a following window collided with it, and the same cursor made "age" depend on call order rather than on the requested age. The factory now issues at exact monotonic timestamps and advances the cursor past them, so each matrix cell varies only in the dimension it is meant to vary in.
- `make lint`, `make format`, and `make verify-all` passed; `verify-all` reported `tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped`.
- GitHub Actions run 31428646694 for the preceding commit `e85cc37` concluded `success`, so hosted verification stayed green across the evidence commit.

### What is now true that was not true before

- A stale, drifting, or component-failed capture cannot produce a green recording indicator, in a way enforced by types and by an independent runtime guard rather than by convention, and any disagreement between the two is a named severity-1 signal with a written response.

### What is still not true

- There is no application target, so nothing yet calls this gate on real capture callbacks, no telemetry leaves the process, and no alert can fire. Invariants I1 and I3 through I8 still lack the same treatment. Every release gate remains red and the repository remains not in production.

### Next item selected by `GOAL.md` section 10.1

- Continue Tier 1 at item 7 with invariant **I3**, "diagnostic work drops before recorded frames". `CaptureAdmissionPolicy` already encodes the arithmetic and is attacked by 32,768 cases, but there is no typed notion of a component under backpressure, no operational event when diagnostics are dropped, no alert contract, and no runbook. Give I3 the same five answers I2 now has, then continue through I1 and I4 through I8 by the same standard.

## 2026-08-10T21:40:00Z — Tier 1, invariant I3: diagnostics cannot starve a recorded frame

### Why this was the selected item

- Section 10.1 item 7, continuing Tier 1. I3 already had correct arithmetic and a 32,768-case attack, but four of Tier 1's five questions were unanswered: no type made a starving admission unrepresentable, no component-failure scenario attacked it, no operational event recorded the decision, and no alert or runbook existed.

### The gap this closed

- `CaptureAdmissionPolicy.decide` computed the right answer, but `CaptureAdmission` was an ordinary public struct: any code in the package could build one that admitted diagnostic work while recorded frames waited, and nothing downstream could tell the difference. The invariant lived in one function rather than in the type.
- Capture pressure was not modeled at all. Under thermal throttling or a storage stall the policy would still hand leftover capacity to diagnostics, competing with the recorder for exactly the margin the recorder needs.
- `CaptureLoad` accepted any non-negative count including `Int.max`, so a corrupted count entered the arithmetic instead of being refused.

### Behavior delivered

- `Sources/CameraDomain/CaptureBackpressure.swift` now owns admission, separated from frame provenance in `LiveFrameEvidence.swift`. `CaptureAdmission` has only a `fileprivate` initializer, so `CaptureAdmissionPolicy` is its sole producer, and `starvesRecordedFrames` names the forbidden condition as a checkable property.
- `CapturePressure` (nominal, thermalThrottling, storageBandwidthLimited, analysisBacklog, sessionRestarting) is a required field of `CaptureLoad`. Under any non-nominal pressure diagnostics receive **zero** capacity, so the remaining margin stays with the recorder rather than being shared with work that can be redone on the next frame. This is a designed refusal, not a heuristic.
- `CaptureLoad.maximumQueueDepth` is 1,000,000. A larger count, including `Int.max`, is refused as `camera.capture_load.queue_depth_too_large` rather than being clamped or saturated: a depth that cannot occur in a real pipeline is corrupted state, not a large number.
- `postconditionHolds` re-derives conservation of both queues, the capacity bound, the recorded-first rule, the pressure rule, and the absence of starvation, independently of the arithmetic it guards. On disagreement the policy falls back to admitting only recorded frames, drops every diagnostic job, and emits `OperationalEvent.invariantViolated` with invariant `I3` and guard `captureAdmissionPostcondition`.
- Every decision now ships `OperationalEvent.captureAdmissionDecided` with scalar counts and a closed `CapturePressure`; no frame, buffer, or identifier crosses that boundary, which keeps I5 intact.
- `docs/runbooks/capture-admission.md` records the encodings, the attacking tests with declared case counts, the fail-closed boundary behaviour, and three alerts: `capture_admission_invariant_violated` at severity 1 with a threshold of one event and an instruction never to silence it, `recorded_frames_deferred_rate` at severity 2 with **no threshold declared because none has been measured on hardware**, and an informational cross-check against the I2 runbook that names disagreement between the two views as a defect.

### Commands run and evidence

- `xcrun swift test` passed 66/66 XCTest methods, up from 62. The I3 matrix grew from 32,768 to 163,840 declared cases by adding the five pressure values, and it now also asserts that zero cells starve recorded frames and that the guard accepts every cell the policy produced.
- New attacks: `testNonNominalPressureStopsDiagnosticWorkEntirely_4DistinctPressures`, `testNoCapacityDefersEveryRecordedFrameAndRunsNoDiagnostics`, `testThePostconditionGuardRejectsStarvationAndMiscounting`, `testQueueDepthsAboveTheSupportedMaximumAreRefused_6DistinctCases`, and `testEveryDecisionRecordsScalarCountsAndNoViolation`.
- **A test was replaced, not removed.** `testAdmissionArithmeticHandlesIntegerExtremesWithoutOverflow` asserted saturating behaviour at `Int.max`. `Int.max` is now refused at the ingestion boundary, so that assertion is no longer meaningful; the replacement asserts both the refusal above the bound and exact arithmetic at the bound. This is a strictly stronger boundary, not a weakened one.
- `make format`, `make lint`, and `make verify-all` passed; `verify-all` reported `tracked-content=stable index=stable untracked-content=stable ignored-artifacts=allowlisted services=ownership-stopped`.
- GitHub Actions run for the preceding commit `480436c` concluded `success`, so hosted verification stayed green across the I2 slice.

### What is now true that was not true before

- An admission that runs diagnostic work while a recorded frame waits cannot be constructed, is rejected by an independent guard if the arithmetic ever produces one, and would raise a named severity-1 signal with a written response. Under any capture pressure, diagnostics stop entirely rather than competing for the recorder's margin.

### What is still not true

- No `AVCaptureSession` adapter calls this policy, no frame has been recorded, no capacity figure has been measured, and no telemetry leaves the process. Invariants I1 and I4 through I8 still lack this treatment. Every release gate remains red and the repository remains not in production.

### Next item selected by `GOAL.md` section 10.1

- Continue Tier 1 with invariant **I5**, "no frame pixels enter analytics or RevenueCat attributes", taken ahead of I1 and I4 because it is the one invariant whose violation is irreversible for the user: a leaked frame cannot be recalled from a provider. `OperationalEvent` and `PurchaseAttributeSnapshot` are already closed scalar-only types, but there is no compile-time boundary test proving a frame type cannot be reached from a telemetry payload, no runtime audit of a serialized payload, and no alert or runbook. Give I5 the same five answers, then continue with I1, I4, I6, I7, and I8.
