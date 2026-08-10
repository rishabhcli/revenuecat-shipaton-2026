import AnalysisDomain
import CameraDomain
import CaptureDomain
import PurchasesDomain
import UIDomain
import XCTest

final class CorrectionConfidencePropertyTests: XCTestCase {
  func testUnsupportedConditionsNeverBecomePositive_5DistinctReasons() throws {
    var factory = try TestLiveEvidenceFactory()
    let before = try factory.issueEvidence(frameCount: 4, normalizedEnergy: 1)
    let after = try factory.issueEvidence(frameCount: 4, normalizedEnergy: 0.01)
    let thresholds = try defaultCorrectionThresholds()
    var evaluatedReasons = 0

    for reason in UnsupportedSourceReason.allCases {
      let confidence = CorrectionAssessment.evaluate(
        before: before,
        after: after,
        sourceCondition: .unsupported(reason),
        candidateMargin: try UnitInterval(1),
        thresholds: thresholds
      )
      let indicator = CorrectionIndicator(confidence: confidence)

      XCTAssertEqual(confidence, .unavailable(.unsupported(reason)))
      XCTAssertEqual(indicator.tone, .refusal)
      XCTAssertEqual(indicator.shape, .xOctagon)
      XCTAssertFalse(indicator.accessibilityLabel.isEmpty)
      evaluatedReasons += 1
    }

    XCTAssertEqual(evaluatedReasons, UnsupportedSourceReason.allCases.count)
    XCTAssertEqual(evaluatedReasons, 5)
  }

  func testUnstableConditionsNeverBecomeVerified_1_024DistinctMeasurementPairs() throws {
    var factory = try TestLiveEvidenceFactory(session: "unstable-property-session")
    let before = try factory.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    let thresholds = try defaultCorrectionThresholds()
    var evaluatedPairs = 0

    for numerator in 1...1_024 {
      let afterEnergy = Double(numerator) / 2_048
      let candidateMargin = Double(numerator) / 1_024
      let after = try factory.issueEvidence(
        frameCount: 3,
        normalizedEnergy: afterEnergy
      )
      let confidence = CorrectionAssessment.evaluate(
        before: before,
        after: after,
        sourceCondition: .unstable,
        candidateMargin: try UnitInterval(candidateMargin),
        thresholds: thresholds
      )

      guard case .unstable(let unstable) = confidence else {
        XCTFail("A qualifying unstable case did not produce unstable confidence.")
        continue
      }
      XCTAssertGreaterThanOrEqual(
        unstable.measuredReduction.value,
        thresholds.minimumReduction.value
      )
      XCTAssertEqual(CorrectionIndicator(confidence: confidence).tone, .caution)
      evaluatedPairs += 1
    }

    XCTAssertEqual(evaluatedPairs, 1_024)
  }

  func testStableMeasuredImprovementIssuesVerifiedCorrectionAndFreeProof() throws {
    var factory = try TestLiveEvidenceFactory(session: "verified-session")
    let before = try factory.issueEvidence(frameCount: 5, normalizedEnergy: 0.8)
    let after = try factory.issueEvidence(frameCount: 5, normalizedEnergy: 0.2)
    let confidence = CorrectionAssessment.evaluate(
      before: before,
      after: after,
      sourceCondition: .stable,
      candidateMargin: try UnitInterval(0.5),
      thresholds: try defaultCorrectionThresholds()
    )

    guard case .verified(let verified) = confidence else {
      return XCTFail("Expected verified correction")
    }
    XCTAssertEqual(verified.captureSessionID, after.frameWindow.sessionID)
    XCTAssertEqual(verified.measuredReduction.value, 0.75, accuracy: 0.000_001)
    XCTAssertEqual(verified.sampledFrameCount, 10)
    XCTAssertEqual(CorrectionIndicator(confidence: confidence).tone, .positive)

    let proof = try FreeProofIssuer.issue(from: confidence)
    let freeAccess = EntitlementPolicy.access(for: .free)
    XCTAssertEqual(
      PaywallPresentationPolicy.decide(proof: nil, access: freeAccess),
      .hiddenUntilFreeProof
    )
    XCTAssertEqual(
      PaywallPresentationPolicy.decide(proof: proof, access: freeAccess),
      .mayPresentAfterVerifiedProof
    )
  }

  func testSessionSourceAlgorithmAndChronologyMismatchesRefuseExactly() throws {
    let thresholds = try defaultCorrectionThresholds()
    let margin = try UnitInterval(1)

    var sessionA = try TestLiveEvidenceFactory(
      session: "session-a",
      source: "rear-wide",
      initialTimestampNanoseconds: 1
    )
    let sessionABefore = try sessionA.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    var sessionB = try TestLiveEvidenceFactory(
      session: "session-b",
      source: "rear-wide",
      initialSequenceNumber: 10,
      initialTimestampNanoseconds: 10_000_000
    )
    let sessionBAfter = try sessionB.issueEvidence(frameCount: 3, normalizedEnergy: 0.1)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: sessionABefore,
        after: sessionBAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.mismatchedCaptureSession)
    )

    var sourceA = try TestLiveEvidenceFactory(
      session: "shared-session",
      source: "rear-wide"
    )
    let sourceABefore = try sourceA.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    var sourceB = try TestLiveEvidenceFactory(
      session: "shared-session",
      source: "front-wide",
      initialSequenceNumber: 10,
      initialTimestampNanoseconds: 10_000_000
    )
    let sourceBAfter = try sourceB.issueEvidence(frameCount: 3, normalizedEnergy: 0.1)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: sourceABefore,
        after: sourceBAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.mismatchedCaptureSource)
    )

    var versionFactory = try TestLiveEvidenceFactory(session: "version-session")
    let versionBefore = try versionFactory.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    let versionAfter = try versionFactory.issueEvidence(
      frameCount: 3,
      normalizedEnergy: 0.1,
      algorithm: "row-banding-v2"
    )
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: versionBefore,
        after: versionAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.algorithmVersionMismatch)
    )

    var chronologyFactory = try TestLiveEvidenceFactory(session: "chronology-session")
    let earlier = try chronologyFactory.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    let later = try chronologyFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0.1)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: later,
        after: earlier,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.nonChronologicalEvidence)
    )
  }

  func testEveryNumericAndEvidenceRefusalIsExact() throws {
    assertThrowsEqual(
      AnalysisDomainError.nonFiniteBandingEnergy,
      try BandingEnergy(normalizedValue: .nan)
    )
    for invalid in [-Double.leastNonzeroMagnitude, 1 + Double.ulpOfOne] {
      assertThrowsEqual(
        AnalysisDomainError.bandingEnergyOutsideUnitInterval,
        try BandingEnergy(normalizedValue: invalid)
      )
    }

    var issuerFactory = try TestLiveEvidenceFactory(session: "issuer-refusals")
    let twoFrames = try issuerFactory.issueFrameWindow(frameCount: 2)
    let evidenceIssuer = BandingEvidenceIssuer(
      algorithmVersion: try AlgorithmVersion("row-banding-v1")
    )
    assertThrowsEqual(
      AnalysisDomainError.insufficientLiveEvidence(requiredFrameCount: 1),
      try evidenceIssuer.issue(frameWindow: twoFrames, energies: [])
    )
    assertThrowsEqual(
      AnalysisDomainError.observationCountMismatch,
      try evidenceIssuer.issue(
        frameWindow: twoFrames,
        energies: [try BandingEnergy(normalizedValue: 0.5)]
      )
    )

    assertThrowsEqual(
      AnalysisDomainError.nonPositiveConfidenceThreshold,
      try CorrectionThresholds(
        minimumReduction: UnitInterval(0),
        minimumCandidateMargin: UnitInterval(0.1),
        minimumFrameCountPerWindow: 3
      )
    )
    assertThrowsEqual(
      AnalysisDomainError.nonPositiveConfidenceThreshold,
      try CorrectionThresholds(
        minimumReduction: UnitInterval(0.1),
        minimumCandidateMargin: UnitInterval(0),
        minimumFrameCountPerWindow: 3
      )
    )
    for invalidFrameCount in [1, LiveFrameWindow.maximumFrameCount + 1] {
      assertThrowsEqual(
        AnalysisDomainError.invalidMinimumFrameCount,
        try CorrectionThresholds(
          minimumReduction: UnitInterval(0.1),
          minimumCandidateMargin: UnitInterval(0.1),
          minimumFrameCountPerWindow: invalidFrameCount
        )
      )
    }
  }

  func testLiveEvidenceRequiresOneMeasurementPerIssuedFrame_479DistinctCounts() throws {
    var factory = try TestLiveEvidenceFactory(session: "measurement-count-property")
    let window = try factory.issueFrameWindow(
      frameCount: LiveFrameWindow.maximumFrameCount
    )
    let issuer = BandingEvidenceIssuer(
      algorithmVersion: try AlgorithmVersion("row-banding-v1")
    )
    let energy = try BandingEnergy(normalizedValue: 0.5)
    var evaluatedCounts = 0

    for measurementCount in 1...480
    where measurementCount != LiveFrameWindow.maximumFrameCount {
      assertThrowsEqual(
        AnalysisDomainError.observationCountMismatch,
        try issuer.issue(
          frameWindow: window,
          energies: Array(repeating: energy, count: measurementCount)
        )
      )
      evaluatedCounts += 1
    }

    XCTAssertEqual(evaluatedCounts, 479)
    XCTAssertEqual(
      try issuer.issue(
        frameWindow: window,
        energies: Array(
          repeating: energy,
          count: LiveFrameWindow.maximumFrameCount
        )
      ).observations.count,
      LiveFrameWindow.maximumFrameCount
    )
  }

  func testAssessmentRefusesInsufficientZeroBaselineLowImprovementAndAmbiguity() throws {
    let thresholds = try defaultCorrectionThresholds()
    let margin = try UnitInterval(1)

    var insufficientFactory = try TestLiveEvidenceFactory(session: "insufficient-session")
    let insufficientBefore = try insufficientFactory.issueEvidence(
      frameCount: 2,
      normalizedEnergy: 1
    )
    let sufficientAfter = try insufficientFactory.issueEvidence(
      frameCount: 3,
      normalizedEnergy: 0.1
    )
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: insufficientBefore,
        after: sufficientAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.insufficientLiveEvidence(requiredFrameCount: 3))
    )

    var zeroFactory = try TestLiveEvidenceFactory(session: "zero-session")
    let zeroBefore = try zeroFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0)
    let zeroAfter = try zeroFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: zeroBefore,
        after: zeroAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.zeroBaselineEnergy)
    )

    var lowFactory = try TestLiveEvidenceFactory(session: "low-improvement-session")
    let lowBefore = try lowFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0.5)
    let lowAfter = try lowFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0.45)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: lowBefore,
        after: lowAfter,
        sourceCondition: .stable,
        candidateMargin: margin,
        thresholds: thresholds
      ),
      .unavailable(.insufficientImprovement)
    )

    var ambiguousFactory = try TestLiveEvidenceFactory(session: "ambiguous-session")
    let ambiguousBefore = try ambiguousFactory.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    let ambiguousAfter = try ambiguousFactory.issueEvidence(frameCount: 3, normalizedEnergy: 0.5)
    XCTAssertEqual(
      CorrectionAssessment.evaluate(
        before: ambiguousBefore,
        after: ambiguousAfter,
        sourceCondition: .stable,
        candidateMargin: try UnitInterval(0.05),
        thresholds: thresholds
      ),
      .unavailable(.ambiguousCandidate)
    )
  }

  func testFreeProofIssuerRefusesNonVerifiedConfidence_6DistinctCases() throws {
    var evaluatedCases = 0
    for reason in UnsupportedSourceReason.allCases {
      assertThrowsEqual(
        UIDomainError.correctionNotVerified,
        try FreeProofIssuer.issue(from: .unavailable(.unsupported(reason)))
      )
      evaluatedCases += 1
    }

    var factory = try TestLiveEvidenceFactory(session: "unstable-proof-session")
    let before = try factory.issueEvidence(frameCount: 3, normalizedEnergy: 1)
    let after = try factory.issueEvidence(frameCount: 3, normalizedEnergy: 0.1)
    let unstable = CorrectionAssessment.evaluate(
      before: before,
      after: after,
      sourceCondition: .unstable,
      candidateMargin: try UnitInterval(1),
      thresholds: try defaultCorrectionThresholds()
    )
    assertThrowsEqual(
      UIDomainError.correctionNotVerified,
      try FreeProofIssuer.issue(from: unstable)
    )
    evaluatedCases += 1

    XCTAssertEqual(evaluatedCases, 6)
  }

  func testUnlockedUsersNeverSeePaywallEvenWithoutProof() throws {
    let entitlement = try ProviderEntitlementIssuer().verifyActiveEntitlement(
      providerEntitlementIdentifier: EntitlementID.proCapture.rawValue,
      verificationReference: "provider-check-1"
    )
    let access = EntitlementPolicy.access(for: .pro(entitlement))

    XCTAssertEqual(
      PaywallPresentationPolicy.decide(proof: nil, access: access),
      .hiddenBecauseAlreadyUnlocked
    )
  }
}
