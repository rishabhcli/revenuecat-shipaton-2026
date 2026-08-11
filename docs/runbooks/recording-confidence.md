# Runbook — recording confidence (invariant I2)

> **Status:** the alert contract below is defined and encoded in types and tests.
> It is **not wired to a live alerting destination**, because no application
> target, telemetry exporter, or deployed environment exists yet. Wiring it is
> part of the `Camera`/`UI` adapter work and Tier 11, not of this document.
> Nothing here may be cited as evidence that alerting is operational.

## The invariant

**I2 — unsupported or unstable conditions are visible, and recording confidence
never turns green.**

A user filming a screen decides whether to keep or re-shoot a take based on one
indicator. A green indicator that is wrong is worse than no indicator: it causes
a lost shoot that the user only discovers later. Every rule here exists to make
the wrong-green state unreachable rather than unlikely.

## Where it is encoded

| Concern | Encoding |
|---|---|
| Only one green state exists | `RecordingConfidence.readyToRecord` in `Sources/AnalysisDomain/RecordingConfidence.swift` |
| Green carries proof, not a flag | Its payload is `VerifiedCorrection`, which only `CorrectionAssessment.evaluate` can mint |
| Only one component may decide | `RecordingConfidenceGate.evaluate` is the sole producer |
| A stale assessment cannot stay green | `RecordingFreshnessPolicy`, bounded to 1 ms – 2 s and validated at construction |
| A failing analysis component withdraws green | `AnalysisAvailability.degraded` and `.stalled` |
| The UI cannot invent green | `CorrectionIndicator.init(recording:)` is the only initializer, and `.positive` is reachable only from `.readyToRecord` |
| A free proof cannot come from a stale correction | `FreeProofIssuer.issue(from: RecordingConfidence)` requires `.readyToRecord` |
| Colour is never the only cue | Every tone is paired with a distinct `StatusShape`, `visibleText`, and `accessibilityLabel` |
| A lost check is caught at runtime | `RecordingConfidenceGate.postconditionHolds`, re-derived independently of the decision path |

## Which tests attack it

| Test | What it attacks | Declared cases |
|---|---|---|
| `testGreenRequiresVerifiedStableMeasuringAndFreshEvidence_2520DistinctCases` | The full cross product of assessment, source condition, component health, and age | 2,520 |
| `testThePostconditionGuardAgreesOnEveryCell_2520DistinctCases` | Divergence between the guard and the decision path | 2,520 |
| `testAComponentFailureWithdrawsGreenWithoutChangingTheAssessment_7DistinctFailures` | Fault injection: analysis degrades or stalls beneath a still-verified assessment | 7 |
| `testAnAgeingAssessmentLosesGreenAtTheDeclaredBoundary_4DistinctAges` | Fault injection: measurement stops and the assessment ages out | 4 |
| `testEvidenceFromAnotherSessionOrSourceIsRefused` | Evidence spliced across sessions or lenses | 2 |
| `testAnObservationOlderThanTheAssessmentIsRefused` | Clock skew and frame reordering | 1 |
| `testFreshnessBudgetRefusesValuesOutsideTheDeclaredRange_4DistinctBounds` | Configuring the freshness budget out of range | 4 |

All live in `Tests/FoundationPropertyTests/RecordingConfidencePropertyTests.swift`
and are re-run by `make test` and `make verify-all`.

## Behaviour at the boundary on malformed input

The gate cannot receive malformed input by construction: every field of
`RecordingConfidenceInputs` is a validated domain value or a closed enum, and
`LiveFrameReference` can only be minted by `LiveCaptureIssuer`. Adversarial but
well-typed inputs fail closed in this order, most severe first:

1. evidence from another capture session → `refused(.evidenceFromAnotherSession)`
2. evidence from another capture source → `refused(.evidenceFromAnotherSource)`
3. observation older than the assessment → `refused(.observationPrecedesAssessment)`
4. analysis stalled → `refused(.analysisStalled)`
5. assessment older than the freshness budget → `refused(.assessmentStale)`
6. assessment unavailable → `refused(.correctionUnavailable)`
7. source drifting, or analysis degraded → `recordWithoutCorrectionClaim`

There is no fallback branch and no default-to-green path.

## Alert contract

Both alerts are driven by `OperationalEvent` values that the gate already emits.
Every field is a scalar or a closed enum; no frame, pixel, identifier, or
timestamp enters telemetry, which is what invariant I5 requires.

### `recording_confidence_invariant_violated` — severity 1

- **Fires on:** any `OperationalEvent.invariantViolated` whose `invariant` is
  `I2`. Threshold is one event; there is no acceptable rate.
- **Means:** `postconditionHolds` rejected a decision the main path was about to
  return as green. The user was protected — the gate returned
  `refused(.invariantGuardTripped)` — but the two implementations disagree,
  which means a code change has broken a check.
- **User impact:** none directly; the indicator refuses instead of showing
  green. The defect is that the invariant now depends on the guard alone.
- **Response:** treat as a release blocker. Identify the change that made
  `decide` and `postconditionHolds` disagree, add the case to the 2,520-cell
  matrix, fix the decision path, and only then close the alert. Do not
  disable, weaken, or rate-limit this alert to reduce noise.

### `recording_confidence_withheld_rate` — severity 3

- **Fires on:** the fraction of `recordingConfidenceEvaluated` events whose
  `outcome` is not `readyToRecord`, measured over a rolling window, exceeding
  the threshold set when real usage data exists. **No threshold is declared
  here, because none has been measured; inventing one would be a fabricated
  number.**
- **Means:** users are being told, correctly, that the app cannot confirm a
  correction. The refusal is working; the question is why so many scenes reach
  it.
- **Response:** group by `reason`. `analysisStalled` or `assessmentStale`
  dominating points at the capture pipeline, not the source. `correctionUnavailable`
  dominating points at the exposure search or at genuinely unsupported sources,
  and the answer may be a `SUPPORT_MATRIX.md` row rather than a code change.
  `analysisDegraded` dominating points at thermal or backpressure budgets.

## What a responder must not do

- Do not widen `RecordingFreshnessPolicy` to clear an alert. The budget is the
  promise that a green indicator describes the scene in front of the camera now.
- Do not add a green state for "probably still fine".
- Do not let a UI layer construct `CorrectionIndicator` from anything but a
  `RecordingConfidence`.
- Do not silence `recording_confidence_invariant_violated`.

## Open work before this runbook is operational

1. An application target that runs the gate on real capture callbacks.
2. A telemetry exporter that carries `OperationalEvent` to a real destination
   with correlation IDs (Tier 11).
3. A measured threshold for `recording_confidence_withheld_rate`.
4. A device-level end-to-end test that observes the indicator withdrawing green
   when a real source drifts, which is release gate G4.
