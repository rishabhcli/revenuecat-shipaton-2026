import CaptureDomain
import XCTest

final class CaptureDomainPropertyTests: XCTestCase {
  func testUnitIntervalRefusesOutOfRangeFiniteValues_2_048DistinctCases() {
    var evaluatedCases = 0

    for numerator in 1...1_024 {
      let distance = Double(numerator) / 1_024
      for invalid in [-distance, 1 + distance] {
        assertThrowsEqual(
          DomainValidationError.valueOutsideUnitInterval,
          try UnitInterval(invalid)
        )
        evaluatedCases += 1
      }
    }

    XCTAssertEqual(evaluatedCases, 2_048)
  }

  func testUnitIntervalRefusesNaNAndInfinityExactly() throws {
    for nonFinite in [Double.nan, Double.infinity, -Double.infinity] {
      assertThrowsEqual(
        DomainValidationError.nonFiniteNumber,
        try UnitInterval(nonFinite)
      )
    }
    XCTAssertEqual(try UnitInterval(0).value, 0)
    XCTAssertEqual(try UnitInterval(1).value, 1)
  }

  func testOperationalEventsRefuseNonPositiveCounts_1_024DistinctCounts() throws {
    let version = try AlgorithmVersion("row-banding-v1")
    var evaluatedCounts = 0

    for offset in 0..<1_024 {
      let invalidCount = -offset
      assertThrowsEqual(
        OperationalEventError.nonPositiveCount,
        try ConfigurationAcceptedEvent(serviceCount: invalidCount)
      )
      assertThrowsEqual(
        OperationalEventError.nonPositiveCount,
        try CorrectionAssessedEvent(
          algorithmVersion: version,
          sampledFrameCount: invalidCount,
          outcome: .insufficientEvidence
        )
      )
      evaluatedCounts += 1
    }

    XCTAssertEqual(evaluatedCounts, 1_024)
  }

  func testStableIdentifiersRejectEveryInvalidBoundaryExactly() throws {
    assertThrowsEqual(
      DomainValidationError.emptyIdentifier,
      try StableIdentifier("")
    )
    for invalid in [
      "contains whitespace",
      "control\u{0000}",
      "unicode-é",
      "slash/value",
      "colon:value",
    ] {
      assertThrowsEqual(
        DomainValidationError.invalidIdentifierCharacter,
        try StableIdentifier(invalid)
      )
    }

    assertThrowsEqual(
      DomainValidationError.identifierTooLong(
        maximumUTF8Bytes: StableIdentifier.maximumUTF8Bytes
      ),
      try StableIdentifier(
        String(repeating: "x", count: StableIdentifier.maximumUTF8Bytes + 1)
      )
    )
    XCTAssertEqual(try StableIdentifier("analysis-v1.2_build").rawValue, "analysis-v1.2_build")
  }

  func testIssuedArtifactIdentitiesAreNamespacedAndDistinct() throws {
    let issuer = try MediaArtifactIssuer(issuerID: "camera-adapter")
    let first = try issuer.issue(artifactReference: "capture-0001")
    let second = try issuer.issue(artifactReference: "capture-0002")

    XCTAssertEqual(first.issuerID.rawValue, "camera-adapter")
    XCTAssertEqual(first.artifactReference.rawValue, "capture-0001")
    XCTAssertNotEqual(first, second)
    requireSendable(MediaArtifactID.self)
  }

  func testArtifactIdentityIsStructuralAndAcceptsIndependentMaximumComponents() throws {
    let ambiguousFirst = try MediaArtifactIssuer(issuerID: "a.b").issue(
      artifactReference: "c"
    )
    let ambiguousSecond = try MediaArtifactIssuer(issuerID: "a").issue(
      artifactReference: "b.c"
    )
    XCTAssertNotEqual(ambiguousFirst, ambiguousSecond)
    XCTAssertNotEqual(ambiguousFirst.description, ambiguousSecond.description)

    let maximumIssuer = String(
      repeating: "i",
      count: StableIdentifier.maximumUTF8Bytes
    )
    let maximumReference = String(
      repeating: "r",
      count: StableIdentifier.maximumUTF8Bytes
    )
    let maximumArtifact = try MediaArtifactIssuer(issuerID: maximumIssuer).issue(
      artifactReference: maximumReference
    )
    XCTAssertEqual(maximumArtifact.issuerID.rawValue.utf8.count, 96)
    XCTAssertEqual(maximumArtifact.artifactReference.rawValue.utf8.count, 96)
  }

  func testSafeValidationMessagesNeverEchoRejectedCallerText() {
    let callerText = "private-user-value"
    let errors: [DomainValidationError] = [
      .emptyIdentifier,
      .identifierTooLong(maximumUTF8Bytes: 96),
      .invalidIdentifierCharacter,
      .nonFiniteNumber,
      .valueOutsideUnitInterval,
    ]

    XCTAssertTrue(errors.allSatisfy { !$0.safeMessage.contains(callerText) })
  }
}
