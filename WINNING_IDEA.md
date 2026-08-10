# RevenueCat Shipaton 2026: Winning Idea Dossier

> **Status:** One idea selected; no product name assigned. The Tier 0 executable, domain, and local development-harness foundation is under construction. No signed app, device/provider path, or production deployment has been established.
> **Deadline:** September 30, 2026 at 11:45 PM PT.
> **Primary award targets:** RevenueCat Design Award and Next Gen Award.
> **Secondary fit:** HAMM and Most Viral only if real results support them.
> **Ground truth:** [`HACKATHON.md`](./HACKATHON.md) is authoritative for rules, assets, and submission fields.

## Final decision

Build a native iPhone camera app for filming monitors, televisions, projectors, LED walls, and PWM-lit rooms without rolling bands or destructive moiré. It analyzes the live rolling-shutter pattern, estimates the source's flicker frequency and phase, locks exposure to a compatible duration, and applies a spatial moiré-reduction pass that preserves real edges. The user sees an immediate split-screen before/after and records only when the correction is stable.

No product name is proposed. “Screen-safe capture camera” is a functional description only.

## The one-line version

Point an iPhone at a screen with rolling bands, tap once, and watch the bands disappear live because the app measures the light's timing and chooses a shutter interval that agrees with it.

## Why this is the strongest RevenueCat concept

Most Shipaton entries will be ordinary apps with an ordinary subscription. This idea begins with a visual defect everyone has seen, then removes it in one uncut shot. It aims at awards whose language matches the product:

- **RevenueCat Design Award:** innovative idea, beautiful app design, animations, craft separate from business viability.
- **Next Gen Award:** active-student path judged through video and open-source code without requiring a paid store account.
- **HAMM:** monetization occurs when the correction visibly works and the user wants to save production-quality footage; it is not a random hard paywall.
- **Most Viral:** every strong before/after clip demonstrates the value, though this should not be claimed without actual distribution results.

The difficult part is not a model call. It is camera timing, calibration, signal estimation, real-time GPU filtering, and a UI that refuses recording when confidence is low.

### Ideas eliminated from the recovered Claude brainstorm

- **Escalating pay-to-unlock blocked apps:** clever monetization but high entitlement/App Review risk and users succeed by churning.
- **LiDAR sofa path planning:** exceptional technical demo, but hardware-gated and stairwell scans are unreliable.
- **Delayed auditory feedback for stuttering:** meaningful social benefit, but requires a willing affected participant, careful clinical claims, and route-latency validation.
- **Room acoustic measurement:** useful, but the phone speaker cannot excite the low frequencies users care about and accuracy is easy to challenge.
- **Signed-at-capture evidence:** cryptographically elegant, but no institution is obligated to trust a private receipt format.
- **UWB hide-and-seek:** fun but requires multiple compatible devices and hurts judge/test accessibility.
- **AR desk physics game:** visually strong, but stable scene geometry and device support make the schedule fragile.
- **On-device SMS fraud filter:** socially valuable but corpus, extension memory, and OS competition weaken differentiation.
- **Chemical strip color measurement:** rigorous but requires physical strips, per-brand calibration, and accuracy evidence.
- **Ad-revenue-visible economy:** excellent Catvertising fit but dependent on ad-network policy and a second app/game worth using.
- **Hidden-camera reflection sweep:** unsafe to position as reliable and belongs to a distrusted product category.
- **Rolling-shutter oscilloscope only:** technically pure but a narrow market. The selected idea turns the same sensing insight into a creator tool with an immediate correction.
- **HealthKit self-analysis:** honest statistics are valuable, but empty judge devices, review friction, and sensitive health framing create avoidable risk.

## Specific problem and user

Creators, students, event organizers, teachers, product teams, gamers, and ordinary users frequently film:

- laptop/desktop screens;
- televisions;
- LED signage and stage walls;
- projectors;
- dashboard displays;
- rooms lit by dimmed LED fixtures.

The camera and source sample time differently. A rolling shutter exposes sensor rows at slightly different moments while displays refresh and lights pulse. The result is dark bands, brightness waves, color stripes, or partial-frame tearing. Fine pixel grids also interfere to produce moiré.

Users currently change shutter values by trial and error in professional camera apps, change the display refresh rate, add light, move the camera, or repair footage later. Stock camera controls hide the timing relationship. The job is simple: make a screen look on camera the way it looks to the eye, and tell the user when that cannot be done reliably.

## Scope boundary

### Version-one job

Detect temporal banding in the live preview, estimate a compatible capture configuration, lock it, reduce residual spatial moiré, and record/export corrected footage.

### Supported targets

- iPhone/iPad running a declared minimum iOS version.
- Rear wide camera first; other lenses only after calibration.
- 30 fps and 60 fps recording.
- Displays/lighting with stable or slowly varying flicker.
- 1080p stable path; 4K only after thermal/performance tests.
- Manual focus/exposure/white-balance lock.
- User-visible confidence and unsupported-state warnings.

### Non-goals

1. No general cinema camera replacement.
2. No Android in the hackathon build.
3. No claim to repair arbitrary footage after capture.
4. No promise to eliminate aliasing caused by content below the sensor/display Nyquist limit.
5. No cloud processing or account requirement.
6. No generative video enhancement.
7. No copyrighted test footage or third-party trademarks in the submission video.
8. No hidden automatic filter that makes measurements impossible to inspect.
9. No subscription required merely to open the camera.
10. No product name until the capture loop is validated.

## Product experience

### Camera opens to diagnosis, not onboarding

The free camera preview opens immediately. A thin diagnostic strip displays:

- detected banding energy;
- likely source frequency or harmonic family;
- selected exposure duration;
- confidence/stability;
- whether spatial moiré is also present.

The center offers a draggable before/after divider. The app continuously tests candidate exposure values within device limits but changes nothing abruptly until a solution is stable.

### One correction action

The primary control is “sync.” On tap:

1. exposure and ISO enter a bounded search;
2. live frame stripes are analyzed;
3. compatible shutter periods are ranked;
4. focus and white balance lock;
5. the best candidate is applied;
6. a short stability window confirms improvement;
7. recording becomes available.

If no candidate materially reduces banding, the UI says why: source is unstable, brightness would be unacceptable, rolling-shutter readout/calibration is unknown, or the target is spatial moiré rather than temporal flicker.

### Moiré pass

A separate strength control appears only when repeated spatial interference is detected. The user sees a magnified loupe over the worst region. The filter targets narrow periodic peaks rather than blurring the whole image.

### Honest capture guard

Before recording, a small indicator is:

- green: stable correction;
- amber: usable but source drift detected;
- red: no reliable correction.

Color is mirrored by shape/text. The user can record in amber/red, but the app does not label it fixed.

### Results

After a clip, show:

- corrected clip;
- optional before/after diagnostic sample;
- measured banding score reduction;
- settings used;
- source stability over time;
- export options.

No social feed, template marketplace, or AI caption generator is added.

## Monetization and RevenueCat design

### Principle

The purchase happens after the app proves it can fix the user's exact scene. Charging before proof would undermine trust.

### Free tier

- Unlimited live diagnosis and preview.
- Short watermarked or resolution-limited test clips sufficient to validate correction.
- One full-quality export during onboarding or a transparent free allowance.
- Access to the compatibility report.

### Paid entitlement

One `pro_capture` entitlement unlocks:

- unlimited full-resolution exports;
- 4K/60 where the device passes performance checks;
- advanced moiré filter;
- saved source profiles;
- manual diagnostic controls;
- batch comparison/export;
- pro scopes and metadata export.

### Offering strategy

RevenueCat controls a remote offering containing:

- lifetime purchase as the honest default for an instrument;
- optional monthly/yearly plans only if ongoing creator workflows and updates justify them;
- a free trial or judge promo mechanism as required.

The app should not use a weekly subscription, fake countdown, or artificial export token scarcity. A/B testing can compare lifetime-first versus subscription-first only after enough users exist; no fabricated conversion result goes in the submission.

### Load-bearing integration

The production integration is not implemented yet. It must satisfy all of the following before it can support a provider-readiness or award claim:

- RevenueCat SDK configures products and purchases.
- Entitlement state gates full-quality export and advanced processing.
- Restore purchases is complete.
- Offline entitlement behavior is documented.
- Customer identity remains anonymous unless an account later becomes necessary.
- Offerings can change without a new binary.
- Sandbox purchase and judge-unlock flow are visible in tests/demo.
- Purchase failure/cancel leaves the free camera usable.

### Award strategy

The submission primarily wins on craft and student execution. HAMM is secondary because RevenueCat is integrated at the exact moment of demonstrated value, but no claim of meaningful revenue is made without real transactions. Grand Prize traction is not the initial strategy; competing for it would require a public store release and serious growth work beyond technical quality.

## Native architecture

```text
AVCaptureSession
   |
   +--> frame sampler -----------------------------+
   |    luma strips / timestamps                   |
   |                                               v
   |                                      temporal analyzer
   |                                      flicker/frequency/phase
   |                                               |
   |                                               v
   |                                      exposure candidate search
   |                                               |
   +--> preview pipeline --> Metal moire filter <--+
   |          |                    |
   |          v                    v
   |     diagnostic overlay     recorder/exporter
   |                                |
   +--------------------------------+
                                    v
                          RevenueCat entitlement gate
                                    |
                               Photos/share sheet
```

### Recommended stack

- Swift 6 and SwiftUI.
- AVFoundation for capture device/session, frame timing, manual exposure, focus, and white balance.
- Metal/Metal Performance Shaders for tiled spectral analysis and filtering.
- Accelerate/vDSP for FFT, windowing, and signal metrics.
- Core Image only for non-critical compositing/export.
- RevenueCat Purchases SDK, with offerings and entitlements configured and verified at the provider boundary before they are described as ready.
- StoreKit sandbox tests.
- XCTest plus prerecorded synthetic frame sequences.
- Local-only diagnostics; no cloud backend required for the core.

## Hard technical core

### 1. Temporal banding signal extraction

For selected preview frames:

1. convert to linear or approximately linear luma;
2. remove scene content using temporal median/background estimation;
3. aggregate intensity by sensor row or narrow horizontal strip;
4. detrend slow illumination gradients;
5. apply a window and compute spectral/phase features;
6. estimate band spacing, direction, drift, and confidence across frames.

A display image itself may contain horizontal lines, so a candidate is trusted only if its phase moves consistently over time and responds to exposure changes like a temporal source.

### 2. Source frequency and rolling-shutter relationship

The visible stripe pattern is an alias between source modulation and row readout. Exact recovery of source frequency may be ambiguous without calibrated line timing. The product does not need a perfect physical frequency to correct the image; it needs to identify exposure durations that integrate an integer number of brightness cycles and minimize measured residual energy.

Maintain a per-device/lens/format calibration table where possible. When unavailable, run an empirical candidate search and label the displayed frequency as an estimate.

### 3. Exposure candidate search

Generate candidate exposure durations from likely 50/60 Hz families, display refresh harmonics, and observed stripe frequency. Respect:

- frame duration;
- sensor exposure limits;
- target brightness/ISO ceiling;
- motion-blur budget;
- anti-flicker integration periods;
- thermal/performance mode.

For each candidate, allow a settling window, score banding energy over several frames, and retain confidence intervals. Use hysteresis so settings do not oscillate when two candidates score similarly.

Objective:

```text
score = banding_energy
      + alpha * brightness_error
      + beta * ISO_noise
      + gamma * motion_blur_cost
      + delta * instability
```

The winning setting is not always the lowest banding value if it makes the footage unusably dark or blurred.

### 4. Moiré detection

Spatial moiré appears as narrow, repeated energy peaks whose orientation varies by image region. Divide the frame into overlapping tiles, transform luma/chroma with a windowed 2D FFT, and identify off-axis spectral peaks exceeding the local natural-image baseline. Temporal persistence and relation to detected display edges reduce false positives.

### 5. Moiré suppression

For affected tiles, apply soft, orientation-aware notch filters around interference peaks in a Metal compute pass, then overlap-add. Protect real edges through:

- conservative notch radius;
- edge/semantic mask limiting strength around text and UI details;
- chroma-first suppression where appropriate;
- temporal smoothing of peak location;
- preview loupe and user strength control.

A simpler oversample/low-pass/downscale path is a fallback for unsupported devices, but the main technical claim requires targeted filtering that preserves detail measurably better.

### 6. Correction confidence

Confidence is based on repeatability:

- banding score reduction across N frames;
- source frequency/phase stability;
- candidate margin versus second-best;
- no exposure oscillation;
- moiré-peak consistency;
- thermal frame drops below threshold.

The app must expose low confidence and avoid a magic “AI fixed” badge.

### 7. Real-time constraints

- Keep camera callback allocation-free or bounded.
- Sample diagnostics at lower resolution/frequency than recording.
- Run Metal filter within frame budget.
- Use separate queues for capture, analysis, render, and export.
- Drop diagnostic work before dropping recorded frames.
- Monitor thermal state and disable costly filters gracefully.
- Preserve audio/video sync.

## Validation plan

### Controlled visual sources

Create original test patterns to avoid trademarks/copyright:

- 50/60 Hz LED PWM driver or dimmable bulbs at several levels;
- laptop display at 60/120 Hz showing custom checkerboards, text, gradients, and scrolling motion;
- television/projector if available;
- an LED strip/controller with known frequencies;
- synthetic rolling-shutter sequences with exact ground truth.

### Metrics

- normalized row-banding energy before/after;
- temporal luminance modulation residual;
- moiré spectral peak energy;
- edge/detail preservation using original digital test pattern as reference;
- exposure stability and setting convergence time;
- dropped frames and thermal state;
- user rating of before/after without knowing mode.

### Device matrix

At minimum test every physically available iPhone/iPad lens and format. Do not claim universal device support. Publish a compatibility table with:

- device;
- iOS version;
- lens;
- 1080p/4K, 30/60;
- tested source types;
- median banding reduction;
- known failures.

### Success thresholds

- obvious banding scene corrected in one continuous take.
- median measured banding-energy reduction of at least 80% on supported test conditions.
- convergence under three seconds.
- no more than declared detail loss under moiré test patterns.
- stable 30 fps minimum on supported devices.
- all unsupported/unstable cases visibly labeled.

## Design system

- Camera preview owns the screen; controls are peripheral.
- Diagnostic data uses fine typography and scopes, not a dashboard grid.
- The before/after divider follows the finger at 60 fps.
- Sync action animates exposure candidates as a narrowing waveform, then settles.
- Haptics confirm lock, loss of lock, and recording.
- Dark neutral chrome prevents color contamination.
- Icons are paired with text and VoiceOver labels.
- Color status uses shape and words.
- Pro paywall uses the same live scene: advanced output is previewed on the user's target, not stock marketing images.
- No full-screen paywall before first proof.

## Privacy and safety

- Video stays on device until the user exports.
- No automatic cloud upload.
- Diagnostics contain no frame pixels in analytics.
- Photos permission requested only at export, camera/mic permissions only when needed.
- Microphone can be disabled for diagnostic-only use.
- No face recognition or content analysis.
- The app warns about filming sensitive screens and respects system capture indicators.
- Never imply that flicker metrics are a medical diagnosis.
- No health claims about migraine/eye strain in this selected scope.

## First 48-hour kill test

The riskiest assumption is that AVFoundation offers enough stable manual control to produce a dramatic, repeatable correction on available hardware.

Within 48 hours:

1. enumerate manual exposure ranges for one rear camera/format;
2. create a custom 60/120 Hz test pattern and one PWM LED source;
3. capture preview buffers;
4. compute a simple row-banding score;
5. sweep at least ten exposure candidates;
6. lock the best candidate;
7. record one uncut before/after;
8. repeat five times and report convergence.

Kill or narrow if no available source produces a stable visible defect, settings cannot be locked, the corrected clip is darker/blurrier than acceptable, or the score does not track human perception.

Do not start moiré filtering until the temporal fix works reliably.

## Build order

### August 9-11: camera-control proof

AVCaptureSession, manual exposure/ISO/focus/WB, row score, candidate sweep, uncut correction clip.

### August 12-15: robust temporal analyzer

Linear luma, detrending, phase consistency, candidate ranking, hysteresis, stability/confidence.

### August 16-18: recording path

Audio/video capture, corrected preview, settings metadata, export, frame/thermal instrumentation.

### August 19-22: core interface

Before/after divider, sync action, status guard, permissions, VoiceOver, error states.

### August 23-27: test matrix

Original display patterns, LED sources, lenses/formats, automated metric harness, compatibility report.

### August 28-September 2: moiré detector

Tiled FFT, peak detection, scene-edge false-positive tests, offline prototype first.

### September 3-7: Metal suppression

Soft notch filters, overlap-add, temporal smoothing, edge protection, live loupe.

### September 8-10: RevenueCat

SDK, products, `pro_capture` entitlement, offerings, purchase/restore/offline/failure states, sandbox tests.

### September 11-13: paid experience

Free proof path, full-quality export gate, paywall using live scene, no dark patterns.

### September 14-17: performance

30/60 fps, 1080p/4K decisions, thermal degradation, device compatibility matrix.

### September 18-20: external creator testing

At least eight users film screens/lights. Record setup failures, correction time, and willingness to pay without leading questions.

### September 21: feature freeze

No new target types, filters, or monetization modes.

### September 22-24: design polish

Icon, motion, haptics, typography, onboarding, accessibility, localization-ready strings.

### September 25-26: submission build

Next Gen video/source route; if public store release is pursued, ensure it meets first-public-version timing and review buffer. Do not endanger Next Gen submission for a rushed store launch.

### September 27: build-in-public evidence

Only publish truthful tests and lessons already gathered. No fabricated traction.

### September 28: record

Public two-minute maximum demo using original patterns, no trademarks or copyrighted music.

### September 29

Final screenshot at 1179×2556 without device frame, 1024×1024 icon, repo cleanup, judge unlock instructions.

### September 30 before 7:00 PM PT

Submit with almost five hours of buffer.

## Demo storyboard, maximum 2:00

- **0:00-0:08:** Stock camera view of an original test display with dark bars rolling through it.
- **0:08-0:18:** Open the app on the same physical target in one continuous shot. Diagnostic says unstable 60/120-family interference.
- **0:18-0:32, winning moment:** Tap Sync. Candidate shutter values sweep, lock, and the bars disappear live. Hold the corrected frame.
- **0:32-0:47:** Drag before/after divider. Show measured banding-energy reduction, not just aesthetics.
- **0:47-1:04:** Point at a high-frequency checker/text pattern. Moiré loupe finds narrow spectral peaks; targeted filter removes them while text edges remain.
- **1:04-1:17:** Source frequency changes. Lock turns amber, re-estimates, and recovers rather than silently recording bad footage.
- **1:17-1:31:** Record/export workflow. RevenueCat sandbox purchase unlocks full-quality export; cancel/restore behavior flashes quickly.
- **1:31-1:43:** Compatibility/evaluation table and one unsupported case labeled red.
- **1:43-1:52:** Show source code, RevenueCat entitlement configuration, and on-device/no-upload architecture.
- **1:52-2:00:** End on side-by-side clips and one sentence: “The screen was never broken. The timing was.”

Do not include Apple, game, streaming-service, or other third-party trademarks in the recorded targets.

## Rubric map and award strategy

### RevenueCat Design Award

- Camera interaction, live split, scopes, motion, haptics, and honest state design.
- Technically original correction shown visually.
- Instrument-like craft independent of market size.

### Next Gen Award

- Active-student eligibility route.
- Open-source native code and clear technical explanation.
- Working device video without depending on a paid developer account/store listing, subject to the final published Next Gen rules.
- Scope shows significant original engineering while remaining finishable.

### HAMM Award

- RevenueCat gates high-value export and advanced processing after the app proves value.
- Lifetime-first offering matches an instrument better than a forced subscription.
- Remote offerings, entitlement, restore, offline, judge access, and failure states are fully implemented.
- No revenue claim without real volume.

### Grand Prize

Not the initial optimization target. It is traction-based. Enter only with actual public release, adoption, and measured growth; do not present downloads or sandbox purchases as momentum.

### Most Viral / #BuildInPublic

The before/after loop is naturally shareable and development produces real lessons about camera timing. These categories become credible only if public posts and response actually occur.

## Submission checklist

- Working iOS/iPadOS app with RevenueCat SDK powering at least one purchase/entitlement.
- Next Gen rules rechecked once published; do not assume every general-store requirement is waived.
- Text description of features/functionality.
- Public video no longer than two minutes.
- Video shows app on device.
- No unauthorized trademarks, music, or material.
- If entering general awards through a store release: public app URL, first version released Aug 1-Sep 30, free trial or judge promo code.
- 1024×1024 icon.
- At least one 1179×2556 screenshot with no device frame.
- Public source for Next Gen.
- RevenueCat product/entitlement and judge-unlock instructions tested.
- 3:2 Devpost thumbnail and gallery.
- README: supported devices, calibration limits, metrics, architecture, privacy, build steps, RevenueCat sandbox, known failures.

## Repository layout contract

ADR-0001 establishes the implementation layout. Portable domain and policy code lives under `Sources/<Area>Domain`; deterministic package and property tests live under the root `Tests/` directory; architecture decisions live under the root `adr/` directory. Apple-framework and provider adapters belong under `App/<Area>/` only when they contain working application code. An `App/` directory is therefore a future boundary, not an empty scaffold or evidence that the signed app exists.

```text
/
├── Package.swift
├── Sources/
│   ├── CaptureDomain/
│   ├── RuntimeConfiguration/
│   └── <Area>Domain/          # Camera, Analysis, Metal, UI, Purchases, Export, Evaluation
├── Tests/                     # package, property, integration, and later app/E2E tests
├── App/                       # future; only working application/adapters under <Area>/
│   └── <Area>/
├── adr/                       # architecture decisions, including ADR-0001
├── docs/                      # runbooks, threat models, evaluation documentation
├── evidence/                  # regenerable artifacts only
├── scripts/                   # repository-local development harness
└── tools/                     # verification and policy tooling
```

## What would make this lose anyway

1. **The before/after only works on one staged display.** Publish a real test matrix and failures.
2. **Correction is just a manually hardcoded shutter.** Live analysis and candidate scoring must be visible and tested.
3. **Moiré filter blurs text.** Measure edge/detail preservation and keep strength conservative.
4. **The paid gate arrives before proof.** Free diagnosis and preview are non-negotiable.
5. **RevenueCat is bolted on in the final week.** Purchases and restoration must be tested as product states.
6. **The app overclaims source frequency or device coverage.** Estimates and unsupported hardware need labels.
7. **The video violates trademark/music rules.** Use entirely original test patterns and silent/original audio.
8. **It targets every award and wins none.** Design + Next Gen stay primary.
9. **No creator uses it before submission.** External tests must shape the final UI and be reported honestly.
10. **A public store release consumes the schedule.** Preserve the lower-friction student path unless store readiness is real.
11. **The app is visually technical but unpleasant.** The diagnostic depth must collapse into one calm correction action.

The winning version shows a physical defect vanish in real time, then proves the result without pretending every screen and phone is solved.
