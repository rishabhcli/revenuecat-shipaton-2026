# Dependency and toolchain register

Last audited: 2026-08-09. This register distinguishes shipped runtime dependencies from development-only verification dependencies. Exact transitive package versions and integrity hashes are authoritative in `package-lock.json`.

## Shipped runtime

No third-party runtime dependency is linked into the current Swift package. The approved future RevenueCat SDK integration is not yet present and therefore is not represented as installed or configured.

Apple SDK modules and the Swift standard library are platform components, not vendored dependencies. Their use is constrained behind adapters when they own framework state.

## Direct development dependencies

| Dependency | Pin | License | Maintenance and security evidence | Native/binary impact | Runtime/bundle cost | Replacement boundary |
|---|---:|---|---|---|---|---|
| `@playwright/test` | `1.62.1` | Apache-2.0 | Current registry release checked 2026-08-09; maintained by Microsoft. `npm audit` is a blocking check. Advisories are not assumed absent merely because the current audit is green. | Development-only JavaScript. `test-e2e` explicitly installs the Playwright-pinned Chromium revision under ignored `.dev/cache/ms-playwright`; `npm ci` runs no install scripts. | Zero in the iOS artifact; Node/browser processes and repository-local cache only during E2E. | `Tests/e2e` and `playwright.config.ts` only. |

## Locked transitive development dependencies

| Dependency | Pin | License | Why present | Native/install behavior |
|---|---:|---|---|---|
| `playwright` | `1.62.1` | Apache-2.0 | Test runner browser/request implementation. | JavaScript; the pinned Chromium download is explicit, bounded to `.dev/cache`, and never linked into the app. |
| `playwright-core` | `1.62.1` | Apache-2.0 | Protocol and browser automation core. | JavaScript; no shipped app linkage. |
| `fsevents` | `2.3.2` | MIT | Optional Darwin watcher dependency of Playwright. | Optional native package with an install script. Bootstrap uses `npm ci --ignore-scripts`, and the harness does not require it. |

## Pinned CI actions

GitHub Actions are supply-chain code and are pinned to immutable commits rather than mutable tags.

| Action | Release | Commit | License | Scope |
|---|---:|---|---|---|
| `actions/checkout` | `v7.0.1` | `3d3c42e5aac5ba805825da76410c181273ba90b1` | MIT | Read-only checkout with persisted credentials disabled. |
| `actions/setup-node` | `v7.0.0` | `820762786026740c76f36085b0efc47a31fe5020` | MIT | Installs the exact `.node-version` runtime and uses npm cache. |
| `actions/upload-artifact` | `v7.0.1` | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` | MIT | Uploads only the redacted verification log for 14 days. |

## Toolchains

| Tool | Declared contract | Local verification surface | CI contract |
|---|---|---|---|
| Swift | Swift language mode 6; `swift-tools-version` is authoritative | Apple Swift 6.x under the selected Xcode `DEVELOPER_DIR` | Explicit `macos-26` runner with the installed Xcode 26.6 path; bootstrap rejects a non-Swift-6 compiler |
| Xcode | Full Xcode required for Apple SDK and eventual signed iOS target | `/Applications/Xcode.app/Contents/Developer` when available | Immutable `/Applications/Xcode_26.6.app/Contents/Developer` path on `macos-26`; no reliance on the image's mutable default symlink |
| Python | Standard library only, 3.11–3.14 | Lifecycle, policy, and integration scripts | Runner Python 3.14.x |
| Node | `.node-version` (`26.5.1`) | Playwright development harness only | Installed by pinned `actions/setup-node` |
| npm | major 11, exact lock format 3 | `npm ci --ignore-scripts` | Same command; `npm audit --audit-level=high` blocks |

## Audit commands

```sh
make bootstrap
make dependency-audit
make policy-check
make sbom
```

`make bootstrap` recreates `node_modules` from `package-lock.json` with install scripts disabled, validates the resulting dependency tree, and confines npm cache and temporary writes to `.dev/`. An update changes the lockfile, this register, the SBOM/release manifest when introduced, and the evidence from a clean `verify-all` run. Binary or native additions require a new ADR before merge.

## Development-footprint measurement contract

No fixed disk-size number is published here. Allocated disk usage varies with filesystem allocation, npm cache state, and the Playwright browser revision's platform archive, so a copied observation would not be reproducible as a repository invariant.

After `make test-e2e`, capture a machine-local observation without turning it into a product or release claim:

```sh
du -sk node_modules .dev/cache/npm .dev/cache/ms-playwright
```

Record the raw KiB values, operating system, architecture, filesystem, Node/npm versions, Playwright version, and source commit beside any evidence that uses them. None of these development-only directories is part of the current Swift package build graph; an eventual signed application requires its own bundle-size measurement from the archived artifact.
