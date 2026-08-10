public protocol CodedDomainError: Error, Sendable {
  /// Stable, non-sensitive identifier suitable for tests and operational events.
  var code: String { get }

  /// A fixed message that never interpolates caller-controlled text.
  var safeMessage: String { get }
}

public enum DomainValidationError: CodedDomainError, Equatable {
  case emptyIdentifier
  case identifierTooLong(maximumUTF8Bytes: Int)
  case invalidIdentifierCharacter
  case nonFiniteNumber
  case valueOutsideUnitInterval

  public var code: String {
    switch self {
    case .emptyIdentifier: "domain.identifier.empty"
    case .identifierTooLong: "domain.identifier.too_long"
    case .invalidIdentifierCharacter: "domain.identifier.invalid_character"
    case .nonFiniteNumber: "domain.number.non_finite"
    case .valueOutsideUnitInterval: "domain.number.outside_unit_interval"
    }
  }

  public var safeMessage: String {
    switch self {
    case .emptyIdentifier:
      "The identifier must not be empty."
    case .identifierTooLong(let maximumUTF8Bytes):
      "The identifier must contain at most \(maximumUTF8Bytes) UTF-8 bytes."
    case .invalidIdentifierCharacter:
      "The identifier contains a character outside its allowed alphabet."
    case .nonFiniteNumber:
      "The numeric value must be finite."
    case .valueOutsideUnitInterval:
      "The numeric value must be between zero and one, inclusive."
    }
  }
}

/// A bounded identifier for protocol, algorithm, and issuance identities.
public struct StableIdentifier: Hashable, Sendable, Comparable, CustomStringConvertible {
  public static let maximumUTF8Bytes = 96

  public let rawValue: String

  public init(_ rawValue: String) throws {
    guard !rawValue.isEmpty else {
      throw DomainValidationError.emptyIdentifier
    }
    guard rawValue.utf8.count <= Self.maximumUTF8Bytes else {
      throw DomainValidationError.identifierTooLong(
        maximumUTF8Bytes: Self.maximumUTF8Bytes
      )
    }
    guard rawValue.utf8.allSatisfy(Self.isAllowedASCIIByte) else {
      throw DomainValidationError.invalidIdentifierCharacter
    }

    self.rawValue = rawValue
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.rawValue < rhs.rawValue
  }

  public var description: String { rawValue }

  private static func isAllowedASCIIByte(_ byte: UInt8) -> Bool {
    switch byte {
    case 45, 46, 48...57, 65...90, 95, 97...122:
      true
    default:
      false
    }
  }
}

/// A finite value constrained to `[0, 1]`, used for normalized measurements.
public struct UnitInterval: Hashable, Sendable, Comparable {
  public let value: Double

  public init(_ value: Double) throws {
    guard value.isFinite else {
      throw DomainValidationError.nonFiniteNumber
    }
    guard (0...1).contains(value) else {
      throw DomainValidationError.valueOutsideUnitInterval
    }
    self.value = value
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.value < rhs.value
  }
}

public struct AlgorithmVersion: Hashable, Sendable, CustomStringConvertible {
  public let identifier: StableIdentifier

  public init(_ rawValue: String) throws {
    identifier = try StableIdentifier(rawValue)
  }

  public var description: String { identifier.rawValue }
}

public struct CorrelationID: Hashable, Sendable, CustomStringConvertible {
  public let identifier: StableIdentifier

  public init(_ rawValue: String) throws {
    identifier = try StableIdentifier(rawValue)
  }

  public var description: String { identifier.rawValue }
}
