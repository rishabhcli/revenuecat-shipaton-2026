/// Operational events are intentionally closed and scalar-only. Camera frame or
/// pixel types cannot cross this boundary into analytics or purchase attributes.
public enum OperationalEvent: Sendable, Equatable {
  case configurationAccepted(ConfigurationAcceptedEvent)
  case configurationRefused(errorCode: StableIdentifier)
  case correctionAssessed(CorrectionAssessedEvent)
  case processingRefused(reason: ProcessingRefusal)

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
