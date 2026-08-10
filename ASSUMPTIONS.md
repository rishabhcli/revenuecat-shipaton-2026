# Assumptions Register

Every decision made without an explicit user instruction is recorded here with its safety rationale and cheapest verification path. An entry remains open until verified or superseded by an ADR.

## A-001 — Portable domain foundation before the signed app target

- **Decision:** Establish strict Swift 6 domain packages and repository verification on macOS before adding the signed iOS application target.
- **Reasoning:** The installed Xcode toolchain can compile both, while portable packages let domain invariants and deterministic tests run in CI without a camera or signing identity. This does not substitute for the required native iOS application or device verification.
- **Safety boundary:** No simulator, macOS, or package-only result may be described as camera, iOS, device, TestFlight, or production evidence.
- **Cheapest verification:** Build the eventual iOS target with the same domain packages under `xcodebuild`, then run it on a physical supported device.
- **Status:** Open.

## A-002 — Standard-library loopback services for Tier 0

- **Decision:** Use Python standard-library HTTP services for the repository-local evaluation, webhook test receiver, original test-pattern, and artifact-metadata development surfaces.
- **Reasoning:** This keeps the services deterministic, inspectable, and free of an unpinned server framework while meeting the exclusive port and health semantics in `GOAL.md` section 0A.
- **Safety boundary:** Services bind only to `127.0.0.1`, persist only repository-local synthetic/test data, and never claim that RevenueCat, TestFlight, App Store, or production verification occurred.
- **Cheapest verification:** Run `make dev:preflight`, `make dev:up`, `make dev:health`, inspect every readiness response, then `make dev:down` and prove only recorded PIDs stop.
- **Status:** Verified for the repository-local harness on 2026-08-09 by the recorded lifecycle and integration commands in `PROGRESS.md`. This does not verify any deployed, provider, app, or device environment.

## A-003 — Node is development-harness-only

- **Decision:** Pin Node/npm and Playwright only for browser-level verification of local support services; none enters the shipped iOS runtime.
- **Reasoning:** `GOAL.md` requires an explicit Playwright `webServer` entry, while the product contract requires a native Swift/SwiftUI application.
- **Safety boundary:** JavaScript packages are dev dependencies only and cannot be imported by Swift domain targets.
- **Cheapest verification:** Inspect the Swift dependency graph and release manifest, then run the boundary policy check in `verify-all`.
- **Status:** Verified for the current portable SwiftPM graph on 2026-08-09. `make policy-check` evaluates the manifest, permits only declared internal imports/dependencies, rejects app/provider/transport placement under `Sources/`, and adversarial tool tests exercise bypass forms. An eventual `App/` target and provider SDK require their own renewed boundary evidence.

## A-004 — MIT license for the public Next Gen source route

- **Decision:** License repository-authored source under the MIT license with copyright held by the repository contributors.
- **Reasoning:** `WINNING_IDEA.md` calls for public/open source for the Next Gen route and already plans a root `LICENSE`; MIT is permissive, short, compatible with the intended public source review, and does not imply a product name or partnership.
- **Safety boundary:** Third-party code and generated assets retain their own licenses and provenance; adding MIT does not relicense external material.
- **Cheapest verification:** Confirm the final published repository and Devpost disclosure identify the same license and list every third-party dependency/assets license.
- **Status:** Open until the public source route is verified.

## A-005 — Playwright coordinates the complete block through port 4222

- **Decision:** Treat the test-pattern server at `127.0.0.1:4222` as Playwright's browser readiness URL while `devctl e2e-server` owns and verifies all four allocated services for that coordinator lifecycle.
- **Reasoning:** The port table does not allocate a separately named test-harness port; 4222 is the browser-served original-pattern surface. Starting it last prevents its readiness response from masking failure of evaluation, webhook, or artifact services.
- **Safety boundary:** Playwright sets `reuseExistingServer: false`; the coordinator must refuse existing owned services and foreign listeners, use the repository-local profile, health-check all four identities, clean up only authenticated owned processes, and never imply physical timing calibration from a browser pattern.
- **Cheapest verification:** Run the Playwright configuration with an allocated port occupied by a foreign listener and prove startup fails without signalling that process, then interrupt a successful run and prove all four authenticated PID records are reconciled.
- **Status:** Verified for the local harness on 2026-08-10. A foreign listener on 4222 caused the Playwright coordinator to refuse startup without signaling that process or creating PID records. A separately interrupted repeated E2E run reported `interrupted`, then left zero service PID records and zero listeners on 4220–4223. This is lifecycle evidence only, not browser timing, device, provider, or production evidence.
