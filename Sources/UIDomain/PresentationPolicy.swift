import AnalysisDomain
import CaptureDomain
import PurchasesDomain

public enum StatusTone: String, Sendable, Equatable {
  case positive
  case caution
  case refusal
}

public enum StatusShape: String, Sendable, Equatable {
  case checkmarkCircle
  case warningTriangle
  case xOctagon
}

/// Framework-neutral presentation contract. SwiftUI can render this value, but
/// confidence semantics remain testable without importing UI framework state.
///
/// Invariant I2: the only initializer takes a `RecordingConfidence`, so a
/// positive tone cannot be rendered from a correction assessment that has gone
/// stale, whose source has drifted, or whose analysis component has stopped.
/// Tone is always accompanied by a distinct shape and by text, so the state is
/// never carried by colour alone.
public struct CorrectionIndicator: Sendable, Equatable {
  public let tone: StatusTone
  public let shape: StatusShape
  public let visibleText: String
  public let accessibilityLabel: String

  public init(recording: RecordingConfidence) {
    switch recording {
    case .readyToRecord:
      tone = .positive
      shape = .checkmarkCircle
      visibleText = "Stable correction verified"
    case .recordWithoutCorrectionClaim(let caution):
      tone = .caution
      shape = .warningTriangle
      visibleText = Self.cautionText(for: caution)
    case .refused(let refusal):
      tone = .refusal
      shape = .xOctagon
      visibleText = Self.refusalText(for: refusal)
    }
    accessibilityLabel = "Correction status: \(visibleText)"
  }

  private static func cautionText(for caution: RecordingCaution) -> String {
    switch caution {
    case .sourceDrift:
      "Source drift detected"
    case .analysisDegraded(.diagnosticsDroppedForRecording):
      "Measuring less often to protect recording"
    case .analysisDegraded(.thermalBudgetExceeded):
      "Reduced measurement while the device is hot"
    case .analysisDegraded(.frameSamplerRestarted):
      "Measurement restarted; correction not re-confirmed"
    case .analysisDegraded(.measurementQueueOverflowed):
      "Measurement is behind the live preview"
    }
  }

  private static func refusalText(for refusal: RecordingRefusal) -> String {
    switch refusal {
    case .correctionUnavailable(let reason):
      correctionText(for: reason)
    case .analysisStalled:
      "Measurement stopped; correction is not confirmed"
    case .assessmentStale:
      "Correction is out of date for this scene"
    case .evidenceFromAnotherSession:
      "Correction evidence changed capture sessions"
    case .evidenceFromAnotherSource:
      "Correction evidence changed sources"
    case .observationPrecedesAssessment:
      "Correction evidence is out of order"
    case .invariantGuardTripped:
      "Correction could not be confirmed safely"
    }
  }

  private static func correctionText(for refusal: CorrectionRefusal) -> String {
    switch refusal {
    case .unsupported:
      "No reliable correction for this source"
    case .insufficientLiveEvidence:
      "Measuring more live frames"
    case .mismatchedCaptureSession:
      "Correction evidence changed capture sessions"
    case .mismatchedCaptureSource:
      "Correction evidence changed sources"
    case .algorithmVersionMismatch:
      "Correction evidence used different analysis versions"
    case .nonChronologicalEvidence:
      "Correction evidence is out of order"
    case .zeroBaselineEnergy:
      "No temporal banding measured"
    case .insufficientImprovement:
      "No material improvement measured"
    case .ambiguousCandidate:
      "No stable exposure candidate"
    }
  }
}

/// Opaque proof that the user has been shown an analysis-issued verified
/// correction. There is no public initializer or caller-selected proof state.
public struct VerifiedFreeProof: Sendable, Equatable {
  public let correction: VerifiedCorrection

  fileprivate init(correction: VerifiedCorrection) {
    self.correction = correction
  }
}

package enum FreeProofIssuer {
  /// A free proof is what the user actually saw work, so it is issued from the
  /// gated recording confidence rather than from a correction assessment that
  /// may since have gone stale or lost its source.
  package static func issue(
    from recording: RecordingConfidence
  ) throws -> VerifiedFreeProof {
    guard case .readyToRecord(let correction) = recording else {
      throw UIDomainError.correctionNotVerified
    }
    return VerifiedFreeProof(correction: correction)
  }
}

public enum PaywallPresentationDecision: Sendable, Equatable {
  case hiddenUntilFreeProof
  case mayPresentAfterVerifiedProof
  case hiddenBecauseAlreadyUnlocked
}

public enum PaywallPresentationPolicy {
  public static func decide(
    proof: VerifiedFreeProof?,
    access: ProductAccess
  ) -> PaywallPresentationDecision {
    if case .unlocked = access.advancedOutput {
      return .hiddenBecauseAlreadyUnlocked
    }
    guard proof != nil else {
      return .hiddenUntilFreeProof
    }
    return .mayPresentAfterVerifiedProof
  }
}

public enum UIDomainError: CodedDomainError, Equatable {
  case correctionNotVerified

  public var code: String { "ui.free_proof.correction_not_verified" }

  public var safeMessage: String {
    "A free proof requires a verified live correction."
  }
}
