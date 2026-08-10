/// Opaque identity for one captured media artifact. Its initializer is not public;
/// only package-owned capture/application adapters can issue it.
public struct MediaArtifactID: Hashable, Sendable, CustomStringConvertible {
  public let issuerID: StableIdentifier
  public let artifactReference: StableIdentifier

  fileprivate init(
    issuerID: StableIdentifier,
    artifactReference: StableIdentifier
  ) {
    self.issuerID = issuerID
    self.artifactReference = artifactReference
  }

  /// Length prefixes keep the display serialization unambiguous even when both
  /// independently bounded components contain periods.
  public var description: String {
    "\(issuerID.rawValue.utf8.count):\(issuerID.rawValue)"
      + "\(artifactReference.rawValue.utf8.count):\(artifactReference.rawValue)"
  }
}

/// Capability reserved for package-owned capture/application adapters.
package struct MediaArtifactIssuer: Sendable {
  private let issuerID: StableIdentifier

  package init(issuerID: String) throws {
    self.issuerID = try StableIdentifier(issuerID)
  }

  package func issue(artifactReference: String) throws -> MediaArtifactID {
    let reference = try StableIdentifier(artifactReference)
    return MediaArtifactID(
      issuerID: issuerID,
      artifactReference: reference
    )
  }
}
