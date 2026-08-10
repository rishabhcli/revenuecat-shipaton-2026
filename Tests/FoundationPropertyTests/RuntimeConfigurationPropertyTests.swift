import RuntimeConfiguration
import XCTest

final class RuntimeConfigurationPropertyTests: XCTestCase {
  private static let validEntries: [(String, String)] = [
    ("PORT_0", "4220"),
    ("PORT_1", "4221"),
    ("PORT_2", "4222"),
    ("PORT_3", "4223"),
    ("BIND_HOST", "127.0.0.1"),
    ("SERVICE_NAMESPACE", "revenuecat-shipaton-2026"),
  ]

  func testCanonicalEnvironmentAcceptsAllInsertionOrders_720DistinctPermutations() throws {
    let permutations = allPermutations(Self.validEntries)
    XCTAssertEqual(permutations.count, 720)
    XCTAssertEqual(
      Set(permutations.map { $0.map(\.0).joined(separator: "|") }).count,
      720
    )

    var evaluatedPermutations = 0
    for entries in permutations {
      let configuration = try RepositoryRuntimeConfiguration(
        environment: Dictionary(uniqueKeysWithValues: entries)
      )

      XCTAssertEqual(configuration.host, .ipv4)
      XCTAssertEqual(configuration.endpoints.count, 4)
      for service in RepositoryService.allCases {
        let endpoint = configuration.endpoint(for: service)
        XCTAssertEqual(endpoint.service, service)
        XCTAssertEqual(endpoint.port, service.canonicalPort)
        XCTAssertEqual(endpoint.host, .ipv4)
        XCTAssertEqual(endpoint.stableIdentity, service.stableIdentity)
        XCTAssertEqual(
          endpoint.stableIdentity.rawValue,
          "revenuecat-shipaton-2026.\(service.rawValue)"
        )
      }
      evaluatedPermutations += 1
    }

    XCTAssertEqual(evaluatedPermutations, 720)
  }

  func testEveryServiceRefusesOutOfBlockPorts_1_024DistinctConfigurations() {
    var evaluatedConfigurations = 0

    for service in RepositoryService.allCases {
      for invalidPort in 1...256 {
        var environment = Dictionary(uniqueKeysWithValues: Self.validEntries)
        environment[service.environmentKey] = String(invalidPort)

        assertThrowsEqual(
          ConfigurationError.portOutsideExclusiveBlock(service),
          try RepositoryRuntimeConfiguration(environment: environment)
        )
        evaluatedConfigurations += 1
      }
    }

    XCTAssertEqual(evaluatedConfigurations, 1_024)
  }

  func testEveryMissingInvalidAndUnexpectedServicePortRefusesExactly() throws {
    for service in RepositoryService.allCases {
      var missing = Dictionary(uniqueKeysWithValues: Self.validEntries)
      missing.removeValue(forKey: service.environmentKey)
      assertThrowsEqual(
        ConfigurationError.missingValue(service),
        try RepositoryRuntimeConfiguration(environment: missing)
      )

      var invalid = Dictionary(uniqueKeysWithValues: Self.validEntries)
      invalid[service.environmentKey] = "not-a-port"
      assertThrowsEqual(
        ConfigurationError.invalidServicePort(service),
        try RepositoryRuntimeConfiguration(environment: invalid)
      )

      var unexpected = Dictionary(uniqueKeysWithValues: Self.validEntries)
      unexpected[service.environmentKey] = "4229"
      assertThrowsEqual(
        ConfigurationError.unexpectedServicePort(
          service: service,
          expected: service.canonicalPort,
          actual: try TCPPort(4_229)
        ),
        try RepositoryRuntimeConfiguration(environment: unexpected)
      )
    }
  }

  func testHostNamespaceAndUnknownPortKeysFailClosedExactly() {
    var environment = Dictionary(uniqueKeysWithValues: Self.validEntries)
    environment["BIND_HOST"] = "0.0.0.0"
    assertThrowsEqual(
      ConfigurationError.nonLoopbackHost,
      try RepositoryRuntimeConfiguration(environment: environment)
    )

    environment = Dictionary(uniqueKeysWithValues: Self.validEntries)
    environment["SERVICE_NAMESPACE"] = "another-repository"
    assertThrowsEqual(
      ConfigurationError.invalidServiceNamespace,
      try RepositoryRuntimeConfiguration(environment: environment)
    )

    environment = Dictionary(uniqueKeysWithValues: Self.validEntries)
    environment["PORT_SECRET"] = "4224"
    assertThrowsEqual(
      ConfigurationError.unknownPortKey,
      try RepositoryRuntimeConfiguration(environment: environment)
    )
  }

  func testPortsEnvironmentFileSyntaxParsesInlineComments() throws {
    let contents = """
      # revenuecat-shipaton-2026 — exclusive block 4220-4229
      PORT_0=4220   # Evaluation dashboard
      PORT_1=4221   # RevenueCat sandbox webhook receiver
      PORT_2=4222   # Test-pattern server
      PORT_3=4223   # Build/artifact server
      """

    let configuration = try RepositoryRuntimeConfiguration(
      portsEnvironmentContents: contents
    )

    XCTAssertEqual(
      configuration.endpoint(for: .buildArtifactServer).port.rawValue,
      4_223
    )
  }

  func testParserRefusesEveryDeclaredBoundaryWithExactErrors() {
    assertThrowsEqual(
      ConfigurationError.duplicateKey,
      try RepositoryRuntimeConfiguration(
        portsEnvironmentContents: "PORT_0=4220\nPORT_0=4220\n"
      )
    )
    assertThrowsEqual(
      ConfigurationError.inputTooLarge(maximumUTF8Bytes: 16_384),
      try RepositoryRuntimeConfiguration(
        portsEnvironmentContents: String(repeating: "X", count: 16_385)
      )
    )
    assertThrowsEqual(
      ConfigurationError.tooManyLines(maximum: 128),
      try RepositoryRuntimeConfiguration(
        portsEnvironmentContents: Array(repeating: "#", count: 129).joined(separator: "\n")
      )
    )
    assertThrowsEqual(
      ConfigurationError.malformedAssignment(line: 1),
      try RepositoryRuntimeConfiguration(portsEnvironmentContents: "PORT_0")
    )
    assertThrowsEqual(
      ConfigurationError.invalidKey(line: 1),
      try RepositoryRuntimeConfiguration(portsEnvironmentContents: "port_0=4220")
    )
  }

  func testTCPPortAndPortBlockNumericBoundariesRefuseExactly() throws {
    for invalid in [Int.min, -1, 0, Int(UInt16.max) + 1, Int.max] {
      assertThrowsEqual(
        ConfigurationError.invalidTCPPort,
        try TCPPort(invalid)
      )
    }
    XCTAssertEqual(try TCPPort(1).rawValue, 1)
    XCTAssertEqual(try TCPPort(Int(UInt16.max)).rawValue, UInt16.max)

    assertThrowsEqual(
      ConfigurationError.reversedPortBlock,
      try PortBlock(lowerBound: TCPPort(4_229), upperBound: TCPPort(4_220))
    )
  }

  func testServiceIdentitiesAreTypedUniqueAndRepositoryScoped() throws {
    let configuration = try RepositoryRuntimeConfiguration(
      environment: Dictionary(uniqueKeysWithValues: Self.validEntries)
    )
    let identities = configuration.endpoints.map(\.stableIdentity)

    XCTAssertEqual(Set(identities).count, RepositoryService.allCases.count)
    XCTAssertTrue(
      identities.allSatisfy {
        $0.rawValue.hasPrefix("revenuecat-shipaton-2026.")
      }
    )
  }

  func testConfigurationErrorsNeverEchoCallerControlledText() {
    let callerText = "SECRET-user-supplied-value"
    let errors: [ConfigurationError] = [
      .duplicateKey,
      .unknownPortKey,
      .invalidServicePort(.evaluationDashboard),
      .portOutsideExclusiveBlock(.evaluationDashboard),
      .nonLoopbackHost,
      .invalidServiceNamespace,
    ]

    XCTAssertTrue(errors.allSatisfy { !$0.safeMessage.contains(callerText) })
  }

  func testConfigurationTypesAreSendable() {
    requireSendable(RepositoryRuntimeConfiguration.self)
    requireSendable(ServiceEndpoint.self)
    requireSendable(ServiceIdentity.self)
    requireSendable(ConfigurationError.self)
  }
}
