import CameraDomain
import CaptureDomain

/// Health of the analysis component that produces correction evidence.
///
/// A correction assessment describes frames that were already measured. It says
/// nothing about whether measurement is still happening, so availability is
/// carried separately and can withdraw a green state that was true a moment ago.
public enum AnalysisAvailability: Sendable, Equatable {
  case measuring
  case degraded(AnalysisDegradation)
  case stalled(AnalysisStall)
}

/// Analysis is still producing results, but under a condition that makes a
/// verified claim unsafe to present as a settled fact.
public enum AnalysisDegradation: String, Sendable, Equatable, CaseIterable {
  case diagnosticsDroppedForRecording
  case thermalBudgetExceeded
  case frameSamplerRestarted
  case measurementQueueOverflowed
}

/// Analysis has stopped producing results entirely.
public enum AnalysisStall: String, Sendable, Equatable, CaseIterable {
  case frameDeliveryStopped
  case measurementWorkerUnresponsive
  case captureSessionInterrupted
}

/// How old a correction assessment may be and still back a green state.
public struct RecordingFreshnessPolicy: Sendable, Equatable {
  public static let smallestPermittedAgeNanoseconds: UInt64 = 1_000_000
  public static let largestPermittedAgeNanoseconds: UInt64 = 2_000_000_000

  public let maximumAssessmentAgeNanoseconds: UInt64

  public init(maximumAssessmentAgeNanoseconds: UInt64) throws {
    guard maximumAssessmentAgeNanoseconds >= Self.smallestPermittedAgeNanoseconds,
      maximumAssessmentAgeNanoseconds <= Self.largestPermittedAgeNanoseconds
    else {
      throw AnalysisDomainError.freshnessBudgetOutsideSupportedRange(
        smallestNanoseconds: Self.smallestPermittedAgeNanoseconds,
        largestNanoseconds: Self.largestPermittedAgeNanoseconds
      )
    }
    self.maximumAssessmentAgeNanoseconds = maximumAssessmentAgeNanoseconds
  }
}

/// Why recording may proceed but must not be labelled as corrected.
public enum RecordingCaution: Sendable, Equatable {
  case sourceDrift
  case analysisDegraded(AnalysisDegradation)
}

/// Why no correction claim can be made at all.
public enum RecordingRefusal: Sendable, Equatable {
  case correctionUnavailable(CorrectionRefusal)
  case analysisStalled(AnalysisStall)
  case assessmentStale(ageMilliseconds: Int)
  case evidenceFromAnotherSession
  case evidenceFromAnotherSource
  case observationPrecedesAssessment
  case invariantGuardTripped(InvariantGuard)
}

/// The recording-confidence state.
///
/// `readyToRecord` is the only state a user interface may render as a positive
/// tone, it carries a `VerifiedCorrection` that only `CorrectionAssessment` can
/// mint, and it is produced by `RecordingConfidenceGate` alone. Every other
/// value of this type is explicitly non-green.
public enum RecordingConfidence: Sendable, Equatable {
  case readyToRecord(VerifiedCorrection)
  case recordWithoutCorrectionClaim(RecordingCaution)
  case refused(RecordingRefusal)

  public var isGreen: Bool {
    if case .readyToRecord = self { return true }
    return false
  }
}

/// A gate decision together with the telemetry that records it.
public struct RecordingConfidenceDecision: Sendable, Equatable {
  public let confidence: RecordingConfidence
  public let events: [OperationalEvent]

  fileprivate init(confidence: RecordingConfidence, events: [OperationalEvent]) {
    self.confidence = confidence
    self.events = events
  }
}

/// Everything the gate is allowed to consider. No pixels, buffers, or framework
/// state can reach this boundary, and every field is a validated domain value.
public struct RecordingConfidenceInputs: Sendable, Equatable {
  public let assessment: CorrectionConfidence
  public let assessedThrough: LiveFrameReference
  public let latestObservedFrame: LiveFrameReference
  public let sourceCondition: SourceCondition
  public let availability: AnalysisAvailability

  public init(
    assessment: CorrectionConfidence,
    assessedThrough: LiveFrameReference,
    latestObservedFrame: LiveFrameReference,
    sourceCondition: SourceCondition,
    availability: AnalysisAvailability
  ) {
    self.assessment = assessment
    self.assessedThrough = assessedThrough
    self.latestObservedFrame = latestObservedFrame
    self.sourceCondition = sourceCondition
    self.availability = availability
  }
}

/// The single boundary that decides whether recording confidence may be green.
///
/// Invariant I2: unsupported or unstable conditions stay visible and recording
/// confidence never turns green. Every ordering here fails closed, and the
/// decision is re-checked by an independent postcondition before any green
/// value is returned, so a later refactor that loses a check is caught at
/// runtime and reported rather than shown to a user as a verified correction.
public enum RecordingConfidenceGate {
  public static func evaluate(
    _ inputs: RecordingConfidenceInputs,
    policy: RecordingFreshnessPolicy
  ) -> RecordingConfidenceDecision {
    let ageNanoseconds = assessmentAgeNanoseconds(inputs)
    let confidence = decide(inputs, policy: policy, ageNanoseconds: ageNanoseconds)

    guard case .readyToRecord = confidence else {
      return decision(confidence, ageNanoseconds: ageNanoseconds, violated: false)
    }
    guard postconditionHolds(inputs, policy: policy) else {
      return decision(
        .refused(.invariantGuardTripped(.recordingConfidencePostcondition)),
        ageNanoseconds: ageNanoseconds,
        violated: true
      )
    }
    return decision(confidence, ageNanoseconds: ageNanoseconds, violated: false)
  }

  /// Independent re-derivation of every condition a green state requires.
  ///
  /// Deliberately duplicated rather than factored out of `decide`: a guard that
  /// shares its implementation with the code it guards cannot detect that the
  /// implementation changed.
  package static func postconditionHolds(
    _ inputs: RecordingConfidenceInputs,
    policy: RecordingFreshnessPolicy
  ) -> Bool {
    guard case .verified = inputs.assessment else { return false }
    guard case .stable = inputs.sourceCondition else { return false }
    guard case .measuring = inputs.availability else { return false }
    guard inputs.assessedThrough.sessionID == inputs.latestObservedFrame.sessionID,
      inputs.assessedThrough.sourceID == inputs.latestObservedFrame.sourceID,
      inputs.assessedThrough.sequenceNumber <= inputs.latestObservedFrame.sequenceNumber,
      inputs.assessedThrough.monotonicTimestampNanoseconds
        <= inputs.latestObservedFrame.monotonicTimestampNanoseconds
    else {
      return false
    }
    return assessmentAgeNanoseconds(inputs) <= policy.maximumAssessmentAgeNanoseconds
  }

  private static func decide(
    _ inputs: RecordingConfidenceInputs,
    policy: RecordingFreshnessPolicy,
    ageNanoseconds: UInt64
  ) -> RecordingConfidence {
    guard inputs.assessedThrough.sessionID == inputs.latestObservedFrame.sessionID else {
      return .refused(.evidenceFromAnotherSession)
    }
    guard inputs.assessedThrough.sourceID == inputs.latestObservedFrame.sourceID else {
      return .refused(.evidenceFromAnotherSource)
    }
    guard
      inputs.assessedThrough.sequenceNumber <= inputs.latestObservedFrame.sequenceNumber,
      inputs.assessedThrough.monotonicTimestampNanoseconds
        <= inputs.latestObservedFrame.monotonicTimestampNanoseconds
    else {
      return .refused(.observationPrecedesAssessment)
    }
    if case .stalled(let stall) = inputs.availability {
      return .refused(.analysisStalled(stall))
    }
    guard ageNanoseconds <= policy.maximumAssessmentAgeNanoseconds else {
      return .refused(.assessmentStale(ageMilliseconds: milliseconds(ageNanoseconds)))
    }

    switch inputs.assessment {
    case .unavailable(let refusal):
      return .refused(.correctionUnavailable(refusal))
    case .unstable:
      return .recordWithoutCorrectionClaim(.sourceDrift)
    case .verified(let correction):
      guard case .stable = inputs.sourceCondition else {
        return .recordWithoutCorrectionClaim(.sourceDrift)
      }
      if case .degraded(let degradation) = inputs.availability {
        return .recordWithoutCorrectionClaim(.analysisDegraded(degradation))
      }
      return .readyToRecord(correction)
    }
  }

  private static func assessmentAgeNanoseconds(_ inputs: RecordingConfidenceInputs) -> UInt64 {
    let assessed = inputs.assessedThrough.monotonicTimestampNanoseconds
    let latest = inputs.latestObservedFrame.monotonicTimestampNanoseconds
    return latest >= assessed ? latest - assessed : 0
  }

  private static func milliseconds(_ nanoseconds: UInt64) -> Int {
    Int(min(nanoseconds / 1_000_000, UInt64(Int.max)))
  }

  private static func decision(
    _ confidence: RecordingConfidence,
    ageNanoseconds: UInt64,
    violated: Bool
  ) -> RecordingConfidenceDecision {
    var events: [OperationalEvent] = []
    if violated {
      events.append(
        .invariantViolated(
          InvariantViolationEvent(
            invariant: .recordingConfidenceNeverFalselyGreen,
            guardIdentifier: .recordingConfidencePostcondition
          )
        )
      )
    }
    events.append(
      .recordingConfidenceEvaluated(
        RecordingConfidenceEvent(
          outcome: confidence.operationalOutcome,
          reason: confidence.operationalReason,
          assessmentAgeNanoseconds: ageNanoseconds
        )
      )
    )
    return RecordingConfidenceDecision(confidence: confidence, events: events)
  }
}

extension RecordingConfidence {
  fileprivate var operationalOutcome: OperationalEvent.RecordingOutcome {
    switch self {
    case .readyToRecord: .readyToRecord
    case .recordWithoutCorrectionClaim: .recordWithoutCorrectionClaim
    case .refused: .refused
    }
  }

  fileprivate var operationalReason: OperationalEvent.RecordingReason {
    switch self {
    case .readyToRecord:
      .none
    case .recordWithoutCorrectionClaim(.sourceDrift):
      .sourceDrift
    case .recordWithoutCorrectionClaim(.analysisDegraded):
      .analysisDegraded
    case .refused(.correctionUnavailable):
      .correctionUnavailable
    case .refused(.analysisStalled):
      .analysisStalled
    case .refused(.assessmentStale):
      .assessmentStale
    case .refused(.evidenceFromAnotherSession):
      .evidenceFromAnotherSession
    case .refused(.evidenceFromAnotherSource):
      .evidenceFromAnotherSource
    case .refused(.observationPrecedesAssessment):
      .observationPrecedesAssessment
    case .refused(.invariantGuardTripped):
      .invariantGuardTripped
    }
  }
}
