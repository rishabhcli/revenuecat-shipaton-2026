import CameraDomain
import CaptureDomain
import XCTest

final class CameraAdmissionPropertyTests: XCTestCase {
  /// 32 recorded x 32 diagnostic x 32 slots x 5 pressure values.
  func testRecordedFramesConsumeCapacityBeforeDiagnostics_163_840DistinctCases() throws {
    var evaluatedCases = 0
    var starvedCases = 0

    for recorded in 0..<32 {
      for diagnostics in 0..<32 {
        for slots in 0..<32 {
          for pressure in CapturePressure.allCases {
            let load = try CaptureLoad(
              recordedFramesAwaiting: recorded,
              diagnosticJobsAwaiting: diagnostics,
              availableSlots: slots,
              pressure: pressure
            )
            let decision = CaptureAdmissionPolicy.decide(for: load)
            let admission = decision.admission
            let expectedRecorded = min(recorded, slots)
            let expectedDiagnostics =
              pressure == .nominal ? min(diagnostics, slots - expectedRecorded) : 0

            XCTAssertEqual(admission.recordedFramesAdmitted, expectedRecorded)
            XCTAssertEqual(admission.diagnosticJobsAdmitted, expectedDiagnostics)
            XCTAssertEqual(admission.recordedFramesDeferred, recorded - expectedRecorded)
            XCTAssertEqual(admission.diagnosticJobsDropped, diagnostics - expectedDiagnostics)
            XCTAssertLessThanOrEqual(
              admission.recordedFramesAdmitted + admission.diagnosticJobsAdmitted,
              slots
            )
            XCTAssertFalse(admission.starvesRecordedFrames)
            XCTAssertTrue(CaptureAdmissionPolicy.postconditionHolds(admission, for: load))
            if admission.starvesRecordedFrames { starvedCases += 1 }
            evaluatedCases += 1
          }
        }
      }
    }

    XCTAssertEqual(evaluatedCases, 163_840)
    XCTAssertEqual(starvedCases, 0)
  }

  /// Fault injection: the capture pipeline is under pressure, so diagnostic work
  /// takes no capacity at all even when capacity is abundant.
  func testNonNominalPressureStopsDiagnosticWorkEntirely_4DistinctPressures() throws {
    var evaluatedPressures = 0

    for pressure in CapturePressure.allCases where pressure != .nominal {
      let decision = CaptureAdmissionPolicy.decide(
        for: try CaptureLoad(
          recordedFramesAwaiting: 1,
          diagnosticJobsAwaiting: 500,
          availableSlots: 1_000,
          pressure: pressure
        )
      )

      XCTAssertEqual(decision.admission.recordedFramesAdmitted, 1)
      XCTAssertEqual(decision.admission.diagnosticJobsAdmitted, 0)
      XCTAssertEqual(decision.admission.diagnosticJobsDropped, 500)
      XCTAssertEqual(decision.admission.recordedFramesDeferred, 0)
      XCTAssertEqual(decision.admission.pressure, pressure)
      evaluatedPressures += 1
    }

    XCTAssertEqual(evaluatedPressures, 4)

    let nominal = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: 1,
        diagnosticJobsAwaiting: 500,
        availableSlots: 1_000,
        pressure: .nominal
      )
    )
    XCTAssertEqual(nominal.admission.diagnosticJobsAdmitted, 500)
  }

  /// Fault injection: capacity collapses to nothing while both queues are full.
  func testNoCapacityDefersEveryRecordedFrameAndRunsNoDiagnostics() throws {
    let decision = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: 64,
        diagnosticJobsAwaiting: 64,
        availableSlots: 0,
        pressure: .nominal
      )
    )

    XCTAssertEqual(decision.admission.recordedFramesAdmitted, 0)
    XCTAssertEqual(decision.admission.recordedFramesDeferred, 64)
    XCTAssertEqual(decision.admission.diagnosticJobsAdmitted, 0)
    XCTAssertEqual(decision.admission.diagnosticJobsDropped, 64)
    XCTAssertFalse(decision.admission.starvesRecordedFrames)
  }

  func testEveryDecisionRecordsScalarCountsAndNoViolation() throws {
    let decision = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: 3,
        diagnosticJobsAwaiting: 7,
        availableSlots: 5,
        pressure: .nominal
      )
    )

    XCTAssertEqual(decision.events.count, 1)
    guard case .captureAdmissionDecided(let event) = decision.events[0] else {
      return XCTFail("Every admission decision must record its counts.")
    }
    XCTAssertEqual(event.pressure, .nominal)
    XCTAssertEqual(event.recordedFramesAdmitted, 3)
    XCTAssertEqual(event.recordedFramesDeferred, 0)
    XCTAssertEqual(event.diagnosticJobsAdmitted, 2)
    XCTAssertEqual(event.diagnosticJobsDropped, 5)
    requireSendable(CaptureAdmissionEvent.self)
  }

  /// The guard must reject exactly the shapes invariant I3 forbids, judged
  /// against admissions the policy itself produced.
  func testThePostconditionGuardRejectsStarvationAndMiscounting() throws {
    let load = try CaptureLoad(
      recordedFramesAwaiting: 4,
      diagnosticJobsAwaiting: 4,
      availableSlots: 2,
      pressure: .nominal
    )
    let honest = CaptureAdmissionPolicy.decide(for: load).admission
    XCTAssertTrue(CaptureAdmissionPolicy.postconditionHolds(honest, for: load))

    let strictlySmallerLoad = try CaptureLoad(
      recordedFramesAwaiting: 4,
      diagnosticJobsAwaiting: 4,
      availableSlots: 8,
      pressure: .nominal
    )
    // The same admission judged against a different load must be rejected,
    // because the guard re-derives the counts instead of trusting them.
    XCTAssertFalse(CaptureAdmissionPolicy.postconditionHolds(honest, for: strictlySmallerLoad))

    let underPressure = try CaptureLoad(
      recordedFramesAwaiting: 4,
      diagnosticJobsAwaiting: 4,
      availableSlots: 8,
      pressure: .thermalThrottling
    )
    let generous = CaptureAdmissionPolicy.decide(for: strictlySmallerLoad).admission
    XCTAssertGreaterThan(generous.diagnosticJobsAdmitted, 0)
    XCTAssertFalse(CaptureAdmissionPolicy.postconditionHolds(generous, for: underPressure))
  }

  func testCaptureLoadRefusesNegativeCounts_3_072DistinctCases() {
    var evaluatedCases = 0

    for magnitude in 1...1_024 {
      let negative = -magnitude
      let inputs = [
        (negative, 0, 0),
        (0, negative, 0),
        (0, 0, negative),
      ]

      for input in inputs {
        assertThrowsEqual(
          CameraDomainError.negativeQueueCount,
          try CaptureLoad(
            recordedFramesAwaiting: input.0,
            diagnosticJobsAwaiting: input.1,
            availableSlots: input.2,
            pressure: .nominal
          )
        )
        evaluatedCases += 1
      }
    }

    XCTAssertEqual(evaluatedCases, 3_072)
  }

  /// A count above the supported depth is corrupted rather than merely large, so
  /// it is refused at the boundary instead of entering admission arithmetic.
  func testQueueDepthsAboveTheSupportedMaximumAreRefused_6DistinctCases() throws {
    let maximum = CaptureLoad.maximumQueueDepth
    let expectedError = CameraDomainError.queueDepthAboveSupportedMaximum(maximum: maximum)
    var evaluatedCases = 0

    for oversized in [maximum + 1, Int.max] {
      for position in 0..<3 {
        assertThrowsEqual(
          expectedError,
          try CaptureLoad(
            recordedFramesAwaiting: position == 0 ? oversized : 0,
            diagnosticJobsAwaiting: position == 1 ? oversized : 0,
            availableSlots: position == 2 ? oversized : 0,
            pressure: .nominal
          )
        )
        evaluatedCases += 1
      }
    }

    XCTAssertEqual(evaluatedCases, 6)
    XCTAssertEqual(expectedError.code, "camera.capture_load.queue_depth_too_large")

    // At the supported maximum the arithmetic still holds exactly.
    let saturated = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: maximum,
        diagnosticJobsAwaiting: maximum,
        availableSlots: maximum,
        pressure: .nominal
      )
    )
    XCTAssertEqual(saturated.admission.recordedFramesAdmitted, maximum)
    XCTAssertEqual(saturated.admission.diagnosticJobsAdmitted, 0)
    XCTAssertEqual(saturated.admission.recordedFramesDeferred, 0)
    XCTAssertEqual(saturated.admission.diagnosticJobsDropped, maximum)
  }

  func testLiveFrameWindowRefusesEveryProvenanceAndOrderingViolation() throws {
    let sourceA = try CaptureSourceID("rear-wide")
    let sourceB = try CaptureSourceID("front-wide")

    var sessionA = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "session-a",
      sourceID: sourceA,
      initialSequenceNumber: 0
    )
    var sessionB = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "session-b",
      sourceID: sourceA,
      initialSequenceNumber: 1
    )
    let frameA = try sessionA.issueFrame(monotonicTimestampNanoseconds: 100)
    let frameB = try sessionB.issueFrame(monotonicTimestampNanoseconds: 101)
    assertThrowsEqual(
      CameraDomainError.mixedCaptureSessions,
      try LiveFrameWindow(frames: [frameA, frameB])
    )

    var otherSource = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "session-a",
      sourceID: sourceB,
      initialSequenceNumber: 1
    )
    let otherSourceFrame = try otherSource.issueFrame(monotonicTimestampNanoseconds: 101)
    assertThrowsEqual(
      CameraDomainError.mixedCaptureSources,
      try LiveFrameWindow(frames: [frameA, otherSourceFrame])
    )

    var sequenceIssuerA = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "sequence-session",
      sourceID: sourceA,
      initialSequenceNumber: 10
    )
    var sequenceIssuerB = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "sequence-session",
      sourceID: sourceA,
      initialSequenceNumber: 10
    )
    let sequenceA = try sequenceIssuerA.issueFrame(monotonicTimestampNanoseconds: 200)
    let sequenceB = try sequenceIssuerB.issueFrame(monotonicTimestampNanoseconds: 201)
    assertThrowsEqual(
      CameraDomainError.nonIncreasingSequence,
      try LiveFrameWindow(frames: [sequenceA, sequenceB])
    )

    var timestampIssuerA = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "timestamp-session",
      sourceID: sourceA,
      initialSequenceNumber: 20
    )
    var timestampIssuerB = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "timestamp-session",
      sourceID: sourceA,
      initialSequenceNumber: 21
    )
    let timestampA = try timestampIssuerA.issueFrame(monotonicTimestampNanoseconds: 300)
    let timestampB = try timestampIssuerB.issueFrame(monotonicTimestampNanoseconds: 300)
    assertThrowsEqual(
      CameraDomainError.nonIncreasingTimestamp,
      try LiveFrameWindow(frames: [timestampA, timestampB])
    )
  }

  func testFrameIssuerRefusesTimestampReplayAndSequenceOverflow() throws {
    let source = try CaptureSourceID("rear-wide")
    var issuer = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "timestamp-replay",
      sourceID: source
    )
    _ = try issuer.issueFrame(monotonicTimestampNanoseconds: 10)
    assertThrowsEqual(
      CameraDomainError.nonIncreasingIssuedTimestamp,
      try issuer.issueFrame(monotonicTimestampNanoseconds: 10)
    )

    var exhaustingIssuer = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "sequence-exhaustion",
      sourceID: source,
      initialSequenceNumber: UInt64.max
    )
    let finalFrame = try exhaustingIssuer.issueFrame(monotonicTimestampNanoseconds: 1)
    XCTAssertEqual(finalFrame.sequenceNumber, UInt64.max)
    assertThrowsEqual(
      CameraDomainError.sequenceNumberExhausted,
      try exhaustingIssuer.issueFrame(monotonicTimestampNanoseconds: 2)
    )
  }

  func testAdapterIdentitySeparatesReusedSessionReferences_1_024DistinctIssuers() throws {
    let source = try CaptureSourceID("rear-wide")
    var sessionIDs: Set<CaptureSessionID> = []

    for index in 0..<1_024 {
      let issuer = try LiveCaptureIssuer(
        adapterID: "camera-adapter-\(index)",
        sessionReference: "reused-session-reference",
        sourceID: source
      )
      XCTAssertTrue(sessionIDs.insert(issuer.sessionID).inserted)
    }

    XCTAssertEqual(sessionIDs.count, 1_024)
  }

  func testSessionIdentityComponentsCannotCollideThroughDelimiterAmbiguity() throws {
    let source = try CaptureSourceID("rear-wide")
    let first = try LiveCaptureIssuer(
      adapterID: "a.b",
      sessionReference: "c",
      sourceID: source
    )
    let second = try LiveCaptureIssuer(
      adapterID: "a",
      sessionReference: "b.c",
      sourceID: source
    )

    XCTAssertNotEqual(first.sessionID, second.sessionID)
    XCTAssertNotEqual(first.sessionID.description, second.sessionID.description)
  }

  func testFrameWindowRefusesEmptyAndOversizedCollectionsExactly() throws {
    assertThrowsEqual(
      CameraDomainError.emptyFrameWindow,
      try LiveFrameWindow(frames: [])
    )

    var issuer = try LiveCaptureIssuer(
      adapterID: "camera-adapter",
      sessionReference: "oversized-window",
      sourceID: CaptureSourceID("rear-wide")
    )
    var frames: [LiveFrameReference] = []
    for timestamp in 1...LiveFrameWindow.maximumFrameCount + 1 {
      frames.append(
        try issuer.issueFrame(monotonicTimestampNanoseconds: UInt64(timestamp))
      )
    }
    assertThrowsEqual(
      CameraDomainError.frameWindowTooLarge(maximum: LiveFrameWindow.maximumFrameCount),
      try LiveFrameWindow(frames: frames)
    )
  }
}
