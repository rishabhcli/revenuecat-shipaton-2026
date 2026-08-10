import CaptureDomain
import EvaluationDomain
import XCTest

final class EvaluationEvidencePropertyTests: XCTestCase {
  func testIssuedPerformanceClaimRetainsCompleteContextAndManifestProvenance() throws {
    let context = try compatibilityContext()
    let issuer = try evaluationIssuer()
    let measurement = EvaluationMeasurement.normalizedBandingReduction(
      try UnitInterval(0.82)
    )
    let claim = try issuer.issueClaim(
      context: context,
      measurement: measurement,
      sampleCount: 50
    )

    XCTAssertEqual(claim.context.device.label.rawValue, "iPhone test device")
    XCTAssertEqual(claim.context.lens.label.rawValue, "rear wide")
    XCTAssertEqual(claim.context.format.label.rawValue, "1920x1080 at 30 fps")
    XCTAssertEqual(claim.context.source.label.rawValue, "original 60 Hz test pattern")
    XCTAssertEqual(claim.metric, .normalizedBandingReduction)
    XCTAssertEqual(claim.unit, .ratio)
    XCTAssertEqual(claim.value, 0.82)
    XCTAssertEqual(claim.provenance.sampleCount, 50)
    XCTAssertEqual(
      claim.provenance.immutableManifestSHA256.lowercaseHex,
      String(repeating: "a", count: 64)
    )
    XCTAssertEqual(claim.provenance.evaluationRunID.description, "evaluation-run-1")
    XCTAssertEqual(claim.provenance.algorithmVersion.description, "row-banding-v1")
  }

  func testUnicodeCompatibilityLabelsRefuseUnsafeForms_1_024DistinctLabels() {
    var evaluatedLabels = 0

    for index in 0..<256 {
      let cases: [(String, Bool)] = [
        ("\u{00A0}label-\(index)", true),
        ("label-\(index)\u{00A0}", true),
        ("label-\(index)\u{200B}x", false),
        ("label-\(index)\u{202E}x", false),
      ]

      for (invalid, isOuterWhitespace) in cases {
        if isOuterWhitespace {
          assertEveryLabelWrapperRefuses(
            invalid,
            expected: { .contextFieldHasOuterWhitespace($0) }
          )
        } else {
          assertEveryLabelWrapperRefuses(
            invalid,
            expected: { .contextFieldContainsUnsafeUnicode($0) }
          )
        }
        evaluatedLabels += 1
      }
    }

    XCTAssertEqual(evaluatedLabels, 1_024)
  }

  func testLabelsRefuseEmptyOversizedControlAndNoncharacterBoundariesExactly() throws {
    assertEveryLabelWrapperRefuses("", expected: { .emptyContextField($0) })
    let oversized = String(
      repeating: "x",
      count: EvidenceLabel.maximumUTF8Bytes + 1
    )
    assertEveryLabelWrapperRefuses(
      oversized,
      expected: {
        .contextFieldTooLong(
          $0,
          maximumUTF8Bytes: EvidenceLabel.maximumUTF8Bytes
        )
      }
    )

    for invalid in [
      "a\tb",
      "a\nb",
      "a\u{00A0}b",
      "a\u{E000}b",
      "a\u{0378}b",
    ] {
      assertEveryLabelWrapperRefuses(
        invalid,
        expected: { .contextFieldContainsUnsafeUnicode($0) }
      )
    }

    XCTAssertEqual(try DeviceIdentity("Écran 60 Hz").label.rawValue, "Écran 60 Hz")
    XCTAssertEqual(try VisualSourceIdentity("LED wall 🟦").label.rawValue, "LED wall 🟦")
    XCTAssertEqual(try DeviceIdentity("E\u{0301}cran").label.rawValue, "E\u{0301}cran")
    XCTAssertEqual(try VisualSourceIdentity("🟦\u{FE0F}").label.rawValue, "🟦\u{FE0F}")
  }

  func testMarkOnlyCompatibilityLabelsRefuse_1_027DistinctLabels() {
    let marks = ["\u{034F}", "\u{FE0F}", "\u{0301}"]
    var labels = marks
    labels.reserveCapacity(1_027)

    // Seven base-three positions yield 2,187 possible mark-only strings. The
    // first 1,024 provide a deterministic property space distinct from the
    // three single-scalar boundary cases above.
    for caseIndex in 0..<1_024 {
      var encodedIndex = caseIndex
      var label = ""
      for _ in 0..<7 {
        label.append(contentsOf: marks[encodedIndex % marks.count])
        encodedIndex /= marks.count
      }
      labels.append(label)
    }

    XCTAssertEqual(labels.count, 1_027)
    XCTAssertEqual(Set(labels).count, 1_027)
    for label in labels {
      assertEveryLabelWrapperRefuses(
        label,
        expected: { .contextFieldHasNoVisibleBase($0) }
      )
    }
  }

  func testManifestIssuerRefusesEveryMalformedDigestExactly() throws {
    let invalidDigests = [
      String(repeating: "a", count: 63),
      String(repeating: "a", count: 65),
      String(repeating: "A", count: 64),
      String(repeating: "g", count: 64),
      String(repeating: "0", count: 63) + "é",
    ]

    for digest in invalidDigests {
      assertThrowsEqual(
        EvaluationDomainError.invalidManifestSHA256,
        try EvaluationEvidenceIssuer(
          immutableManifestSHA256Hex: digest,
          evaluationRunReference: "evaluation-run-1",
          algorithmVersion: AlgorithmVersion("row-banding-v1")
        )
      )
    }
  }

  func testClaimIssuerRefusesNonPositiveSampleCounts_1_024DistinctCounts() throws {
    let issuer = try evaluationIssuer()
    let context = try compatibilityContext()
    let measurement = EvaluationMeasurement.convergenceDurationMilliseconds(
      try ConvergenceDurationMilliseconds(125)
    )
    var evaluatedCounts = 0

    for offset in 0..<1_024 {
      assertThrowsEqual(
        EvaluationDomainError.nonPositiveSampleCount,
        try issuer.issueClaim(
          context: context,
          measurement: measurement,
          sampleCount: -offset
        )
      )
      evaluatedCounts += 1
    }

    XCTAssertEqual(evaluatedCounts, 1_024)
  }

  func testEveryTypedMetricRequiresCompleteFourAxisContext_6DistinctMetrics() throws {
    let measurements: [(EvaluationMeasurement, EvaluationMetric, EvaluationUnit, Double)] = [
      (
        .normalizedBandingReduction(try UnitInterval(0.8)), .normalizedBandingReduction, .ratio, 0.8
      ),
      (
        .convergenceDurationMilliseconds(try ConvergenceDurationMilliseconds(125)),
        .convergenceDuration,
        .milliseconds,
        125
      ),
      (
        .droppedFramesPerThousand(try FramesPerThousand(3)),
        .droppedFrameRate,
        .framesPerThousand,
        3
      ),
      (
        .audioSynchronizationOffsetMilliseconds(
          try AudioSynchronizationOffsetMilliseconds(-4.5)
        ),
        .audioSynchronizationOffset,
        .milliseconds,
        -4.5
      ),
      (.edgeEnergyPreservation(try UnitInterval(0.95)), .edgeEnergyPreservation, .ratio, 0.95),
      (.moirePeakEnergyReduction(try UnitInterval(0.7)), .moirePeakEnergyReduction, .ratio, 0.7),
    ]

    let issuer = try evaluationIssuer()
    let context = try compatibilityContext()
    var evaluatedMetrics = 0

    for (measurement, metric, unit, value) in measurements {
      XCTAssertEqual(measurement.metric, metric)
      XCTAssertEqual(measurement.unit, unit)
      XCTAssertEqual(measurement.value, value)

      let claim = try issuer.issueClaim(
        context: context,
        measurement: measurement,
        sampleCount: 1
      )
      XCTAssertFalse(claim.context.device.label.rawValue.isEmpty)
      XCTAssertFalse(claim.context.lens.label.rawValue.isEmpty)
      XCTAssertFalse(claim.context.format.label.rawValue.isEmpty)
      XCTAssertFalse(claim.context.source.label.rawValue.isEmpty)
      evaluatedMetrics += 1
    }

    XCTAssertEqual(evaluatedMetrics, 6)
  }

  func testFramesPerThousandRefusesOutOfRangeValues_2_048DistinctCases() {
    var evaluatedCases = 0

    for numerator in 1...1_024 {
      let distance = Double(numerator) / 1_024
      for invalid in [-distance, 1_000 + distance] {
        assertThrowsEqual(
          EvaluationDomainError.framesPerThousandOutsideRange,
          try FramesPerThousand(invalid)
        )
        evaluatedCases += 1
      }
    }
    XCTAssertEqual(evaluatedCases, 2_048)

    for nonFinite in [Double.nan, .infinity, -.infinity] {
      assertThrowsEqual(
        EvaluationDomainError.nonFiniteMeasurement,
        try FramesPerThousand(nonFinite)
      )
    }
  }

  func testBoundedMillisecondMeasurementsRefuseHugeFiniteValues_4_096DistinctCases() throws {
    var evaluatedCases = 0

    for numerator in 1...1_024 {
      let distance = Double(numerator) / 1_024
      for invalidDuration in [
        -distance,
        ConvergenceDurationMilliseconds.maximumRepresentableValue + distance,
      ] {
        assertThrowsEqual(
          EvaluationDomainError.convergenceDurationOutsideRange,
          try ConvergenceDurationMilliseconds(invalidDuration)
        )
        evaluatedCases += 1
      }

      for invalidOffset in [
        -AudioSynchronizationOffsetMilliseconds.maximumAbsoluteRepresentableValue - distance,
        AudioSynchronizationOffsetMilliseconds.maximumAbsoluteRepresentableValue + distance,
      ] {
        assertThrowsEqual(
          EvaluationDomainError.audioSynchronizationOffsetOutsideRange,
          try AudioSynchronizationOffsetMilliseconds(invalidOffset)
        )
        evaluatedCases += 1
      }
    }

    XCTAssertEqual(evaluatedCases, 4_096)
    XCTAssertEqual(try ConvergenceDurationMilliseconds(0).value, 0)
    XCTAssertEqual(
      try ConvergenceDurationMilliseconds(
        ConvergenceDurationMilliseconds.maximumRepresentableValue
      ).value,
      600_000
    )
    XCTAssertEqual(
      try AudioSynchronizationOffsetMilliseconds(
        -AudioSynchronizationOffsetMilliseconds.maximumAbsoluteRepresentableValue
      ).value,
      -60_000
    )
    XCTAssertEqual(
      try AudioSynchronizationOffsetMilliseconds(
        AudioSynchronizationOffsetMilliseconds.maximumAbsoluteRepresentableValue
      ).value,
      60_000
    )

    for nonFinite in [Double.nan, Double.infinity, -Double.infinity] {
      assertThrowsEqual(
        EvaluationDomainError.nonFiniteMeasurement,
        try ConvergenceDurationMilliseconds(nonFinite)
      )
      assertThrowsEqual(
        EvaluationDomainError.nonFiniteMeasurement,
        try AudioSynchronizationOffsetMilliseconds(nonFinite)
      )
    }
  }

  private func compatibilityContext() throws -> CompatibilityContext {
    try CompatibilityContext(
      device: DeviceIdentity("iPhone test device"),
      lens: LensIdentity("rear wide"),
      format: CaptureFormatIdentity("1920x1080 at 30 fps"),
      source: VisualSourceIdentity("original 60 Hz test pattern")
    )
  }

  private func evaluationIssuer() throws -> EvaluationEvidenceIssuer {
    try EvaluationEvidenceIssuer(
      immutableManifestSHA256Hex: String(repeating: "a", count: 64),
      evaluationRunReference: "evaluation-run-1",
      algorithmVersion: AlgorithmVersion("row-banding-v1")
    )
  }

  private func assertEveryLabelWrapperRefuses(
    _ value: String,
    expected: (EvaluationContextField) -> EvaluationDomainError,
    file: StaticString = #filePath,
    line: UInt = #line
  ) {
    assertThrowsEqual(
      expected(.device),
      try DeviceIdentity(value),
      file: file,
      line: line
    )
    assertThrowsEqual(
      expected(.lens),
      try LensIdentity(value),
      file: file,
      line: line
    )
    assertThrowsEqual(
      expected(.format),
      try CaptureFormatIdentity(value),
      file: file,
      line: line
    )
    assertThrowsEqual(
      expected(.source),
      try VisualSourceIdentity(value),
      file: file,
      line: line
    )
  }
}
