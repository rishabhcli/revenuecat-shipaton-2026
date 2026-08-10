import CaptureDomain

public enum EvaluationContextField: String, Sendable, Hashable {
  case device
  case lens
  case format
  case source
}

public struct EvidenceLabel: Hashable, Sendable, CustomStringConvertible {
  public static let maximumUTF8Bytes = 128

  public let rawValue: String

  fileprivate init(_ rawValue: String, field: EvaluationContextField) throws {
    guard !rawValue.isEmpty else {
      throw EvaluationDomainError.emptyContextField(field)
    }
    guard rawValue.utf8.count <= Self.maximumUTF8Bytes else {
      throw EvaluationDomainError.contextFieldTooLong(
        field,
        maximumUTF8Bytes: Self.maximumUTF8Bytes
      )
    }
    guard rawValue.unicodeScalars.first?.properties.isWhitespace != true,
      rawValue.unicodeScalars.last?.properties.isWhitespace != true
    else {
      throw EvaluationDomainError.contextFieldHasOuterWhitespace(field)
    }
    guard rawValue.unicodeScalars.allSatisfy(Self.isAllowedScalar) else {
      throw EvaluationDomainError.contextFieldContainsUnsafeUnicode(field)
    }
    guard rawValue.unicodeScalars.contains(where: Self.isVisibleBaseScalar) else {
      throw EvaluationDomainError.contextFieldHasNoVisibleBase(field)
    }

    self.rawValue = rawValue
  }

  public var description: String { rawValue }

  private static func isAllowedScalar(_ scalar: Unicode.Scalar) -> Bool {
    if scalar.properties.isWhitespace {
      return scalar.value == 0x20
    }

    switch scalar.properties.generalCategory {
    case .control, .format, .lineSeparator, .paragraphSeparator,
      .privateUse, .surrogate, .unassigned:
      return false
    default:
      return true
    }
  }

  /// A mark can safely modify a visible scalar but cannot make a label visible
  /// by itself. Requiring one base category preserves composed Unicode while
  /// refusing mark-only and variation-selector-only labels.
  private static func isVisibleBaseScalar(_ scalar: Unicode.Scalar) -> Bool {
    switch scalar.properties.generalCategory {
    case .uppercaseLetter, .lowercaseLetter, .titlecaseLetter, .modifierLetter,
      .otherLetter, .decimalNumber, .letterNumber, .otherNumber,
      .connectorPunctuation, .dashPunctuation, .openPunctuation, .closePunctuation,
      .initialPunctuation, .finalPunctuation, .otherPunctuation,
      .mathSymbol, .currencySymbol, .modifierSymbol, .otherSymbol:
      return true
    default:
      return false
    }
  }
}

public struct DeviceIdentity: Hashable, Sendable {
  public let label: EvidenceLabel

  public init(_ value: String) throws {
    label = try EvidenceLabel(value, field: .device)
  }
}

public struct LensIdentity: Hashable, Sendable {
  public let label: EvidenceLabel

  public init(_ value: String) throws {
    label = try EvidenceLabel(value, field: .lens)
  }
}

public struct CaptureFormatIdentity: Hashable, Sendable {
  public let label: EvidenceLabel

  public init(_ value: String) throws {
    label = try EvidenceLabel(value, field: .format)
  }
}

public struct VisualSourceIdentity: Hashable, Sendable {
  public let label: EvidenceLabel

  public init(_ value: String) throws {
    label = try EvidenceLabel(value, field: .source)
  }
}

/// Every compatibility or performance claim carries all four context axes.
public struct CompatibilityContext: Hashable, Sendable {
  public let device: DeviceIdentity
  public let lens: LensIdentity
  public let format: CaptureFormatIdentity
  public let source: VisualSourceIdentity

  public init(
    device: DeviceIdentity,
    lens: LensIdentity,
    format: CaptureFormatIdentity,
    source: VisualSourceIdentity
  ) {
    self.device = device
    self.lens = lens
    self.format = format
    self.source = source
  }
}

public struct SHA256Digest: Hashable, Sendable, CustomStringConvertible {
  public let lowercaseHex: String

  fileprivate init(lowercaseHex: String) {
    self.lowercaseHex = lowercaseHex
  }

  public var description: String { lowercaseHex }
}

public struct EvaluationRunID: Hashable, Sendable, CustomStringConvertible {
  public let identifier: StableIdentifier

  fileprivate init(identifier: StableIdentifier) {
    self.identifier = identifier
  }

  public var description: String { identifier.rawValue }
}

public struct EvidenceProvenance: Hashable, Sendable {
  public let immutableManifestSHA256: SHA256Digest
  public let evaluationRunID: EvaluationRunID
  public let algorithmVersion: AlgorithmVersion
  public let sampleCount: Int

  fileprivate init(
    immutableManifestSHA256: SHA256Digest,
    evaluationRunID: EvaluationRunID,
    algorithmVersion: AlgorithmVersion,
    sampleCount: Int
  ) {
    self.immutableManifestSHA256 = immutableManifestSHA256
    self.evaluationRunID = evaluationRunID
    self.algorithmVersion = algorithmVersion
    self.sampleCount = sampleCount
  }
}

public enum EvaluationMetric: String, Sendable, Hashable {
  case normalizedBandingReduction
  case convergenceDuration
  case droppedFrameRate
  case audioSynchronizationOffset
  case edgeEnergyPreservation
  case moirePeakEnergyReduction
}

public enum EvaluationUnit: String, Sendable, Hashable {
  case ratio
  case milliseconds
  case framesPerThousand
}

public struct FramesPerThousand: Hashable, Sendable, Comparable {
  public let value: Double

  public init(_ value: Double) throws {
    guard value.isFinite else {
      throw EvaluationDomainError.nonFiniteMeasurement
    }
    guard (0...1_000).contains(value) else {
      throw EvaluationDomainError.framesPerThousandOutsideRange
    }
    self.value = value
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.value < rhs.value
  }
}

/// Representation bound, not a performance promise: convergence measurements
/// longer than ten minutes are invalid for this capture workflow.
public struct ConvergenceDurationMilliseconds: Hashable, Sendable, Comparable {
  public static let maximumRepresentableValue = 600_000.0

  public let value: Double

  public init(_ value: Double) throws {
    guard value.isFinite else {
      throw EvaluationDomainError.nonFiniteMeasurement
    }
    guard (0...Self.maximumRepresentableValue).contains(value) else {
      throw EvaluationDomainError.convergenceDurationOutsideRange
    }
    self.value = value
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.value < rhs.value
  }
}

/// Representation bound, not an acceptance threshold: offsets outside one
/// minute in either direction indicate invalid evidence or clock association.
public struct AudioSynchronizationOffsetMilliseconds: Hashable, Sendable, Comparable {
  public static let maximumAbsoluteRepresentableValue = 60_000.0

  public let value: Double

  public init(_ value: Double) throws {
    guard value.isFinite else {
      throw EvaluationDomainError.nonFiniteMeasurement
    }
    guard value >= -Self.maximumAbsoluteRepresentableValue,
      value <= Self.maximumAbsoluteRepresentableValue
    else {
      throw EvaluationDomainError.audioSynchronizationOffsetOutsideRange
    }
    self.value = value
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.value < rhs.value
  }
}

/// Metric and unit are coupled in the type so impossible pairs cannot be built.
public enum EvaluationMeasurement: Hashable, Sendable {
  case normalizedBandingReduction(UnitInterval)
  case convergenceDurationMilliseconds(ConvergenceDurationMilliseconds)
  case droppedFramesPerThousand(FramesPerThousand)
  case audioSynchronizationOffsetMilliseconds(AudioSynchronizationOffsetMilliseconds)
  case edgeEnergyPreservation(UnitInterval)
  case moirePeakEnergyReduction(UnitInterval)

  public var metric: EvaluationMetric {
    switch self {
    case .normalizedBandingReduction: .normalizedBandingReduction
    case .convergenceDurationMilliseconds: .convergenceDuration
    case .droppedFramesPerThousand: .droppedFrameRate
    case .audioSynchronizationOffsetMilliseconds: .audioSynchronizationOffset
    case .edgeEnergyPreservation: .edgeEnergyPreservation
    case .moirePeakEnergyReduction: .moirePeakEnergyReduction
    }
  }

  public var unit: EvaluationUnit {
    switch self {
    case .normalizedBandingReduction, .edgeEnergyPreservation,
      .moirePeakEnergyReduction:
      .ratio
    case .convergenceDurationMilliseconds, .audioSynchronizationOffsetMilliseconds:
      .milliseconds
    case .droppedFramesPerThousand:
      .framesPerThousand
    }
  }

  public var value: Double {
    switch self {
    case .normalizedBandingReduction(let value),
      .edgeEnergyPreservation(let value),
      .moirePeakEnergyReduction(let value):
      value.value
    case .convergenceDurationMilliseconds(let value):
      value.value
    case .droppedFramesPerThousand(let value):
      value.value
    case .audioSynchronizationOffsetMilliseconds(let value):
      value.value
    }
  }
}

/// Opaque claim issued only from a validated, immutable evidence manifest.
public struct PerformanceClaim: Hashable, Sendable {
  public let context: CompatibilityContext
  public let measurement: EvaluationMeasurement
  public let provenance: EvidenceProvenance

  fileprivate init(
    context: CompatibilityContext,
    measurement: EvaluationMeasurement,
    provenance: EvidenceProvenance
  ) {
    self.context = context
    self.measurement = measurement
    self.provenance = provenance
  }

  public var metric: EvaluationMetric { measurement.metric }
  public var value: Double { measurement.value }
  public var unit: EvaluationUnit { measurement.unit }
}

/// Package-owned evaluation adapters hold this capability after validating an
/// immutable manifest and a reproducible run identifier.
package struct EvaluationEvidenceIssuer: Sendable {
  package let immutableManifestSHA256: SHA256Digest
  package let evaluationRunID: EvaluationRunID
  package let algorithmVersion: AlgorithmVersion

  package init(
    immutableManifestSHA256Hex: String,
    evaluationRunReference: String,
    algorithmVersion: AlgorithmVersion
  ) throws {
    guard immutableManifestSHA256Hex.utf8.count == 64,
      immutableManifestSHA256Hex.utf8.allSatisfy(Self.isLowercaseHexByte)
    else {
      throw EvaluationDomainError.invalidManifestSHA256
    }

    immutableManifestSHA256 = SHA256Digest(lowercaseHex: immutableManifestSHA256Hex)
    evaluationRunID = EvaluationRunID(
      identifier: try StableIdentifier(evaluationRunReference)
    )
    self.algorithmVersion = algorithmVersion
  }

  package func issueClaim(
    context: CompatibilityContext,
    measurement: EvaluationMeasurement,
    sampleCount: Int
  ) throws -> PerformanceClaim {
    guard sampleCount > 0 else {
      throw EvaluationDomainError.nonPositiveSampleCount
    }
    return PerformanceClaim(
      context: context,
      measurement: measurement,
      provenance: EvidenceProvenance(
        immutableManifestSHA256: immutableManifestSHA256,
        evaluationRunID: evaluationRunID,
        algorithmVersion: algorithmVersion,
        sampleCount: sampleCount
      )
    )
  }

  private static func isLowercaseHexByte(_ byte: UInt8) -> Bool {
    (48...57).contains(byte) || (97...102).contains(byte)
  }
}

public enum EvaluationDomainError: CodedDomainError, Equatable {
  case emptyContextField(EvaluationContextField)
  case contextFieldTooLong(EvaluationContextField, maximumUTF8Bytes: Int)
  case contextFieldHasOuterWhitespace(EvaluationContextField)
  case contextFieldContainsUnsafeUnicode(EvaluationContextField)
  case contextFieldHasNoVisibleBase(EvaluationContextField)
  case invalidManifestSHA256
  case nonPositiveSampleCount
  case nonFiniteMeasurement
  case framesPerThousandOutsideRange
  case convergenceDurationOutsideRange
  case audioSynchronizationOffsetOutsideRange

  public var code: String {
    switch self {
    case .emptyContextField: "evaluation.context.empty"
    case .contextFieldTooLong: "evaluation.context.too_long"
    case .contextFieldHasOuterWhitespace: "evaluation.context.outer_whitespace"
    case .contextFieldContainsUnsafeUnicode: "evaluation.context.unsafe_unicode"
    case .contextFieldHasNoVisibleBase: "evaluation.context.no_visible_base"
    case .invalidManifestSHA256: "evaluation.provenance.manifest_sha256.invalid"
    case .nonPositiveSampleCount: "evaluation.provenance.sample_count_non_positive"
    case .nonFiniteMeasurement: "evaluation.measurement.non_finite"
    case .framesPerThousandOutsideRange: "evaluation.measurement.frames_per_thousand.outside_range"
    case .convergenceDurationOutsideRange:
      "evaluation.measurement.convergence_duration.outside_range"
    case .audioSynchronizationOffsetOutsideRange:
      "evaluation.measurement.audio_offset.outside_range"
    }
  }

  public var safeMessage: String {
    switch self {
    case .emptyContextField:
      "Every compatibility context field must contain a visible label."
    case .contextFieldTooLong:
      "A compatibility context label exceeds its UTF-8 size limit."
    case .contextFieldHasOuterWhitespace:
      "Compatibility context labels must not have outer whitespace."
    case .contextFieldContainsUnsafeUnicode:
      "A compatibility context label contains unsafe Unicode."
    case .contextFieldHasNoVisibleBase:
      "A compatibility context label must contain a visible base character."
    case .invalidManifestSHA256:
      "The evidence manifest digest must be lowercase SHA-256 hexadecimal."
    case .nonPositiveSampleCount:
      "Evidence must contain at least one sample."
    case .nonFiniteMeasurement:
      "Evaluation measurements must be finite."
    case .framesPerThousandOutsideRange:
      "Dropped frames per thousand must be between zero and one thousand."
    case .convergenceDurationOutsideRange:
      "Convergence duration is outside its conservative representation range."
    case .audioSynchronizationOffsetOutsideRange:
      "Audio synchronization offset is outside its conservative representation range."
    }
  }
}
