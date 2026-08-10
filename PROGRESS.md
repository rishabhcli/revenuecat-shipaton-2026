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
