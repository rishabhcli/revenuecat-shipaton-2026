import AnalysisDomain
import CameraDomain
import CaptureDomain
import XCTest

func requireSendable<T: Sendable>(_: T.Type) {}

func assertThrowsEqual<T, E: Error & Equatable>(
  _ expectedError: E,
  _ expression: @autoclosure () throws -> T,
  file: StaticString = #filePath,
  line: UInt = #line
) {
  do {
    _ = try expression()
    XCTFail("Expected \(expectedError), but no error was thrown.", file: file, line: line)
  } catch let actualError as E {
    XCTAssertEqual(actualError, expectedError, file: file, line: line)
  } catch {
    XCTFail(
      "Expected \(expectedError), but received \(error).",
      file: file,
      line: line
    )
  }
}

func allPermutations<Element>(_ input: [Element]) -> [[Element]] {
  guard !input.isEmpty else { return [[]] }

  var values = input
  var result: [[Element]] = []
  result.reserveCapacity(factorial(input.count))

  func generate(_ count: Int) {
    if count == 1 {
      result.append(values)
      return
    }

    generate(count - 1)
    for index in 0..<(count - 1) {
      if count.isMultiple(of: 2) {
        values.swapAt(index, count - 1)
      } else {
        values.swapAt(0, count - 1)
      }
      generate(count - 1)
    }
  }

  generate(values.count)
  return result
}

private func factorial(_ value: Int) -> Int {
  (1...max(value, 1)).reduce(1, *)
}

struct TestLiveEvidenceFactory {
  private var captureIssuer: LiveCaptureIssuer
  private let defaultBandingIssuer: BandingEvidenceIssuer
  private var nextTimestampNanoseconds: UInt64

  init(
    adapter: String = "test-camera-adapter",
    session: String = "test-live-session",
    source: String = "rear-wide",
    algorithm: String = "row-banding-v1",
    initialSequenceNumber: UInt64 = 0,
    initialTimestampNanoseconds: UInt64 = 1
  ) throws {
    captureIssuer = try LiveCaptureIssuer(
      adapterID: adapter,
      sessionReference: session,
      sourceID: CaptureSourceID(source),
      initialSequenceNumber: initialSequenceNumber
    )
    defaultBandingIssuer = BandingEvidenceIssuer(
      algorithmVersion: try AlgorithmVersion(algorithm)
    )
    nextTimestampNanoseconds = initialTimestampNanoseconds
  }

  mutating func issueFrameWindow(frameCount: Int) throws -> LiveFrameWindow {
    precondition(frameCount > 0)
    var frames: [LiveFrameReference] = []
    frames.reserveCapacity(frameCount)

    for _ in 0..<frameCount {
      frames.append(
        try captureIssuer.issueFrame(
          monotonicTimestampNanoseconds: nextTimestampNanoseconds
        )
      )
      nextTimestampNanoseconds += 1_000_000
    }
    return try LiveFrameWindow(frames: frames)
  }

  /// Issue one further frame from the same session and source at an exact
  /// monotonic timestamp, so a test can control an assessment's age precisely.
  /// The issuer still enforces that timestamps increase.
  mutating func issueFrame(atNanoseconds timestamp: UInt64) throws -> LiveFrameReference {
    let frame = try captureIssuer.issueFrame(monotonicTimestampNanoseconds: timestamp)
    nextTimestampNanoseconds = timestamp + 1_000_000
    return frame
  }

  /// Issue one further frame to stand in for "what the camera is delivering
  /// now", leaving the cursor free for the next window.
  mutating func issueFrame(advanceNanoseconds: UInt64) throws -> LiveFrameReference {
    nextTimestampNanoseconds += advanceNanoseconds
    return try issueFrame(atNanoseconds: nextTimestampNanoseconds)
  }

  mutating func issueEvidence(
    frameCount: Int,
    normalizedEnergy: Double,
    algorithm: String? = nil
  ) throws -> LiveBandingEvidence {
    let window = try issueFrameWindow(frameCount: frameCount)
    let issuer: BandingEvidenceIssuer
    if let algorithm {
      issuer = BandingEvidenceIssuer(
        algorithmVersion: try AlgorithmVersion(algorithm)
      )
    } else {
      issuer = defaultBandingIssuer
    }
    return try issuer.issue(
      frameWindow: window,
      energies: Array(
        repeating: try BandingEnergy(normalizedValue: normalizedEnergy),
        count: frameCount
      )
    )
  }
}

func defaultCorrectionThresholds() throws -> CorrectionThresholds {
  try CorrectionThresholds(
    minimumReduction: UnitInterval(0.20),
    minimumCandidateMargin: UnitInterval(0.10),
    minimumFrameCountPerWindow: 3
  )
}

func defaultFreshnessPolicy() throws -> RecordingFreshnessPolicy {
  try RecordingFreshnessPolicy(maximumAssessmentAgeNanoseconds: 500_000_000)
}

/// Gate an assessment under otherwise-ideal live conditions.
///
/// A test that is about the assessment should not silently also depend on
/// staleness, session identity, or component health, so those are held healthy
/// here and attacked directly in `RecordingConfidencePropertyTests`.
func liveRecordingConfidence(
  _ assessment: CorrectionConfidence,
  assessedThrough: LiveFrameReference,
  latestObservedFrame: LiveFrameReference,
  sourceCondition: SourceCondition,
  availability: AnalysisAvailability = .measuring
) throws -> RecordingConfidence {
  RecordingConfidenceGate.evaluate(
    RecordingConfidenceInputs(
      assessment: assessment,
      assessedThrough: assessedThrough,
      latestObservedFrame: latestObservedFrame,
      sourceCondition: sourceCondition,
      availability: availability
    ),
    policy: try defaultFreshnessPolicy()
  ).confidence
}
