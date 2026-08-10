import CaptureDomain

/// Non-degenerate safety limits for a moiré algorithm version. A limit of one
/// would permit total detail loss, so every upper bound is strictly below one.
public struct DetailPreservationLimits: Sendable, Equatable {
  public let maximumEdgeEnergyLoss: UnitInterval
  public let maximumTextEdgeEnergyLoss: UnitInterval
  public let maximumResidualInterferenceEnergy: UnitInterval
  public let maximumSuppressionStrength: UnitInterval

  public init(
    maximumEdgeEnergyLoss: UnitInterval,
    maximumTextEdgeEnergyLoss: UnitInterval,
    maximumResidualInterferenceEnergy: UnitInterval,
    maximumSuppressionStrength: UnitInterval
  ) throws {
    guard maximumTextEdgeEnergyLoss <= maximumEdgeEnergyLoss else {
      throw MetalDomainError.textLimitMustBeAtLeastAsStrict
    }
    guard maximumEdgeEnergyLoss.value < 1,
      maximumTextEdgeEnergyLoss.value < 1,
      maximumResidualInterferenceEnergy.value < 1,
      maximumSuppressionStrength.value > 0,
      maximumSuppressionStrength.value < 1
    else {
      throw MetalDomainError.degenerateSafetyLimit
    }

    self.maximumEdgeEnergyLoss = maximumEdgeEnergyLoss
    self.maximumTextEdgeEnergyLoss = maximumTextEdgeEnergyLoss
    self.maximumResidualInterferenceEnergy = maximumResidualInterferenceEnergy
    self.maximumSuppressionStrength = maximumSuppressionStrength
  }
}

/// Opaque measurements issued by a package-owned Metal adapter and bound to one
/// media artifact and algorithm version.
public struct DetailPreservationMeasurement: Sendable, Equatable {
  public let artifactID: MediaArtifactID
  public let algorithmVersion: AlgorithmVersion
  public let edgeEnergyLoss: UnitInterval
  public let textEdgeEnergyLoss: UnitInterval
  public let residualInterferenceEnergy: UnitInterval

  fileprivate init(
    artifactID: MediaArtifactID,
    algorithmVersion: AlgorithmVersion,
    edgeEnergyLoss: UnitInterval,
    textEdgeEnergyLoss: UnitInterval,
    residualInterferenceEnergy: UnitInterval
  ) {
    self.artifactID = artifactID
    self.algorithmVersion = algorithmVersion
    self.edgeEnergyLoss = edgeEnergyLoss
    self.textEdgeEnergyLoss = textEdgeEnergyLoss
    self.residualInterferenceEnergy = residualInterferenceEnergy
  }
}

/// Issuance capability held by the package-owned Metal measurement adapter.
package struct DetailPreservationMeasurementIssuer: Sendable {
  package let algorithmVersion: AlgorithmVersion

  package init(algorithmVersion: AlgorithmVersion) {
    self.algorithmVersion = algorithmVersion
  }

  package func issue(
    artifactID: MediaArtifactID,
    edgeEnergyLoss: UnitInterval,
    textEdgeEnergyLoss: UnitInterval,
    residualInterferenceEnergy: UnitInterval
  ) -> DetailPreservationMeasurement {
    DetailPreservationMeasurement(
      artifactID: artifactID,
      algorithmVersion: algorithmVersion,
      edgeEnergyLoss: edgeEnergyLoss,
      textEdgeEnergyLoss: textEdgeEnergyLoss,
      residualInterferenceEnergy: residualInterferenceEnergy
    )
  }
}

/// Opaque approval that cannot be constructed without an issued measurement.
public struct BoundedSuppression: Sendable, Equatable {
  public let artifactID: MediaArtifactID
  public let algorithmVersion: AlgorithmVersion
  public let approvedStrength: UnitInterval
  public let measuredDetailPreservation: DetailPreservationMeasurement

  fileprivate init(
    approvedStrength: UnitInterval,
    measuredDetailPreservation: DetailPreservationMeasurement
  ) {
    artifactID = measuredDetailPreservation.artifactID
    algorithmVersion = measuredDetailPreservation.algorithmVersion
    self.approvedStrength = approvedStrength
    self.measuredDetailPreservation = measuredDetailPreservation
  }
}

public enum SuppressionRefusal: String, Sendable, Equatable {
  case measurementUnavailable
  case edgeLossLimitExceeded
  case textEdgeLossLimitExceeded
  case residualInterferenceLimitExceeded
  case requestedStrengthExceedsLimit
}

public enum MoireSuppressionDecision: Sendable, Equatable {
  case apply(BoundedSuppression)
  case refuse(SuppressionRefusal)
}

/// Produces an applicable suppression token only after every bounded measurement
/// and the requested strength pass the declared limits.
public struct DetailPreservationPolicy: Sendable, Equatable {
  public let limits: DetailPreservationLimits

  public init(limits: DetailPreservationLimits) {
    self.limits = limits
  }

  public func evaluate(
    requestedStrength: UnitInterval,
    measurement: DetailPreservationMeasurement?
  ) -> MoireSuppressionDecision {
    guard let measurement else {
      return .refuse(.measurementUnavailable)
    }
    guard requestedStrength.value > 0,
      requestedStrength <= limits.maximumSuppressionStrength
    else {
      return .refuse(.requestedStrengthExceedsLimit)
    }
    guard measurement.edgeEnergyLoss <= limits.maximumEdgeEnergyLoss else {
      return .refuse(.edgeLossLimitExceeded)
    }
    guard measurement.textEdgeEnergyLoss <= limits.maximumTextEdgeEnergyLoss else {
      return .refuse(.textEdgeLossLimitExceeded)
    }
    guard
      measurement.residualInterferenceEnergy
        <= limits.maximumResidualInterferenceEnergy
    else {
      return .refuse(.residualInterferenceLimitExceeded)
    }

    return .apply(
      BoundedSuppression(
        approvedStrength: requestedStrength,
        measuredDetailPreservation: measurement
      )
    )
  }
}

public enum MetalDomainError: CodedDomainError, Equatable {
  case textLimitMustBeAtLeastAsStrict
  case degenerateSafetyLimit

  public var code: String {
    switch self {
    case .textLimitMustBeAtLeastAsStrict: "metal.detail_limit.invalid_order"
    case .degenerateSafetyLimit: "metal.detail_limit.degenerate"
    }
  }

  public var safeMessage: String {
    switch self {
    case .textLimitMustBeAtLeastAsStrict:
      "The text-edge loss limit must not exceed the general edge loss limit."
    case .degenerateSafetyLimit:
      "Moiré safety limits must preserve nonzero detail and bounded strength."
    }
  }
}
