import CameraDomain
import CaptureDomain

/// A normalized temporal-banding measurement in the closed interval `[0, 1]`.
public struct BandingEnergy: Hashable, Sendable, Comparable {
  public let normalizedValue: Double

  public init(normalizedValue: Double) throws {
    guard normalizedValue.isFinite else {
      throw AnalysisDomainError.nonFiniteBandingEnergy
    }
    guard (0...1).contains(normalizedValue) else {
      throw AnalysisDomainError.bandingEnergyOutsideUnitInterval
    }
    self.normalizedValue = normalizedValue
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.normalizedValue < rhs.normalizedValue
  }
}

/// One algorithm observation bound to an issued live-frame reference.
public struct BandingObservation: Sendable, Equatable {
  public let frame: LiveFrameReference
  public let energy: BandingEnergy
  public let algorithmVersion: AlgorithmVersion

  fileprivate init(
    frame: LiveFrameReference,
    energy: BandingEnergy,
    algorithmVersion: AlgorithmVersion
  ) {
    self.frame = frame
    self.energy = energy
    self.algorithmVersion = algorithmVersion
  }
}

/// A measured banding series whose observations are bound one-to-one to a
/// validated window of issued live camera frames.
public struct LiveBandingEvidence: Sendable, Equatable {
  public let frameWindow: LiveFrameWindow
  public let observations: [BandingObservation]
  public let algorithmVersion: AlgorithmVersion

  fileprivate init(
    frameWindow: LiveFrameWindow,
    observations: [BandingObservation],
    algorithmVersion: AlgorithmVersion
  ) {
    self.frameWindow = frameWindow
    self.observations = observations
    self.algorithmVersion = algorithmVersion
  }

  public var meanBandingEnergy: Double {
    observations.enumerated().reduce(0.0) { partialMean, item in
      partialMean + (item.element.energy.normalizedValue - partialMean) / Double(item.offset + 1)
    }
  }
}

/// Package-owned analysis adapters use this capability after measuring every
/// frame. External callers cannot mint live evidence or a verified correction.
package struct BandingEvidenceIssuer: Sendable {
  package let algorithmVersion: AlgorithmVersion

  package init(algorithmVersion: AlgorithmVersion) {
    self.algorithmVersion = algorithmVersion
  }

  package func issue(
    frameWindow: LiveFrameWindow,
    energies: [BandingEnergy]
  ) throws -> LiveBandingEvidence {
    guard !energies.isEmpty else {
      throw AnalysisDomainError.insufficientLiveEvidence(requiredFrameCount: 1)
    }
    guard energies.count == frameWindow.frames.count else {
      throw AnalysisDomainError.observationCountMismatch
    }

    let observations = zip(frameWindow.frames, energies).map { frame, energy in
      BandingObservation(
        frame: frame,
        energy: energy,
        algorithmVersion: algorithmVersion
      )
    }
    return LiveBandingEvidence(
      frameWindow: frameWindow,
      observations: observations,
      algorithmVersion: algorithmVersion
    )
  }
}

public enum UnsupportedSourceReason: String, Sendable, Equatable, CaseIterable {
  case unknownReadoutCalibration
  case sourceFrequencyChangingTooQuickly
  case exposureOutsideDeviceLimits
  case insufficientSceneBrightness
  case spatialInterferenceOnly
}

public enum SourceCondition: Sendable, Equatable {
  case stable
  case unstable
  case unsupported(UnsupportedSourceReason)
}

public struct CorrectionThresholds: Sendable, Equatable {
  public let minimumReduction: UnitInterval
  public let minimumCandidateMargin: UnitInterval
  public let minimumFrameCountPerWindow: Int

  public init(
    minimumReduction: UnitInterval,
    minimumCandidateMargin: UnitInterval,
    minimumFrameCountPerWindow: Int
  ) throws {
    guard minimumReduction.value > 0, minimumCandidateMargin.value > 0 else {
      throw AnalysisDomainError.nonPositiveConfidenceThreshold
    }
    guard minimumFrameCountPerWindow >= 2,
      minimumFrameCountPerWindow <= LiveFrameWindow.maximumFrameCount
    else {
      throw AnalysisDomainError.invalidMinimumFrameCount
    }
    self.minimumReduction = minimumReduction
    self.minimumCandidateMargin = minimumCandidateMargin
    self.minimumFrameCountPerWindow = minimumFrameCountPerWindow
  }
}

/// Opaque proof that a package-owned assessment accepted live, chronological
/// evidence from one capture session.
public struct VerifiedCorrection: Sendable, Equatable {
  public let captureSessionID: CaptureSessionID
  public let measuredReduction: UnitInterval
  public let candidateMargin: UnitInterval
  public let sampledFrameCount: Int
  public let algorithmVersion: AlgorithmVersion

  fileprivate init(
    captureSessionID: CaptureSessionID,
    measuredReduction: UnitInterval,
    candidateMargin: UnitInterval,
    sampledFrameCount: Int,
    algorithmVersion: AlgorithmVersion
  ) {
    self.captureSessionID = captureSessionID
    self.measuredReduction = measuredReduction
    self.candidateMargin = candidateMargin
    self.sampledFrameCount = sampledFrameCount
    self.algorithmVersion = algorithmVersion
  }
}

public struct UnstableCorrection: Sendable, Equatable {
  public let captureSessionID: CaptureSessionID
  public let measuredReduction: UnitInterval
  public let sampledFrameCount: Int
  public let algorithmVersion: AlgorithmVersion

  fileprivate init(
    captureSessionID: CaptureSessionID,
    measuredReduction: UnitInterval,
    sampledFrameCount: Int,
    algorithmVersion: AlgorithmVersion
  ) {
    self.captureSessionID = captureSessionID
    self.measuredReduction = measuredReduction
    self.sampledFrameCount = sampledFrameCount
    self.algorithmVersion = algorithmVersion
  }
}

public enum CorrectionRefusal: Sendable, Equatable {
  case unsupported(UnsupportedSourceReason)
  case insufficientLiveEvidence(requiredFrameCount: Int)
  case mismatchedCaptureSession
  case mismatchedCaptureSource
  case algorithmVersionMismatch
  case nonChronologicalEvidence
  case zeroBaselineEnergy
  case insufficientImprovement
  case ambiguousCandidate
}

/// The only `verified` payload construction path checks live evidence, source
/// stability, improvement, and candidate margin together.
public enum CorrectionConfidence: Sendable, Equatable {
  case verified(VerifiedCorrection)
  case unstable(UnstableCorrection)
  case unavailable(CorrectionRefusal)
}

public enum CorrectionAssessment {
  /// Reserved for package-owned analysis/application orchestration so ordinary
  /// library callers cannot manufacture a verified result from chosen numbers.
  package static func evaluate(
    before: LiveBandingEvidence,
    after: LiveBandingEvidence,
    sourceCondition: SourceCondition,
    candidateMargin: UnitInterval,
    thresholds: CorrectionThresholds
  ) -> CorrectionConfidence {
    if case .unsupported(let reason) = sourceCondition {
      return .unavailable(.unsupported(reason))
    }

    guard before.observations.count >= thresholds.minimumFrameCountPerWindow,
      after.observations.count >= thresholds.minimumFrameCountPerWindow
    else {
      return .unavailable(
        .insufficientLiveEvidence(
          requiredFrameCount: thresholds.minimumFrameCountPerWindow
        )
      )
    }
    guard before.frameWindow.sessionID == after.frameWindow.sessionID else {
      return .unavailable(.mismatchedCaptureSession)
    }
    guard before.frameWindow.sourceID == after.frameWindow.sourceID else {
      return .unavailable(.mismatchedCaptureSource)
    }
    guard before.algorithmVersion == after.algorithmVersion else {
      return .unavailable(.algorithmVersionMismatch)
    }
    guard let beforeLast = before.frameWindow.frames.last,
      let afterFirst = after.frameWindow.frames.first,
      beforeLast.monotonicTimestampNanoseconds < afterFirst.monotonicTimestampNanoseconds,
      beforeLast.sequenceNumber < afterFirst.sequenceNumber
    else {
      return .unavailable(.nonChronologicalEvidence)
    }
    guard before.meanBandingEnergy > 0 else {
      return .unavailable(.zeroBaselineEnergy)
    }

    let reductionValue = 1 - (after.meanBandingEnergy / before.meanBandingEnergy)
    guard reductionValue.isFinite,
      reductionValue >= thresholds.minimumReduction.value,
      let reduction = try? UnitInterval(reductionValue)
    else {
      return .unavailable(.insufficientImprovement)
    }

    let totalFrameCount = before.observations.count + after.observations.count
    switch sourceCondition {
    case .unstable:
      return .unstable(
        UnstableCorrection(
          captureSessionID: after.frameWindow.sessionID,
          measuredReduction: reduction,
          sampledFrameCount: totalFrameCount,
          algorithmVersion: after.algorithmVersion
        )
      )
    case .stable:
      guard candidateMargin >= thresholds.minimumCandidateMargin else {
        return .unavailable(.ambiguousCandidate)
      }
      return .verified(
        VerifiedCorrection(
          captureSessionID: after.frameWindow.sessionID,
          measuredReduction: reduction,
          candidateMargin: candidateMargin,
          sampledFrameCount: totalFrameCount,
          algorithmVersion: after.algorithmVersion
        )
      )
    case .unsupported(let reason):
      return .unavailable(.unsupported(reason))
    }
  }
}

public enum AnalysisDomainError: CodedDomainError, Equatable {
  case nonFiniteBandingEnergy
  case bandingEnergyOutsideUnitInterval
  case observationCountMismatch
  case insufficientLiveEvidence(requiredFrameCount: Int)
  case nonPositiveConfidenceThreshold
  case invalidMinimumFrameCount
  case freshnessBudgetOutsideSupportedRange(smallestNanoseconds: UInt64, largestNanoseconds: UInt64)

  public var code: String {
    switch self {
    case .nonFiniteBandingEnergy: "analysis.banding_energy.non_finite"
    case .bandingEnergyOutsideUnitInterval: "analysis.banding_energy.outside_unit_interval"
    case .observationCountMismatch: "analysis.evidence.observation_count_mismatch"
    case .insufficientLiveEvidence: "analysis.evidence.insufficient"
    case .nonPositiveConfidenceThreshold: "analysis.threshold.non_positive"
    case .invalidMinimumFrameCount: "analysis.threshold.invalid_frame_count"
    case .freshnessBudgetOutsideSupportedRange: "analysis.freshness.outside_supported_range"
    }
  }

  public var safeMessage: String {
    switch self {
    case .nonFiniteBandingEnergy:
      "Banding energy must be finite."
    case .bandingEnergyOutsideUnitInterval:
      "Normalized banding energy must be between zero and one."
    case .observationCountMismatch:
      "Every issued live frame must have exactly one observation."
    case .insufficientLiveEvidence:
      "More measured live frames are required."
    case .nonPositiveConfidenceThreshold:
      "Reduction and candidate-margin thresholds must be greater than zero."
    case .invalidMinimumFrameCount:
      "The minimum frame count is outside the supported frame-window range."
    case .freshnessBudgetOutsideSupportedRange(let smallest, let largest):
      "The recording freshness budget must be between \(smallest) and \(largest) nanoseconds."
    }
  }
}
