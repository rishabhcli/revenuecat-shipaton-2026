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
public struct CorrectionIndicator: Sendable, Equatable {
  public let tone: StatusTone
  public let shape: StatusShape
  public let visibleText: String
  public let accessibilityLabel: String

  public init(confidence: CorrectionConfidence) {
    switch confidence {
    case .verified:
      tone = .positive
      shape = .checkmarkCircle
      visibleText = "Stable correction verified"
    case .unstable:
      tone = .caution
      shape = .warningTriangle
      visibleText = "Source drift detected"
    case .unavailable(let reason):
      tone = .refusal
      shape = .xOctagon
      visibleText = Self.refusalText(for: reason)
    }
    accessibilityLabel = "Correction status: \(visibleText)"
  }

  private static func refusalText(for refusal: CorrectionRefusal) -> String {
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
  package static func issue(
    from confidence: CorrectionConfidence
  ) throws -> VerifiedFreeProof {
    guard case .verified(let correction) = confidence else {
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
