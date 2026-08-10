import CaptureDomain
import ExportDomain
import MetalDomain
import PurchasesDomain
import XCTest

final class PurchaseAndExportPropertyTests: XCTestCase {
  func testPurchaseCancellationAndFailurePreserveFreeCamera_12DistinctStateTransitions() throws {
    let entitlement = try verifiedEntitlement()
    let previousStates: [EntitlementState] = [.free, .pro(entitlement)]
    let outcomes: [PurchaseAttemptOutcome] =
      [.cancelledByUser] + PurchaseFailureKind.allCases.map(PurchaseAttemptOutcome.failed)
    let artifact = try MediaArtifactIssuer(issuerID: "purchase-tests").issue(
      artifactReference: "proof-artifact"
    )
    var evaluatedTransitions = 0

    for previousState in previousStates {
      for outcome in outcomes {
        let access = EntitlementPolicy.access(
          after: outcome,
          previousEntitlement: previousState
        )
        XCTAssertEqual(access, EntitlementPolicy.access(for: previousState))
        XCTAssertEqual(access.freeCamera, .liveDiagnosisAndProofCaptureAvailable)

        let authorization = ExportAuthorizationPolicy.authorize(
          request: ExportRequest(artifactID: artifact, quality: .proofPreview),
          access: access,
          moireDecision: nil
        )
        guard case .allowed(let authorized) = authorization else {
          XCTFail("A purchase cancellation/failure disabled proof export.")
          continue
        }
        XCTAssertEqual(authorized.artifactID, artifact)
        XCTAssertEqual(authorized.basis, .freeProof)
        evaluatedTransitions += 1
      }
    }

    XCTAssertEqual(evaluatedTransitions, 12)
  }

  func testProviderAdapterRefusesUnknownEntitlements_1_024DistinctIdentifiers() {
    let issuer = ProviderEntitlementIssuer()
    var evaluatedIdentifiers = 0

    for index in 0..<1_024 {
      let identifier = "unrecognized-entitlement-\(index)"
      assertThrowsEqual(
        PurchasesDomainError.unrecognizedEntitlement,
        try issuer.verifyActiveEntitlement(
          providerEntitlementIdentifier: identifier,
          verificationReference: "provider-check"
        )
      )
      evaluatedIdentifiers += 1
    }

    XCTAssertEqual(evaluatedIdentifiers, 1_024)
  }

  func testPurchasedAndRestoredOutcomesRequireAndPreserveVerifiedProviderToken() throws {
    let entitlement = try verifiedEntitlement()

    for outcome in [
      PurchaseAttemptOutcome.purchased(entitlement),
      .restored(entitlement),
    ] {
      let access = EntitlementPolicy.access(
        after: outcome,
        previousEntitlement: .free
      )
      XCTAssertEqual(access.advancedOutput, .unlocked(entitlement))
      XCTAssertEqual(access.freeCamera, .liveDiagnosisAndProofCaptureAvailable)
    }
  }

  func testPurchaseAttributeBoundaryUsesOnlyClosedScalarValues_3DistinctStatuses() throws {
    assertThrowsEqual(
      PurchasesDomainError.zeroAppBuildNumber,
      try AppBuildNumber(0)
    )
    let statuses: [PurchaseCompatibilityStatus] = [
      .supported,
      .unsupported,
      .unverified,
    ]
    var evaluatedStatuses = 0

    for status in statuses {
      let snapshot = PurchaseAttributeIssuer.issue(
        appBuildNumber: try AppBuildNumber(42),
        compatibilityStatus: status
      )
      XCTAssertEqual(snapshot.appBuildNumber.rawValue, 42)
      XCTAssertEqual(snapshot.compatibilityStatus, status)
      evaluatedStatuses += 1
    }

    XCTAssertEqual(evaluatedStatuses, 3)
    requireSendable(PurchaseAttributeSnapshot.self)
  }

  func testAdvancedExportRequiresEntitlementAndSameArtifactSuppressionProof() throws {
    let artifactIssuer = try MediaArtifactIssuer(issuerID: "export-tests")
    let requestedArtifact = try artifactIssuer.issue(artifactReference: "artifact-a")
    let otherArtifact = try artifactIssuer.issue(artifactReference: "artifact-b")
    let freeAccess = EntitlementPolicy.access(for: .free)
    let entitlement = try verifiedEntitlement()
    let proAccess = EntitlementPolicy.access(for: .pro(entitlement))
    let request = ExportRequest(
      artifactID: requestedArtifact,
      quality: .advancedMoireProcessed
    )

    XCTAssertEqual(
      ExportAuthorizationPolicy.authorize(
        request: request,
        access: freeAccess,
        moireDecision: nil
      ),
      .refused(.advancedOutputRequiresEntitlement)
    )
    XCTAssertEqual(
      ExportAuthorizationPolicy.authorize(
        request: request,
        access: proAccess,
        moireDecision: nil
      ),
      .refused(.detailPreservationNotVerified)
    )
    XCTAssertEqual(
      ExportAuthorizationPolicy.authorize(
        request: request,
        access: proAccess,
        moireDecision: .refuse(.edgeLossLimitExceeded)
      ),
      .refused(.detailPreservationNotVerified)
    )

    let policy = DetailPreservationPolicy(
      limits: try DetailPreservationLimits(
        maximumEdgeEnergyLoss: UnitInterval(0.2),
        maximumTextEdgeEnergyLoss: UnitInterval(0.1),
        maximumResidualInterferenceEnergy: UnitInterval(0.3),
        maximumSuppressionStrength: UnitInterval(0.8)
      )
    )
    let measurementIssuer = DetailPreservationMeasurementIssuer(
      algorithmVersion: try AlgorithmVersion("moire-v1")
    )

    func approvedDecision(for artifact: MediaArtifactID) throws -> MoireSuppressionDecision {
      policy.evaluate(
        requestedStrength: try UnitInterval(0.5),
        measurement: measurementIssuer.issue(
          artifactID: artifact,
          edgeEnergyLoss: try UnitInterval(0.1),
          textEdgeEnergyLoss: try UnitInterval(0.05),
          residualInterferenceEnergy: try UnitInterval(0.2)
        )
      )
    }

    XCTAssertEqual(
      ExportAuthorizationPolicy.authorize(
        request: request,
        access: proAccess,
        moireDecision: try approvedDecision(for: otherArtifact)
      ),
      .refused(.suppressionArtifactMismatch)
    )

    let authorization = ExportAuthorizationPolicy.authorize(
      request: request,
      access: proAccess,
      moireDecision: try approvedDecision(for: requestedArtifact)
    )
    guard case .allowed(let authorized) = authorization else {
      return XCTFail("Matching verified tokens should authorize advanced export.")
    }
    XCTAssertEqual(authorized.artifactID, requestedArtifact)
    XCTAssertEqual(authorized.quality, .advancedMoireProcessed)
    guard case .boundedMoire(let basisEntitlement, let suppression) = authorized.basis else {
      return XCTFail("Advanced export did not retain its authorization provenance.")
    }
    XCTAssertEqual(basisEntitlement, entitlement)
    XCTAssertEqual(suppression.artifactID, requestedArtifact)
  }

  func testFullResolutionRequiresVerifiedEntitlementWhileProofRemainsFree() throws {
    let artifact = try MediaArtifactIssuer(issuerID: "export-tests").issue(
      artifactReference: "artifact-c"
    )
    let freeAccess = EntitlementPolicy.access(for: .free)
    let entitlement = try verifiedEntitlement()
    let proAccess = EntitlementPolicy.access(for: .pro(entitlement))

    XCTAssertEqual(
      ExportAuthorizationPolicy.authorize(
        request: ExportRequest(artifactID: artifact, quality: .fullResolution),
        access: freeAccess,
        moireDecision: nil
      ),
      .refused(.advancedOutputRequiresEntitlement)
    )

    let fullAuthorization = ExportAuthorizationPolicy.authorize(
      request: ExportRequest(artifactID: artifact, quality: .fullResolution),
      access: proAccess,
      moireDecision: nil
    )
    guard case .allowed(let fullExport) = fullAuthorization else {
      return XCTFail("Verified entitlement should authorize full-resolution export.")
    }
    XCTAssertEqual(fullExport.basis, .verifiedEntitlement(entitlement))

    let proofAuthorization = ExportAuthorizationPolicy.authorize(
      request: ExportRequest(artifactID: artifact, quality: .proofPreview),
      access: freeAccess,
      moireDecision: nil
    )
    guard case .allowed(let proofExport) = proofAuthorization else {
      return XCTFail("Free proof export must remain available.")
    }
    XCTAssertEqual(proofExport.basis, .freeProof)
  }

  private func verifiedEntitlement() throws -> VerifiedProEntitlement {
    try ProviderEntitlementIssuer().verifyActiveEntitlement(
      providerEntitlementIdentifier: EntitlementID.proCapture.rawValue,
      verificationReference: "revenuecat-verification-1"
    )
  }
}
