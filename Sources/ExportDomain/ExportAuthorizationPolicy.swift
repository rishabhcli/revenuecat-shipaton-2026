import CaptureDomain
import MetalDomain
import PurchasesDomain

public enum ExportQuality: String, Sendable, Equatable {
  case proofPreview
  case fullResolution
  case advancedMoireProcessed
}

public enum MediaPrivacyDisposition: String, Sendable, Equatable {
  case onDeviceUntilUserInitiatedExport
}

/// Export intent is bound to a capture-issued artifact identity.
public struct ExportRequest: Sendable, Equatable {
  public let artifactID: MediaArtifactID
  public let quality: ExportQuality
  public let privacyDisposition: MediaPrivacyDisposition

  public init(artifactID: MediaArtifactID, quality: ExportQuality) {
    self.artifactID = artifactID
    self.quality = quality
    privacyDisposition = .onDeviceUntilUserInitiatedExport
  }
}

public enum ExportRefusal: String, Sendable, Equatable {
  case advancedOutputRequiresEntitlement
  case detailPreservationNotVerified
  case suppressionArtifactMismatch
}

public enum ExportAuthorizationBasis: Sendable, Equatable {
  case freeProof
  case verifiedEntitlement(VerifiedProEntitlement)
  case boundedMoire(
    entitlement: VerifiedProEntitlement,
    suppression: BoundedSuppression
  )
}

/// Opaque authorization issued only by the policy after all applicable tokens
/// are checked. A bare public success value cannot be forged.
public struct AuthorizedExport: Sendable, Equatable {
  public let artifactID: MediaArtifactID
  public let quality: ExportQuality
  public let privacyDisposition: MediaPrivacyDisposition
  public let basis: ExportAuthorizationBasis

  fileprivate init(request: ExportRequest, basis: ExportAuthorizationBasis) {
    artifactID = request.artifactID
    quality = request.quality
    privacyDisposition = request.privacyDisposition
    self.basis = basis
  }
}

public enum ExportAuthorization: Sendable, Equatable {
  case allowed(AuthorizedExport)
  case refused(ExportRefusal)
}

public enum ExportAuthorizationPolicy {
  public static func authorize(
    request: ExportRequest,
    access: ProductAccess,
    moireDecision: MoireSuppressionDecision?
  ) -> ExportAuthorization {
    switch request.quality {
    case .proofPreview:
      // Free proof remains available before purchase and after any purchase
      // cancellation/failure.
      return .allowed(AuthorizedExport(request: request, basis: .freeProof))

    case .fullResolution:
      guard case .unlocked(let entitlement) = access.advancedOutput else {
        return .refused(.advancedOutputRequiresEntitlement)
      }
      return .allowed(
        AuthorizedExport(
          request: request,
          basis: .verifiedEntitlement(entitlement)
        )
      )

    case .advancedMoireProcessed:
      guard case .unlocked(let entitlement) = access.advancedOutput else {
        return .refused(.advancedOutputRequiresEntitlement)
      }
      guard case .apply(let suppression)? = moireDecision else {
        return .refused(.detailPreservationNotVerified)
      }
      guard suppression.artifactID == request.artifactID else {
        return .refused(.suppressionArtifactMismatch)
      }
      return .allowed(
        AuthorizedExport(
          request: request,
          basis: .boundedMoire(
            entitlement: entitlement,
            suppression: suppression
          )
        )
      )
    }
  }
}
