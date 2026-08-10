import CameraDomain
import XCTest

final class CameraAdmissionPropertyTests: XCTestCase {
  func testRecordedFramesConsumeCapacityBeforeDiagnostics_32_768DistinctCases() throws {
    var evaluatedCases = 0

    for recorded in 0..<32 {
      for diagnostics in 0..<32 {
        for slots in 0..<32 {
          let load = try CaptureLoad(
            recordedFramesAwaiting: recorded,
            diagnosticJobsAwaiting: diagnostics,
            availableSlots: slots
          )
          let decision = CaptureAdmissionPolicy.decide(for: load)
          let expectedRecorded = min(recorded, slots)
          let expectedDiagnostics = min(diagnostics, slots - expectedRecorded)

          XCTAssertEqual(decision.recordedFramesAdmitted, expectedRecorded)
          XCTAssertEqual(decision.diagnosticJobsAdmitted, expectedDiagnostics)
          XCTAssertEqual(decision.recordedFramesDeferred, recorded - expectedRecorded)
          XCTAssertEqual(decision.diagnosticJobsDropped, diagnostics - expectedDiagnostics)
          XCTAssertLessThanOrEqual(
            decision.recordedFramesAdmitted + decision.diagnosticJobsAdmitted,
            slots
          )
          if decision.recordedFramesDeferred > 0 {
            XCTAssertEqual(decision.diagnosticJobsAdmitted, 0)
          }
          evaluatedCases += 1
        }
      }
    }

    XCTAssertEqual(evaluatedCases, 32_768)
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
            availableSlots: input.2
          )
        )
        evaluatedCases += 1
      }
    }

    XCTAssertEqual(evaluatedCases, 3_072)
  }

  func testAdmissionArithmeticHandlesIntegerExtremesWithoutOverflow() throws {
    let saturated = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: Int.max,
        diagnosticJobsAwaiting: Int.max,
        availableSlots: Int.max
      )
    )
    XCTAssertEqual(saturated.recordedFramesAdmitted, Int.max)
    XCTAssertEqual(saturated.diagnosticJobsAdmitted, 0)
    XCTAssertEqual(saturated.recordedFramesDeferred, 0)
    XCTAssertEqual(saturated.diagnosticJobsDropped, Int.max)

    let diagnosticsOnly = CaptureAdmissionPolicy.decide(
      for: try CaptureLoad(
        recordedFramesAwaiting: 0,
        diagnosticJobsAwaiting: Int.max,
        availableSlots: Int.max
      )
    )
    XCTAssertEqual(diagnosticsOnly.diagnosticJobsAdmitted, Int.max)
    XCTAssertEqual(diagnosticsOnly.diagnosticJobsDropped, 0)
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
