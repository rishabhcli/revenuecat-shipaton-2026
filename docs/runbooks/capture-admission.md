# Runbook — capture admission (invariant I3)

> **Status:** the alert contract below is defined and encoded in types and tests.
> It is **not wired to a live alerting destination**, because no application
> target, capture session, telemetry exporter, or deployed environment exists
> yet. Nothing here may be cited as evidence that alerting is operational, that
> frames have been recorded, or that any frame budget has been measured.

## The invariant

**I3 — diagnostic work drops before recorded frames.**

A recorded frame is irreplaceable. Once it is not written it is gone from the
user's take, and the user usually discovers that after the event they were
filming has ended. Diagnostic work is recomputable from the next frame that
arrives. Any capacity contest between the two therefore has a fixed winner, and
the losing side is always diagnostics.

## Where it is encoded

| Concern | Encoding |
|---|---|
| Capacity goes to recorded frames first | `CaptureAdmissionPolicy.decide` in `Sources/CameraDomain/CaptureBackpressure.swift` |
| Starvation is a named, checkable property | `CaptureAdmission.starvesRecordedFrames` |
| A starving admission is not representable | `CaptureAdmission` has only a `fileprivate` initializer, so the policy is its sole producer |
| Pressure removes diagnostics entirely | `CapturePressure`; any non-nominal value admits zero diagnostic jobs |
| Corrupted queue depths never reach the arithmetic | `CaptureLoad.maximumQueueDepth`, refused as `camera.capture_load.queue_depth_too_large` |
| Negative depths never reach the arithmetic | `camera.capture_load.negative_count` |
| A lost check is caught at runtime | `CaptureAdmissionPolicy.postconditionHolds`, re-derived independently of the decision path |
| The decision is observable | `OperationalEvent.captureAdmissionDecided`, scalar counts and a closed pressure value only |

## Which tests attack it

| Test | What it attacks | Declared cases |
|---|---|---|
| `testRecordedFramesConsumeCapacityBeforeDiagnostics_163_840DistinctCases` | The full cross product of both queue depths, capacity, and pressure; asserts zero starving cells | 163,840 |
| `testNonNominalPressureStopsDiagnosticWorkEntirely_4DistinctPressures` | Fault injection: the pipeline is under pressure while capacity looks abundant | 4 |
| `testNoCapacityDefersEveryRecordedFrameAndRunsNoDiagnostics` | Fault injection: capacity collapses to zero with both queues full | 1 |
| `testThePostconditionGuardRejectsStarvationAndMiscounting` | Divergence between the guard and the decision path | 3 |
| `testQueueDepthsAboveTheSupportedMaximumAreRefused_6DistinctCases` | Corrupted counts, including `Int.max`, at the ingestion boundary | 6 |
| `testCaptureLoadRefusesNegativeCounts_3_072DistinctCases` | Negative counts at the ingestion boundary | 3,072 |

All live in `Tests/FoundationPropertyTests/CameraAdmissionPropertyTests.swift`
and are re-run by `make test` and `make verify-all`.

## Behaviour at the boundary on malformed input

`CaptureLoad` is the only way to describe a load, and it refuses before any
arithmetic runs:

1. any negative count → `CameraDomainError.negativeQueueCount`
2. any count above `maximumQueueDepth` (1,000,000), including `Int.max` →
   `CameraDomainError.queueDepthAboveSupportedMaximum`

Both are typed refusals with stable codes and fixed safe messages. There is no
clamping, no saturation, and no "best effort" branch: a count that cannot occur
in a real pipeline is treated as corrupted state, not as a large number.

## Alert contract

### `capture_admission_invariant_violated` — severity 1

- **Fires on:** any `OperationalEvent.invariantViolated` whose `invariant` is
  `I3`. Threshold is one event; there is no acceptable rate.
- **Means:** `postconditionHolds` rejected the admission the arithmetic
  produced. The user was protected — the policy fell back to admitting only
  recorded frames and dropping every diagnostic job — but the two
  implementations disagree, so a change has broken a check.
- **Response:** treat as a release blocker. Find the change that made `decide`
  and `postconditionHolds` disagree, add the case to the 163,840-cell matrix,
  fix the arithmetic, and only then close the alert. Never silence or
  rate-limit this alert.

### `recorded_frames_deferred_rate` — severity 2

- **Fires on:** the fraction of `captureAdmissionDecided` events with
  `recordedFramesDeferred > 0`, over a rolling window, exceeding the threshold
  set when real capture data exists. **No threshold is declared here, because
  none has been measured on real hardware; inventing one would be a fabricated
  number.**
- **Means:** capacity is short for recording itself, which is upstream of this
  invariant. Diagnostics are already at zero in these decisions, so there is no
  further work to shed — the next lever is resolution, frame rate, or codec.
- **Response:** group by `pressure`. `thermalThrottling` points at the sustained
  recording envelope and release gate G2. `storageBandwidthLimited` points at
  the writer. `analysisBacklog` should be impossible while diagnostics are at
  zero, so seeing it means work is being queued outside this admission point,
  which is a defect.

### `diagnostics_starved_by_pressure_rate` — severity 4, informational

- **Fires on:** sustained non-nominal `pressure` in `captureAdmissionDecided`.
- **Means:** correction quality is degrading by design, and invariant I2 should
  already be showing the user a non-green indicator through
  `AnalysisAvailability.degraded`. Cross-check
  [recording-confidence.md](./recording-confidence.md): if I3 reports sustained
  pressure while I2 reports `measuring`, the two views disagree and that is a
  defect in the adapter that feeds them.

## What a responder must not do

- Do not give diagnostics a reserved share of capacity "so the correction keeps
  working". The correction is worth nothing if the take is not recorded.
- Do not raise `maximumQueueDepth` to make a refusal stop firing. A depth above
  it means a count is corrupted, not that the queue is deep.
- Do not construct a `CaptureAdmission` outside the policy.
- Do not silence `capture_admission_invariant_violated`.

## Open work before this runbook is operational

1. An `AVCaptureSession` adapter that calls this policy on real capture
   callbacks with a real measure of available capacity.
2. Frame-accounting instrumentation that proves the deferred count matches what
   the recorder actually wrote, which is what release gate G2 requires.
3. A measured threshold for `recorded_frames_deferred_rate` on real hardware,
   named by device, lens, format, and source as invariant I8 requires.
4. A sustained-recording thermal test that exercises `thermalThrottling`
   against a real device rather than a constructed value.
