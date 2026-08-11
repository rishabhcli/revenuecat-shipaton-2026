/// Operational events are intentionally closed and scalar-only. Camera frame or
/// pixel types cannot cross this boundary into analytics or purchase attributes.
public enum OperationalEvent: Sendable, Equatable {
  case configurationAccepted(ConfigurationAcceptedEvent)
  case configurationRefused(errorCode: StableIdentifier)
  case correctionAssessed(CorrectionAssessedEvent)
  case processingRefused(reason: ProcessingRefusal)
  case recordingConfidenceEvaluated(RecordingConfidenceEvent)
  case invariantViolated(InvariantViolationEvent)

  public enum CorrectionOutcome: String, Sendable, Equatable {
    case verified
    case unstable
    case unsupported
    case insufficientEvidence
  }

  public enum ProcessingRefusal: String, Sendable, Equatable {
    case detailPreservationLimitExceeded
    case measurementUnavailable
    case thermalBudgetExceeded
  }

  public enum RecordingOutcome: String, Sendable, Equatable, CaseIterable {
    case readyToRecord
    case recordWithoutCorrectionClaim
    case refused
  }

  /// Closed reason set. `none` accompanies `readyToRecord` only.
  public enum RecordingReason: String, Sendable, Equatable, CaseIterable {
    case none
    case sourceDrift
    case analysisDegraded
    case correctionUnavailable
    case analysisStalled
    case assessmentStale
    case evidenceFromAnotherSession
    case evidenceFromAnotherSource
    case observationPrecedesAssessment
    case invariantGuardTripped
  }
}

/// The domain invariants from `AGENTS.md`, identified so that a violation is a
/// named, alertable signal rather than an anonymous log line.
public enum DomainInvariant: String, Sendable, Equatable, CaseIterable {
  case correctionMeasuredOnLiveFrames = "I1"
  case recordingConfidenceNeverFalselyGreen = "I2"
  case diagnosticsDropBeforeRecordedFrames = "I3"
  case moireSuppressionBoundedByDetailPreservation = "I4"
  case noFramePixelsInTelemetry = "I5"
  case freeProofPrecedesPurchase = "I6"
  case purchaseFailurePreservesFreeCamera = "I7"
  case claimsNameDeviceLensFormatSource = "I8"
}

/// The specific runtime guard that detected a violation.
public enum InvariantGuard: String, Sendable, Equatable, CaseIterable {
  case recordingConfidencePostcondition
}

/// Emitted only when a runtime guard proves an invariant was about to be
/// broken. Any occurrence is a defect: see `docs/runbooks/`.
public struct InvariantViolationEvent: Sendable, Equatable {
  public let invariant: DomainInvariant
  public let guardIdentifier: InvariantGuard

  package init(invariant: DomainInvariant, guardIdentifier: InvariantGuard) {
    self.invariant = invariant
    self.guardIdentifier = guardIdentifier
  }
}

/// Scalar-only record of one recording-confidence decision. Frame contents,
/// identifiers, and timestamps never enter it; only the decision, its closed
/// reason, and a bounded age do.
public struct RecordingConfidenceEvent: Sendable, Equatable {
  public let outcome: OperationalEvent.RecordingOutcome
  public let reason: OperationalEvent.RecordingReason
  public let assessmentAgeMilliseconds: Int

  package init(
    outcome: OperationalEvent.RecordingOutcome,
    reason: OperationalEvent.RecordingReason,
    assessmentAgeNanoseconds: UInt64
  ) {
    self.outcome = outcome
    self.reason = reason
    // Constructed from an unsigned duration and clamped, so the recorded age is
    // valid by construction and this initializer cannot fail.
    assessmentAgeMilliseconds = Int(
      min(assessmentAgeNanoseconds / 1_000_000, UInt64(Int.max))
    )
  }
}

public struct ConfigurationAcceptedEvent: Sendable, Equatable {
  public let serviceCount: Int

  package init(serviceCount: Int) throws {
    guard serviceCount > 0 else {
      throw OperationalEventError.nonPositiveCount
    }
    self.serviceCount = serviceCount
  }
}

public struct CorrectionAssessedEvent: Sendable, Equatable {
  public let algorithmVersion: AlgorithmVersion
  public let sampledFrameCount: Int
  public let outcome: OperationalEvent.CorrectionOutcome

  package init(
    algorithmVersion: AlgorithmVersion,
    sampledFrameCount: Int,
    outcome: OperationalEvent.CorrectionOutcome
  ) throws {
    guard sampledFrameCount > 0 else {
      throw OperationalEventError.nonPositiveCount
    }
    self.algorithmVersion = algorithmVersion
    self.sampledFrameCount = sampledFrameCount
    self.outcome = outcome
  }
}

public enum OperationalEventError: CodedDomainError, Equatable {
  case nonPositiveCount

  public var code: String { "operational_event.count.non_positive" }

  public var safeMessage: String {
    "Operational event counts must be greater than zero."
  }
}
