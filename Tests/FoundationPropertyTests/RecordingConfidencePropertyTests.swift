import AnalysisDomain
import CameraDomain
import CaptureDomain
import UIDomain
import XCTest

/// Invariant I2: unsupported or unstable conditions stay visible and recording
/// confidence never turns green.
///
/// These tests attack the gate from four directions at once — what the
/// assessment said, what the source is doing now, whether the analysis
/// component is still working, and how old the assessment is — because the
/// dangerous case is the one where only one of the four has gone wrong.
final class RecordingConfidencePropertyTests: XCTestCase {
  private struct Fixture {
    var factory: TestLiveEvidenceFactory
    let verified: CorrectionConfidence
    let unstable: CorrectionConfidence
    let assessedThrough: LiveFrameReference
    let policy: RecordingFreshnessPolicy
  }

  private func makeFixture(session: String) throws -> Fixture {
    var factory = try TestLiveEvidenceFactory(session: session)
    let before = try factory.issueEvidence(frameCount: 4, normalizedEnergy: 0.8)
    let after = try factory.issueEvidence(frameCount: 4, normalizedEnergy: 0.1)
    let thresholds = try defaultCorrectionThresholds()
    let verified = CorrectionAssessment.evaluate(
      before: before,
      after: after,
      sourceCondition: .stable,
      candidateMargin: try UnitInterval(0.9),
      thresholds: thresholds
    )
    let unstable = CorrectionAssessment.evaluate(
      before: before,
      after: after,
      sourceCondition: .unstable,
      candidateMargin: try UnitInterval(0.9),
      thresholds: thresholds
    )
    guard case .verified = verified, case .unstable = unstable else {
      throw XCTSkip("The fixture must produce both a verified and an unstable assessment.")
    }
    return Fixture(
      factory: factory,
      verified: verified,
      unstable: unstable,
      assessedThrough: try XCTUnwrap(after.frameWindow.frames.last),
      policy: try defaultFreshnessPolicy()
    )
  }

  private static let everyAssessmentRefusal: [CorrectionRefusal] =
    UnsupportedSourceReason.allCases.map { .unsupported($0) } + [
      .insufficientLiveEvidence(requiredFrameCount: 3),
      .mismatchedCaptureSession,
      .mismatchedCaptureSource,
      .algorithmVersionMismatch,
      .nonChronologicalEvidence,
      .zeroBaselineEnergy,
      .insufficientImprovement,
      .ambiguousCandidate,
    ]

  private static let everyAvailability: [AnalysisAvailability] =
    [.measuring]
    + AnalysisDegradation.allCases.map { .degraded($0) }
    + AnalysisStall.allCases.map { .stalled($0) }

  private static let everySourceCondition: [SourceCondition] =
    [.stable, .unstable] + UnsupportedSourceReason.allCases.map { .unsupported($0) }

  /// 15 assessments x 7 source conditions x 8 availability states x 3 ages.
  ///
  /// The three observation frames are issued once at exact ages relative to the
  /// assessed frame and then reused, so every cell varies only in the dimension
  /// it is meant to vary in.
  func testGreenRequiresVerifiedStableMeasuringAndFreshEvidence_2520DistinctCases() throws {
    var fixture = try makeFixture(session: "i2-matrix-session")
    let policy = fixture.policy
    let assessedAt = fixture.assessedThrough.monotonicTimestampNanoseconds
    let budget = policy.maximumAssessmentAgeNanoseconds
    let observations: [(age: UInt64, frame: LiveFrameReference)] = [
      (budget / 2, try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget / 2)),
      (budget, try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget)),
      (budget + 1, try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget + 1)),
    ]

    var assessments: [CorrectionConfidence] = [fixture.verified, fixture.unstable]
    assessments += Self.everyAssessmentRefusal.map { .unavailable($0) }
    XCTAssertEqual(assessments.count, 15)
    XCTAssertEqual(Self.everySourceCondition.count, 7)
    XCTAssertEqual(Self.everyAvailability.count, 8)

    var evaluatedCases = 0
    var greenCases = 0
    for assessment in assessments {
      for sourceCondition in Self.everySourceCondition {
        for availability in Self.everyAvailability {
          for observation in observations {
            let decision = RecordingConfidenceGate.evaluate(
              RecordingConfidenceInputs(
                assessment: assessment,
                assessedThrough: fixture.assessedThrough,
                latestObservedFrame: observation.frame,
                sourceCondition: sourceCondition,
                availability: availability
              ),
              policy: policy
            )
            evaluatedCases += 1

            let expectedGreen =
              isVerified(assessment) && isStable(sourceCondition)
              && isMeasuring(availability) && observation.age <= budget

            XCTAssertEqual(
              decision.confidence.isGreen,
              expectedGreen,
              """
              Green mismatch for assessment=\(assessment) source=\(sourceCondition) \
              availability=\(availability) age=\(observation.age)
              """
            )
            XCTAssertEqual(
              CorrectionIndicator(recording: decision.confidence).tone == .positive,
              expectedGreen
            )
            XCTAssertFalse(
              decision.events.contains { event in
                if case .invariantViolated = event { return true }
                return false
              },
              "A correct decision must not report an invariant violation."
            )
            if expectedGreen { greenCases += 1 }

            // Every observation here is newer than the assessed frame, so an
            // ordering refusal anywhere in this matrix would be a defect.
            if case .refused(.observationPrecedesAssessment) = decision.confidence {
              XCTFail("Chronological inputs must not produce an ordering refusal.")
            }
          }
        }
      }
    }

    XCTAssertEqual(evaluatedCases, 2_520)
    // One of fifteen assessments, one of seven conditions, one of eight
    // availability states, and two of three ages can be simultaneously green.
    XCTAssertEqual(greenCases, 2)
  }

  /// Fault injection: the assessment stays verified and the source stays stable,
  /// but the analysis component fails underneath it.
  func testAComponentFailureWithdrawsGreenWithoutChangingTheAssessment_7DistinctFailures()
    throws
  {
    var fixture = try makeFixture(session: "i2-component-failure-session")
    var withdrawnCases = 0

    for failure in Self.everyAvailability where !isMeasuring(failure) {
      let latest = try fixture.factory.issueFrame(advanceNanoseconds: 1_000_000)
      let decision = RecordingConfidenceGate.evaluate(
        RecordingConfidenceInputs(
          assessment: fixture.verified,
          assessedThrough: fixture.assessedThrough,
          latestObservedFrame: latest,
          sourceCondition: .stable,
          availability: failure
        ),
        policy: fixture.policy
      )

      XCTAssertFalse(decision.confidence.isGreen)
      let indicator = CorrectionIndicator(recording: decision.confidence)
      XCTAssertNotEqual(indicator.tone, .positive)
      XCTAssertNotEqual(indicator.shape, .checkmarkCircle)
      XCTAssertFalse(indicator.visibleText.isEmpty)
      XCTAssertFalse(indicator.accessibilityLabel.isEmpty)

      switch failure {
      case .stalled(let stall):
        XCTAssertEqual(decision.confidence, .refused(.analysisStalled(stall)))
        XCTAssertEqual(indicator.tone, .refusal)
      case .degraded(let degradation):
        XCTAssertEqual(
          decision.confidence,
          .recordWithoutCorrectionClaim(.analysisDegraded(degradation))
        )
        XCTAssertEqual(indicator.tone, .caution)
      case .measuring:
        XCTFail("A healthy component is not a failure case.")
      }
      withdrawnCases += 1
    }

    XCTAssertEqual(withdrawnCases, 7)
  }

  /// Fault injection: measurement simply stops, so the last assessment ages out
  /// while the assessment, the source, and the component all still look correct.
  func testAnAgeingAssessmentLosesGreenAtTheDeclaredBoundary_4DistinctAges() throws {
    var fixture = try makeFixture(session: "i2-staleness-session")
    let budget = fixture.policy.maximumAssessmentAgeNanoseconds
    let assessedAt = fixture.assessedThrough.monotonicTimestampNanoseconds
    var evaluatedAges = 0

    for age in [UInt64(1), budget - 1, budget, budget + 1] {
      let decision = RecordingConfidenceGate.evaluate(
        RecordingConfidenceInputs(
          assessment: fixture.verified,
          assessedThrough: fixture.assessedThrough,
          latestObservedFrame: try fixture.factory.issueFrame(atNanoseconds: assessedAt + age),
          sourceCondition: .stable,
          availability: .measuring
        ),
        policy: fixture.policy
      )

      XCTAssertEqual(decision.confidence.isGreen, age <= budget, "age=\(age)")
      if age > budget {
        XCTAssertEqual(
          decision.confidence,
          .refused(.assessmentStale(ageMilliseconds: Int(age / 1_000_000)))
        )
        XCTAssertEqual(
          CorrectionIndicator(recording: decision.confidence).tone,
          .refusal
        )
      }
      evaluatedAges += 1
    }

    XCTAssertEqual(evaluatedAges, 4)
  }

  func testEvidenceFromAnotherSessionOrSourceIsRefused() throws {
    let fixture = try makeFixture(session: "i2-identity-session")
    var otherSession = try TestLiveEvidenceFactory(session: "i2-other-session")
    _ = try otherSession.issueEvidence(frameCount: 3, normalizedEnergy: 0.5)
    var otherSource = try TestLiveEvidenceFactory(
      session: "i2-identity-session",
      source: "rear-ultra-wide"
    )
    _ = try otherSource.issueEvidence(frameCount: 3, normalizedEnergy: 0.5)

    for (frame, expected) in [
      (
        try otherSession.issueFrame(advanceNanoseconds: 1_000_000),
        RecordingConfidence.refused(.evidenceFromAnotherSession)
      ),
      (
        try otherSource.issueFrame(advanceNanoseconds: 1_000_000),
        RecordingConfidence.refused(.evidenceFromAnotherSource)
      ),
    ] {
      let decision = RecordingConfidenceGate.evaluate(
        RecordingConfidenceInputs(
          assessment: fixture.verified,
          assessedThrough: fixture.assessedThrough,
          latestObservedFrame: frame,
          sourceCondition: .stable,
          availability: .measuring
        ),
        policy: fixture.policy
      )
      XCTAssertEqual(decision.confidence, expected)
      XCTAssertEqual(CorrectionIndicator(recording: decision.confidence).tone, .refusal)
    }
  }

  /// Clock skew: the frame presented as "now" predates the assessed frame.
  func testAnObservationOlderThanTheAssessmentIsRefused() throws {
    let fixture = try makeFixture(session: "i2-skew-session")
    let earlier = fixture.assessedThrough
    var replay = try TestLiveEvidenceFactory(
      session: "i2-skew-session",
      initialTimestampNanoseconds: 1
    )
    _ = try replay.issueEvidence(frameCount: 2, normalizedEnergy: 0.5)
    let stale = try replay.issueFrame(advanceNanoseconds: 1)
    XCTAssertLessThan(
      stale.monotonicTimestampNanoseconds,
      earlier.monotonicTimestampNanoseconds
    )

    let decision = RecordingConfidenceGate.evaluate(
      RecordingConfidenceInputs(
        assessment: fixture.verified,
        assessedThrough: earlier,
        latestObservedFrame: stale,
        sourceCondition: .stable,
        availability: .measuring
      ),
      policy: fixture.policy
    )
    XCTAssertEqual(decision.confidence, .refused(.observationPrecedesAssessment))
  }

  /// The postcondition is an independent guard, so it must agree with the
  /// decision path on every cell rather than trusting it.
  func testThePostconditionGuardAgreesOnEveryCell_2520DistinctCases() throws {
    var fixture = try makeFixture(session: "i2-guard-session")
    let policy = fixture.policy
    let assessedAt = fixture.assessedThrough.monotonicTimestampNanoseconds
    let budget = policy.maximumAssessmentAgeNanoseconds
    let observations = [
      try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget / 2),
      try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget),
      try fixture.factory.issueFrame(atNanoseconds: assessedAt + budget + 1),
    ]
    var assessments: [CorrectionConfidence] = [fixture.verified, fixture.unstable]
    assessments += Self.everyAssessmentRefusal.map { .unavailable($0) }

    var evaluatedCases = 0
    for assessment in assessments {
      for sourceCondition in Self.everySourceCondition {
        for availability in Self.everyAvailability {
          for observation in observations {
            let inputs = RecordingConfidenceInputs(
              assessment: assessment,
              assessedThrough: fixture.assessedThrough,
              latestObservedFrame: observation,
              sourceCondition: sourceCondition,
              availability: availability
            )
            XCTAssertEqual(
              RecordingConfidenceGate.postconditionHolds(inputs, policy: policy),
              RecordingConfidenceGate.evaluate(inputs, policy: policy).confidence.isGreen
            )
            evaluatedCases += 1
          }
        }
      }
    }

    XCTAssertEqual(evaluatedCases, 2_520)
  }

  func testEveryDecisionEmitsExactlyOneScalarRecordingEvent() throws {
    var fixture = try makeFixture(session: "i2-telemetry-session")
    let latest = try fixture.factory.issueFrame(
      atNanoseconds: fixture.assessedThrough.monotonicTimestampNanoseconds + 3_000_000
    )
    let decision = RecordingConfidenceGate.evaluate(
      RecordingConfidenceInputs(
        assessment: fixture.verified,
        assessedThrough: fixture.assessedThrough,
        latestObservedFrame: latest,
        sourceCondition: .stable,
        availability: .measuring
      ),
      policy: fixture.policy
    )

    XCTAssertEqual(decision.events.count, 1)
    guard case .recordingConfidenceEvaluated(let event) = decision.events[0] else {
      return XCTFail("Every decision must record its outcome.")
    }
    XCTAssertEqual(event.outcome, .readyToRecord)
    XCTAssertEqual(event.reason, .none)
    XCTAssertEqual(event.assessmentAgeMilliseconds, 3)
    requireSendable(RecordingConfidenceEvent.self)
    requireSendable(OperationalEvent.self)
  }

  func testStaleAndStalledDecisionsRecordTheirClosedReason() throws {
    var fixture = try makeFixture(session: "i2-reason-session")
    let stalledDecision = RecordingConfidenceGate.evaluate(
      RecordingConfidenceInputs(
        assessment: fixture.verified,
        assessedThrough: fixture.assessedThrough,
        latestObservedFrame: try fixture.factory.issueFrame(advanceNanoseconds: 1_000_000),
        sourceCondition: .stable,
        availability: .stalled(.frameDeliveryStopped)
      ),
      policy: fixture.policy
    )
    guard case .recordingConfidenceEvaluated(let stalled) = stalledDecision.events[0] else {
      return XCTFail("A stalled decision must record its outcome.")
    }
    XCTAssertEqual(stalled.outcome, .refused)
    XCTAssertEqual(stalled.reason, .analysisStalled)

    let staleDecision = RecordingConfidenceGate.evaluate(
      RecordingConfidenceInputs(
        assessment: fixture.verified,
        assessedThrough: fixture.assessedThrough,
        latestObservedFrame: try fixture.factory.issueFrame(
          advanceNanoseconds: fixture.policy.maximumAssessmentAgeNanoseconds + 1
        ),
        sourceCondition: .stable,
        availability: .measuring
      ),
      policy: fixture.policy
    )
    guard case .recordingConfidenceEvaluated(let stale) = staleDecision.events[0] else {
      return XCTFail("A stale decision must record its outcome.")
    }
    XCTAssertEqual(stale.outcome, .refused)
    XCTAssertEqual(stale.reason, .assessmentStale)
    XCTAssertGreaterThan(stale.assessmentAgeMilliseconds, 0)
  }

  func testFreshnessBudgetRefusesValuesOutsideTheDeclaredRange_4DistinctBounds() throws {
    let smallest = RecordingFreshnessPolicy.smallestPermittedAgeNanoseconds
    let largest = RecordingFreshnessPolicy.largestPermittedAgeNanoseconds
    let expectedError = AnalysisDomainError.freshnessBudgetOutsideSupportedRange(
      smallestNanoseconds: smallest,
      largestNanoseconds: largest
    )

    XCTAssertEqual(
      try RecordingFreshnessPolicy(maximumAssessmentAgeNanoseconds: smallest)
        .maximumAssessmentAgeNanoseconds,
      smallest
    )
    XCTAssertEqual(
      try RecordingFreshnessPolicy(maximumAssessmentAgeNanoseconds: largest)
        .maximumAssessmentAgeNanoseconds,
      largest
    )
    assertThrowsEqual(
      expectedError,
      try RecordingFreshnessPolicy(maximumAssessmentAgeNanoseconds: smallest - 1)
    )
    assertThrowsEqual(
      expectedError,
      try RecordingFreshnessPolicy(maximumAssessmentAgeNanoseconds: largest + 1)
    )
    XCTAssertEqual(expectedError.code, "analysis.freshness.outside_supported_range")
  }

  func testEveryInvariantIsIdentifiedForAlerting_8DistinctInvariants() {
    XCTAssertEqual(DomainInvariant.allCases.count, 8)
    XCTAssertEqual(
      DomainInvariant.allCases.map(\.rawValue),
      ["I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8"]
    )
    XCTAssertEqual(
      DomainInvariant.recordingConfidenceNeverFalselyGreen.rawValue,
      "I2"
    )
    XCTAssertEqual(InvariantGuard.allCases, [.recordingConfidencePostcondition])
  }

  private func isMeasuring(_ availability: AnalysisAvailability) -> Bool {
    if case .measuring = availability { return true }
    return false
  }

  private func isVerified(_ assessment: CorrectionConfidence) -> Bool {
    if case .verified = assessment { return true }
    return false
  }

  private func isStable(_ condition: SourceCondition) -> Bool {
    if case .stable = condition { return true }
    return false
  }
}
