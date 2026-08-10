import CaptureDomain

/// The one entitlement recognized by the domain. Provider strings never cross
/// this boundary as open-ended authorization values.
public enum EntitlementID: String, Sendable, Hashable {
  case proCapture = "pro_capture"
}

public enum EntitlementProvider: String, Sendable, Hashable {
  case revenueCat
}

/// Opaque evidence that the package-owned provider adapter verified the current
/// RevenueCat entitlement response. Ordinary callers cannot construct it.
public struct VerifiedProEntitlement: Sendable, Hashable {
  public let entitlementID: EntitlementID
  public let provider: EntitlementProvider
  public let verificationReference: StableIdentifier

  fileprivate init(
    entitlementID: EntitlementID,
    provider: EntitlementProvider,
    verificationReference: StableIdentifier
  ) {
    self.entitlementID = entitlementID
    self.provider = provider
    self.verificationReference = verificationReference
  }
}

/// Capability reserved for the RevenueCat adapter after SDK/provider response
/// verification. It refuses every identifier except the canonical entitlement.
package struct ProviderEntitlementIssuer: Sendable {
  package init() {}

  package func verifyActiveEntitlement(
    providerEntitlementIdentifier: String,
    verificationReference: String
  ) throws -> VerifiedProEntitlement {
    guard providerEntitlementIdentifier == EntitlementID.proCapture.rawValue else {
      throw PurchasesDomainError.unrecognizedEntitlement
    }
    return VerifiedProEntitlement(
      entitlementID: .proCapture,
      provider: .revenueCat,
      verificationReference: try StableIdentifier(verificationReference)
    )
  }
}

public enum EntitlementState: Sendable, Equatable {
  case free
  case pro(VerifiedProEntitlement)
}

public enum PurchaseFailureKind: String, Sendable, Equatable, CaseIterable {
  case networkUnavailable
  case storeUnavailable
  case paymentNotAllowed
  case verificationFailed
  case unknownProviderFailure
}

public enum PurchaseAttemptOutcome: Sendable, Equatable {
  case purchased(VerifiedProEntitlement)
  case restored(VerifiedProEntitlement)
  case cancelledByUser
  case failed(PurchaseFailureKind)
}

/// There is intentionally no unavailable case: the free proof camera is a
/// product invariant and cannot be disabled by purchase state.
public enum FreeCameraAccess: String, Sendable, Equatable {
  case liveDiagnosisAndProofCaptureAvailable
}

public enum AdvancedOutputAccess: Sendable, Equatable {
  case lockedAfterProof
  case unlocked(VerifiedProEntitlement)
}

public struct ProductAccess: Sendable, Equatable {
  public let freeCamera: FreeCameraAccess
  public let advancedOutput: AdvancedOutputAccess

  fileprivate init(
    freeCamera: FreeCameraAccess,
    advancedOutput: AdvancedOutputAccess
  ) {
    self.freeCamera = freeCamera
    self.advancedOutput = advancedOutput
  }
}

public enum EntitlementPolicy {
  public static func access(for entitlement: EntitlementState) -> ProductAccess {
    switch entitlement {
    case .free:
      ProductAccess(
        freeCamera: .liveDiagnosisAndProofCaptureAvailable,
        advancedOutput: .lockedAfterProof
      )
    case .pro(let verifiedEntitlement):
      ProductAccess(
        freeCamera: .liveDiagnosisAndProofCaptureAvailable,
        advancedOutput: .unlocked(verifiedEntitlement)
      )
    }
  }

  public static func access(
    after outcome: PurchaseAttemptOutcome,
    previousEntitlement: EntitlementState
  ) -> ProductAccess {
    switch outcome {
    case .purchased(let entitlement), .restored(let entitlement):
      access(for: .pro(entitlement))
    case .cancelledByUser, .failed:
      // A provider failure cannot downgrade an already verified entitlement,
      // and it can never remove the free proof camera.
      access(for: previousEntitlement)
    }
  }
}

public struct AppBuildNumber: Sendable, Hashable, Comparable {
  public let rawValue: UInt32

  public init(_ rawValue: UInt32) throws {
    guard rawValue > 0 else {
      throw PurchasesDomainError.zeroAppBuildNumber
    }
    self.rawValue = rawValue
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.rawValue < rhs.rawValue
  }
}

public enum PurchaseCompatibilityStatus: String, Sendable, Equatable {
  case supported
  case unsupported
  case unverified
}

/// Closed, scalar-only RevenueCat attributes. No string dictionary, frame,
/// bytes, media artifact, or user content can enter this representation.
public struct PurchaseAttributeSnapshot: Sendable, Equatable {
  public let appBuildNumber: AppBuildNumber
  public let compatibilityStatus: PurchaseCompatibilityStatus

  fileprivate init(
    appBuildNumber: AppBuildNumber,
    compatibilityStatus: PurchaseCompatibilityStatus
  ) {
    self.appBuildNumber = appBuildNumber
    self.compatibilityStatus = compatibilityStatus
  }
}

/// Package-owned RevenueCat serialization adapters issue the closed snapshot.
package enum PurchaseAttributeIssuer {
  package static func issue(
    appBuildNumber: AppBuildNumber,
    compatibilityStatus: PurchaseCompatibilityStatus
  ) -> PurchaseAttributeSnapshot {
    PurchaseAttributeSnapshot(
      appBuildNumber: appBuildNumber,
      compatibilityStatus: compatibilityStatus
    )
  }
}

public enum PurchasesDomainError: CodedDomainError, Equatable {
  case unrecognizedEntitlement
  case zeroAppBuildNumber

  public var code: String {
    switch self {
    case .unrecognizedEntitlement: "purchases.entitlement.unrecognized"
    case .zeroAppBuildNumber: "purchases.attribute.build_number.zero"
    }
  }

  public var safeMessage: String {
    switch self {
    case .unrecognizedEntitlement:
      "The provider response does not contain the required entitlement."
    case .zeroAppBuildNumber:
      "The application build number must be greater than zero."
    }
  }
}
