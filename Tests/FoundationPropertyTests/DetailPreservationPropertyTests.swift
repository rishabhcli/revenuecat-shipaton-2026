import CaptureDomain
import MetalDomain
import XCTest

final class DetailPreservationPropertyTests: XCTestCase {
  func testSuppressionAppliesExactlyWhenEveryBoundPasses_6_561DistinctCases() throws {
    let limits = try DetailPreservationLimits(
      maximumEdgeEnergyLoss: UnitInterval(0.5),
      maximumTextEdgeEnergyLoss: UnitInterval(0.25),
      maximumResidualInterferenceEnergy: UnitInterval(0.375),
      maximumSuppressionStrength: UnitInterval(0.75)
    )
    let policy = DetailPreservationPolicy(limits: limits)
    let artifact = try MediaArtifactIssuer(issuerID: "metal-tests").issue(
      artifactReference: "artifact-1"
    )
    let algorithm = try AlgorithmVersion("moire-v1")
    let measurementIssuer = DetailPreservationMeasurementIssuer(
      algorithmVersion: algorithm
    )
    let values = try (0...8).map { try UnitInterval(Double($0) / 8) }
    var evaluatedCases = 0

    for strength in values {
      for edgeLoss in values {
        for textLoss in values {
          for residual in values {
            let measurement = measurementIssuer.issue(
              artifactID: artifact,
              edgeEnergyLoss: edgeLoss,
              textEdgeEnergyLoss: textLoss,
              residualInterferenceEnergy: residual
            )
            let decision = policy.evaluate(
              requestedStrength: strength,
              measurement: measurement
            )
            let shouldApply =
              strength.value > 0
              && strength <= limits.maximumSuppressionStrength
              && edgeLoss <= limits.maximumEdgeEnergyLoss
              && textLoss <= limits.maximumTextEdgeEnergyLoss
              && residual <= limits.maximumResidualInterferenceEnergy

            switch decision {
            case .apply(let approved):
              XCTAssertTrue(shouldApply)
              XCTAssertEqual(approved.artifactID, artifact)
              XCTAssertEqual(approved.algorithmVersion, algorithm)
              XCTAssertEqual(approved.approvedStrength, strength)
              XCTAssertEqual(approved.measuredDetailPreservation, measurement)
            case .refuse:
              XCTAssertFalse(shouldApply)
            }
            evaluatedCases += 1
          }
        }
      }
    }

    XCTAssertEqual(evaluatedCases, 6_561)
  }

  func testMissingMetricsAndEveryExceededLimitRefuseExactly() throws {
    let policy = DetailPreservationPolicy(
      limits: try DetailPreservationLimits(
        maximumEdgeEnergyLoss: UnitInterval(0.2),
        maximumTextEdgeEnergyLoss: UnitInterval(0.1),
        maximumResidualInterferenceEnergy: UnitInterval(0.3),
        maximumSuppressionStrength: UnitInterval(0.8)
      )
    )
    let artifact = try MediaArtifactIssuer(issuerID: "metal-tests").issue(
      artifactReference: "artifact-2"
    )
    let issuer = DetailPreservationMeasurementIssuer(
      algorithmVersion: try AlgorithmVersion("moire-v1")
    )

    func measurement(
      edge: Double = 0.1,
      text: Double = 0.05,
      residual: Double = 0.2
    ) throws -> DetailPreservationMeasurement {
      issuer.issue(
        artifactID: artifact,
        edgeEnergyLoss: try UnitInterval(edge),
        textEdgeEnergyLoss: try UnitInterval(text),
        residualInterferenceEnergy: try UnitInterval(residual)
      )
    }

    XCTAssertEqual(
      policy.evaluate(requestedStrength: try UnitInterval(0.5), measurement: nil),
      .refuse(.measurementUnavailable)
    )
    XCTAssertEqual(
      policy.evaluate(
        requestedStrength: try UnitInterval(0),
        measurement: try measurement()
      ),
      .refuse(.requestedStrengthExceedsLimit)
    )
    XCTAssertEqual(
      policy.evaluate(
        requestedStrength: try UnitInterval(0.9),
        measurement: try measurement()
      ),
      .refuse(.requestedStrengthExceedsLimit)
    )
    XCTAssertEqual(
      policy.evaluate(
        requestedStrength: try UnitInterval(0.5),
        measurement: try measurement(edge: 0.3)
      ),
      .refuse(.edgeLossLimitExceeded)
    )
    XCTAssertEqual(
      policy.evaluate(
        requestedStrength: try UnitInterval(0.5),
        measurement: try measurement(text: 0.2)
      ),
      .refuse(.textEdgeLossLimitExceeded)
    )
    XCTAssertEqual(
      policy.evaluate(
        requestedStrength: try UnitInterval(0.5),
        measurement: try measurement(residual: 0.4)
      ),
      .refuse(.residualInterferenceLimitExceeded)
    )
  }

  func testDegenerateSafetyLimitsAlwaysRefuseConstructionExactly() throws {
    assertThrowsEqual(
      MetalDomainError.textLimitMustBeAtLeastAsStrict,
      try DetailPreservationLimits(
        maximumEdgeEnergyLoss: UnitInterval(0.1),
        maximumTextEdgeEnergyLoss: UnitInterval(0.2),
        maximumResidualInterferenceEnergy: UnitInterval(0.2),
        maximumSuppressionStrength: UnitInterval(0.5)
      )
    )

    let degenerateInputs: [(Double, Double, Double, Double)] = [
      (1, 0.1, 0.2, 0.5),
      (0.2, 0.1, 1, 0.5),
      (0.2, 0.1, 0.2, 0),
      (0.2, 0.1, 0.2, 1),
    ]
    for input in degenerateInputs {
      assertThrowsEqual(
        MetalDomainError.degenerateSafetyLimit,
        try DetailPreservationLimits(
          maximumEdgeEnergyLoss: UnitInterval(input.0),
          maximumTextEdgeEnergyLoss: UnitInterval(input.1),
          maximumResidualInterferenceEnergy: UnitInterval(input.2),
          maximumSuppressionStrength: UnitInterval(input.3)
        )
      )
    }
  }
}
