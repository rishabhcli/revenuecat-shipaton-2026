import CaptureDomain

public enum RepositoryService: String, CaseIterable, Sendable, Hashable {
  case evaluationDashboard = "evaluation-dashboard"
  case revenueCatWebhookReceiver = "revenuecat-sandbox-webhook-receiver"
  case testPatternServer = "test-pattern-server"
  case buildArtifactServer = "build-artifact-server"

  public var environmentKey: String {
    switch self {
    case .evaluationDashboard: "PORT_0"
    case .revenueCatWebhookReceiver: "PORT_1"
    case .testPatternServer: "PORT_2"
    case .buildArtifactServer: "PORT_3"
    }
  }

  public var canonicalPort: TCPPort {
    switch self {
    case .evaluationDashboard: TCPPort(validatedRawValue: 4_220)
    case .revenueCatWebhookReceiver: TCPPort(validatedRawValue: 4_221)
    case .testPatternServer: TCPPort(validatedRawValue: 4_222)
    case .buildArtifactServer: TCPPort(validatedRawValue: 4_223)
    }
  }

  public var stableIdentity: ServiceIdentity {
    ServiceIdentity(service: self)
  }
}

/// Repository service identities are closed over `RepositoryService`; arbitrary
/// strings cannot masquerade as a service identity.
public struct ServiceIdentity: Hashable, Sendable, CustomStringConvertible {
  public let service: RepositoryService

  fileprivate init(service: RepositoryService) {
    self.service = service
  }

  public var rawValue: String {
    "\(RepositoryRuntimeConfiguration.repositoryNamespace).\(service.rawValue)"
  }

  public var description: String { rawValue }
}

public struct TCPPort: Hashable, Sendable, Comparable, CustomStringConvertible {
  public let rawValue: UInt16

  public init(_ integer: Int) throws {
    guard (1...Int(UInt16.max)).contains(integer) else {
      throw ConfigurationError.invalidTCPPort
    }
    rawValue = UInt16(integer)
  }

  fileprivate init(validatedRawValue: UInt16) {
    rawValue = validatedRawValue
  }

  public static func < (lhs: Self, rhs: Self) -> Bool {
    lhs.rawValue < rhs.rawValue
  }

  public var description: String { String(rawValue) }
}

public struct PortBlock: Hashable, Sendable {
  public let lowerBound: TCPPort
  public let upperBound: TCPPort

  public init(lowerBound: TCPPort, upperBound: TCPPort) throws {
    guard lowerBound <= upperBound else {
      throw ConfigurationError.reversedPortBlock
    }
    self.lowerBound = lowerBound
    self.upperBound = upperBound
  }

  fileprivate init(validatedLowerBound: TCPPort, upperBound: TCPPort) {
    lowerBound = validatedLowerBound
    self.upperBound = upperBound
  }

  public func contains(_ port: TCPPort) -> Bool {
    lowerBound <= port && port <= upperBound
  }
}

public enum LoopbackHost: String, Sendable, Hashable {
  case ipv4 = "127.0.0.1"
}

public struct ServiceEndpoint: Sendable, Hashable {
  public let service: RepositoryService
  public let stableIdentity: ServiceIdentity
  public let host: LoopbackHost
  public let port: TCPPort

  fileprivate init(service: RepositoryService, host: LoopbackHost, port: TCPPort) {
    self.service = service
    stableIdentity = service.stableIdentity
    self.host = host
    self.port = port
  }
}

public struct RepositoryRuntimeConfiguration: Sendable, Equatable {
  public static let repositoryNamespace = "revenuecat-shipaton-2026"
  public static let canonicalPortBlock = PortBlock(
    validatedLowerBound: TCPPort(validatedRawValue: 4_220),
    upperBound: TCPPort(validatedRawValue: 4_229)
  )

  public let host: LoopbackHost
  public let endpoints: [ServiceEndpoint]

  public init(environment: [String: String]) throws {
    let knownPortKeys = Set(RepositoryService.allCases.map(\.environmentKey))
    guard
      !environment.keys.contains(where: {
        $0.hasPrefix("PORT_") && !knownPortKeys.contains($0)
      })
    else {
      throw ConfigurationError.unknownPortKey
    }

    if let suppliedNamespace = environment["SERVICE_NAMESPACE"],
      suppliedNamespace != Self.repositoryNamespace
    {
      throw ConfigurationError.invalidServiceNamespace
    }

    if let suppliedHost = environment["BIND_HOST"], suppliedHost != LoopbackHost.ipv4.rawValue {
      throw ConfigurationError.nonLoopbackHost
    }

    host = .ipv4
    var parsedEndpoints: [ServiceEndpoint] = []
    parsedEndpoints.reserveCapacity(RepositoryService.allCases.count)

    for service in RepositoryService.allCases {
      guard let rawPort = environment[service.environmentKey] else {
        throw ConfigurationError.missingValue(service)
      }
      guard let integer = Int(rawPort),
        let port = try? TCPPort(integer)
      else {
        throw ConfigurationError.invalidServicePort(service)
      }
      guard Self.canonicalPortBlock.contains(port) else {
        throw ConfigurationError.portOutsideExclusiveBlock(service)
      }
      guard port == service.canonicalPort else {
        throw ConfigurationError.unexpectedServicePort(
          service: service,
          expected: service.canonicalPort,
          actual: port
        )
      }
      parsedEndpoints.append(ServiceEndpoint(service: service, host: host, port: port))
    }

    endpoints = parsedEndpoints
  }

  public init(portsEnvironmentContents: String) throws {
    try self.init(environment: PortsEnvironmentParser.parse(portsEnvironmentContents))
  }

  public func endpoint(for service: RepositoryService) -> ServiceEndpoint {
    // The closed service enum and successful construction guarantee one endpoint
    // in declaration order for every supported service.
    endpoints[service.index]
  }
}

extension RepositoryService {
  fileprivate var index: Int {
    switch self {
    case .evaluationDashboard: 0
    case .revenueCatWebhookReceiver: 1
    case .testPatternServer: 2
    case .buildArtifactServer: 3
    }
  }
}

public enum ConfigurationError: CodedDomainError, Equatable {
  case inputTooLarge(maximumUTF8Bytes: Int)
  case tooManyLines(maximum: Int)
  case malformedAssignment(line: Int)
  case invalidKey(line: Int)
  case duplicateKey
  case unknownPortKey
  case missingValue(RepositoryService)
  case invalidTCPPort
  case invalidServicePort(RepositoryService)
  case portOutsideExclusiveBlock(RepositoryService)
  case unexpectedServicePort(
    service: RepositoryService,
    expected: TCPPort,
    actual: TCPPort
  )
  case reversedPortBlock
  case nonLoopbackHost
  case invalidServiceNamespace

  public var code: String {
    switch self {
    case .inputTooLarge: "configuration.input.too_large"
    case .tooManyLines: "configuration.input.too_many_lines"
    case .malformedAssignment: "configuration.assignment.malformed"
    case .invalidKey: "configuration.key.invalid"
    case .duplicateKey: "configuration.key.duplicate"
    case .unknownPortKey: "configuration.port_key.unknown"
    case .missingValue: "configuration.value.missing"
    case .invalidTCPPort: "configuration.tcp_port.invalid"
    case .invalidServicePort: "configuration.service_port.invalid"
    case .portOutsideExclusiveBlock: "configuration.port.outside_block"
    case .unexpectedServicePort: "configuration.port.unexpected_for_service"
    case .reversedPortBlock: "configuration.port_block.reversed"
    case .nonLoopbackHost: "configuration.host.not_loopback"
    case .invalidServiceNamespace: "configuration.namespace.invalid"
    }
  }

  public var safeMessage: String {
    switch self {
    case .inputTooLarge:
      "Configuration exceeds its UTF-8 size limit."
    case .tooManyLines:
      "Configuration exceeds its line-count limit."
    case .malformedAssignment:
      "A configuration line is not a key-value assignment."
    case .invalidKey:
      "A configuration line has an invalid key."
    case .duplicateKey:
      "A configuration key is declared more than once."
    case .unknownPortKey:
      "A port key does not identify a declared repository service."
    case .missingValue:
      "A required repository service port is missing."
    case .invalidTCPPort, .invalidServicePort:
      "A configured value is not a valid TCP port."
    case .portOutsideExclusiveBlock:
      "A service port is outside this repository's exclusive port block."
    case .unexpectedServicePort:
      "A repository service is not using its canonical port."
    case .reversedPortBlock:
      "The port block lower bound must not exceed its upper bound."
    case .nonLoopbackHost:
      "Repository services must bind to the IPv4 loopback host."
    case .invalidServiceNamespace:
      "The service namespace must match this repository."
    }
  }
}

enum PortsEnvironmentParser {
  static let maximumUTF8Bytes = 16_384
  static let maximumLines = 128

  static func parse(_ contents: String) throws -> [String: String] {
    guard contents.utf8.count <= maximumUTF8Bytes else {
      throw ConfigurationError.inputTooLarge(maximumUTF8Bytes: maximumUTF8Bytes)
    }

    let lines = contents.split(separator: "\n", omittingEmptySubsequences: false)
    guard lines.count <= maximumLines else {
      throw ConfigurationError.tooManyLines(maximum: maximumLines)
    }

    var result: [String: String] = [:]
    result.reserveCapacity(lines.count)

    for (zeroBasedIndex, rawLine) in lines.enumerated() {
      let lineNumber = zeroBasedIndex + 1
      let withoutComment = rawLine.prefix { $0 != "#" }
      let line = trimASCIIWhitespace(withoutComment)
      guard !line.isEmpty else { continue }
      guard let equalsIndex = line.firstIndex(of: "=") else {
        throw ConfigurationError.malformedAssignment(line: lineNumber)
      }

      let key = trimASCIIWhitespace(line[..<equalsIndex])
      let value = trimASCIIWhitespace(line[line.index(after: equalsIndex)...])
      guard isValidKey(key) else {
        throw ConfigurationError.invalidKey(line: lineNumber)
      }

      let keyString = String(key)
      guard result[keyString] == nil else {
        throw ConfigurationError.duplicateKey
      }
      result[keyString] = String(value)
    }

    return result
  }

  private static func trimASCIIWhitespace(_ value: Substring) -> Substring {
    var lowerBound = value.startIndex
    var upperBound = value.endIndex

    while lowerBound < upperBound, isASCIIWhitespace(value[lowerBound]) {
      lowerBound = value.index(after: lowerBound)
    }
    while lowerBound < upperBound {
      let previous = value.index(before: upperBound)
      guard isASCIIWhitespace(value[previous]) else { break }
      upperBound = previous
    }
    return value[lowerBound..<upperBound]
  }

  private static func isASCIIWhitespace(_ character: Character) -> Bool {
    character == " " || character == "\t" || character == "\r"
  }

  private static func isValidKey(_ key: Substring) -> Bool {
    guard let first = key.utf8.first, isUppercaseASCII(first) || first == 95 else {
      return false
    }
    return key.utf8.dropFirst().allSatisfy {
      isUppercaseASCII($0) || (48...57).contains($0) || $0 == 95
    }
  }

  private static func isUppercaseASCII(_ byte: UInt8) -> Bool {
    (65...90).contains(byte)
  }
}
