# ADR-0001: Swift 6 toolchain and enforceable module boundaries

- **Status:** Accepted
- **Date:** 2026-08-09
- **Owners:** Repository maintainers

## Context

The product contract requires a signed native iOS/iPadOS application using Swift 6, SwiftUI, AVFoundation, Accelerate, Metal, and RevenueCat. The repository begins without code, so the first architectural decision must make clean-checkout verification possible without pretending a simulator or portable package is device evidence. Domain packages must not import UI, transport, cloud SDK, or framework state, and provider objects must not cross adapters.

## Decision

1. Use Swift Package Manager with Swift language mode 6 for portable domain and policy modules. Compiler concurrency checks and warnings are blocking.
2. Keep application/framework adapters in modules that depend inward on domain contracts. Domain targets do not link SwiftUI, AVFoundation, Metal, Photos, StoreKit, RevenueCat, or network frameworks.
3. Add the signed iOS application target through an Xcode project while reusing the package modules; package-only success remains explicitly non-device evidence.
4. Use deterministic XCTest suites for domain and policy behavior. Property-style suites declare their case count and seed.
5. Use Python standard-library loopback services for repository-local operational surfaces, and Playwright only for browser/E2E verification. Neither is shipped in the iOS binary.
6. Pin direct and transitive third-party dependencies with lockfiles and record their license, maintenance, security, native impact, and cost.
7. CI runs on an explicit macOS runner label with permissions minimized and third-party actions pinned to immutable commit SHAs.
8. Portable implementations live under `Sources/<OwnershipArea>Domain`; deterministic package tests live under `Tests/`. The future signed application owns Apple-framework adapters under `App/<OwnershipArea>/` only when they contain working code. This reconciles the conceptual root-area layout in `README.md` with the more specific `App/` ownership layout in `WINNING_IDEA.md` without creating empty directories.
9. Architecture decisions use root `adr/`, as required by `GOAL.md`; `README.md` is updated to match. `verify-all` is canonical, while `full-verify` and `release-check` are aliases/supersets rather than divergent implementations.
10. Local development exports `DEVELOPER_DIR` per command rather than mutating the machine-wide `xcode-select`. CI uses the immutable installed path `/Applications/Xcode_26.6.app/Contents/Developer` on `macos-26`, not that image's mutable `/Applications/Xcode.app` default symlink; a newer local Xcode may compile language-mode-6 packages but cannot by itself establish App Store eligibility.
11. The package-policy gate reads SwiftPM's evaluated package graph, rejects external/product/binary dependencies in the portable foundation, rejects adapter/provider/transport targets under `Sources/`, and accepts source imports only when they are an explicitly allowed Swift module or a declared internal target dependency. Access-modified and selective imports are parsed too. Future framework/provider work belongs under `App/` and requires an ADR-backed boundary update rather than an import-check exception.
12. `verify-all` recreates the Node development tree from `package-lock.json`; no stamp file is accepted as dependency evidence. npm cache, Playwright browsers, logs, and scratch stay beneath a symlink-refusing `.dev/` namespace. Verification hashes the Git index plus every tracked and non-ignored untracked worktree file before and after, while separately recording every permitted ignored artifact path and category.
13. Clean-checkout verification rejects a dirty source repository, verifies exactly `HEAD`, runs only the canonical `make verify-all` command under a hard deadline in its own process group, and terminates that group on timeout/interruption. Because development services deliberately own independent sessions, cleanup then runs that detached worktree's ownership-safe `scripts/devctl.py down` under a separate deadline before removing anything. Failed service shutdown retains the worktree and PID evidence and makes the gate fail; incomplete Git/filesystem cleanup also fails.

### Enforced portable dependency graph

This table is an allowlist, not merely a description. `tools/check_policy.py` rejects missing or additional targets, missing or additional edges, external products/packages, binary/plugin/system targets, unapproved imports, linked frameworks/libraries, and missing strict compiler flags. Any graph change requires this ADR (or a superseding ADR), the policy allowlist, and adversarial tests to change together.

| Target | Permitted direct dependencies |
|---|---|
| `CaptureDomain` | None |
| `RuntimeConfiguration` | `CaptureDomain` |
| `CameraDomain` | `CaptureDomain` |
| `AnalysisDomain` | `CaptureDomain`, `CameraDomain` |
| `MetalDomain` | `CaptureDomain` |
| `PurchasesDomain` | `CaptureDomain` |
| `ExportDomain` | `CaptureDomain`, `MetalDomain`, `PurchasesDomain` |
| `EvaluationDomain` | `CaptureDomain` |
| `UIDomain` | `CaptureDomain`, `AnalysisDomain`, `PurchasesDomain` |
| `FoundationPropertyTests` | Every portable target above; external import limited to `XCTest` |

Every portable and test target must retain `-warnings-as-errors`, `-strict-concurrency=complete`, and `-warn-concurrency`; these are the only permitted unsafe flags. Portable source may import only its declared direct dependencies plus explicitly allowed Swift language modules; tests may additionally import `XCTest`. This narrow Tier 0 rule intentionally fails closed before Apple/provider adapters exist.

## Alternatives considered

- **Xcode project only:** rejected because pure domain verification would become coupled to simulator runtimes and signing configuration.
- **A cross-platform UI framework:** rejected because it conflicts with the approved native Swift/SwiftUI direction and adds a large runtime boundary.
- **A web-first demonstration:** rejected because it cannot exercise AVFoundation/Metal capture behavior and would create a prohibited judging-only path.
- **Unmodularized single app target:** rejected because framework/provider objects could silently leak into the domain and boundary violations would be review-only.
- **Third-party Python/Node server framework:** deferred because Tier 0 needs only bounded loopback services and the standard library avoids extra supply-chain and runtime cost.

## Consequences

- Core math, state, privacy, and entitlement policies can be tested on CI and macOS.
- Camera, Metal, recording, purchase-provider, Photos, accessibility, and thermal claims still require their real adapters and physical-device/provider tests.
- More modules add build graph overhead but make prohibited imports structurally visible.
- Fail-closed import and dependency allowlists deliberately require policy/ADR review before a new foundation module or external package can enter the graph.
- Reinstalling the small locked browser-test dependency tree costs time but removes mutable stamp files from the release-gate trust base. Ignored build/cache artifacts may change, but only inside explicitly inventoried repository-local namespaces.
- A later dependency or target change requires this ADR or a superseding ADR to analyze migration, failure modes, operational cost, and reversal.

## Reversal

The package modules can be embedded as local Xcode targets or migrated to another Apple-native package layout while preserving public typed contracts and tests. Reversal requires a clean-checkout comparison proving identical invariant enforcement and no new outward domain dependencies.
