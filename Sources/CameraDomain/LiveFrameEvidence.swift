import CaptureDomain

public struct CaptureSourceID: Hashable, Sendable, CustomStringConvertible {
  public let identifier: StableIdentifier

  public init(_ rawValue: String) throws {
    identifier = try StableIdentifier(rawValue)
  }

  public var description: String { identifier.rawValue }
}

/// Opaque identity issued when a package-owned camera adapter starts a live session.
public struct CaptureSessionID: Hashable, Sendable, CustomStringConvertible {
  public let adapterID: StableIdentifier
  public let sessionReference: StableIdentifier

  fileprivate init(
    adapterID: StableIdentifier,
    sessionReference: StableIdentifier
  ) {
    self.adapterID = adapterID
    self.sessionReference = sessionReference
  }

  public var description: String {
    "\(adapterID.rawValue.utf8.count):\(adapterID.rawValue)"
      + "\(sessionReference.rawValue.utf8.count):\(sessionReference.rawValue)"
  }
}

/// A provenance reference produced only by `LiveCaptureIssuer`.
public struct LiveFrameReference: Hashable, Sendable {
  public let sessionID: CaptureSessionID
  public let sourceID: CaptureSourceID
  public let sequenceNumber: UInt64
  public let monotonicTimestampNanoseconds: UInt64

  fileprivate init(
    sessionID: CaptureSessionID,
    sourceID: CaptureSourceID,
    sequenceNumber: UInt64,
    monotonicTimestampNanoseconds: UInt64
  ) {
    self.sessionID = sessionID
    self.sourceID = sourceID
    self.sequenceNumber = sequenceNumber
    self.monotonicTimestampNanoseconds = monotonicTimestampNanoseconds
  }
}

/// Issuance capability reserved for package-owned camera adapters and package tests.
/// Sequence numbers are generated here and timestamps must increase at issuance.
package struct LiveCaptureIssuer: Sendable {
  package let sessionID: CaptureSessionID
  package let sourceID: CaptureSourceID

  private var nextSequenceNumber: UInt64?
  private var lastTimestampNanoseconds: UInt64?

  package init(
    adapterID: String,
    sessionReference: String,
    sourceID: CaptureSourceID,
    initialSequenceNumber: UInt64 = 0
  ) throws {
    sessionID = CaptureSessionID(
      adapterID: try StableIdentifier(adapterID),
      sessionReference: try StableIdentifier(sessionReference)
    )
    self.sourceID = sourceID
    nextSequenceNumber = initialSequenceNumber
    lastTimestampNanoseconds = nil
  }

  package mutating func issueFrame(
    monotonicTimestampNanoseconds: UInt64
  ) throws -> LiveFrameReference {
    if let lastTimestampNanoseconds,
      monotonicTimestampNanoseconds <= lastTimestampNanoseconds
    {
      throw CameraDomainError.nonIncreasingIssuedTimestamp
    }
    guard let sequenceNumber = nextSequenceNumber else {
      throw CameraDomainError.sequenceNumberExhausted
    }

    let (followingSequence, overflow) = sequenceNumber.addingReportingOverflow(1)
    nextSequenceNumber = overflow ? nil : followingSequence
    lastTimestampNanoseconds = monotonicTimestampNanoseconds

    return LiveFrameReference(
      sessionID: sessionID,
      sourceID: sourceID,
      sequenceNumber: sequenceNumber,
      monotonicTimestampNanoseconds: monotonicTimestampNanoseconds
    )
  }
}

public struct LiveFrameWindow: Sendable, Equatable {
  public static let maximumFrameCount = 240

  public let sessionID: CaptureSessionID
  public let sourceID: CaptureSourceID
  public let frames: [LiveFrameReference]

  public init(frames: [LiveFrameReference]) throws {
    guard let first = frames.first else {
      throw CameraDomainError.emptyFrameWindow
    }
    guard frames.count <= Self.maximumFrameCount else {
      throw CameraDomainError.frameWindowTooLarge(maximum: Self.maximumFrameCount)
    }
    guard frames.allSatisfy({ $0.sessionID == first.sessionID }) else {
      throw CameraDomainError.mixedCaptureSessions
    }
    guard frames.allSatisfy({ $0.sourceID == first.sourceID }) else {
      throw CameraDomainError.mixedCaptureSources
    }

    for pair in zip(frames, frames.dropFirst()) {
      guard pair.0.sequenceNumber < pair.1.sequenceNumber else {
        throw CameraDomainError.nonIncreasingSequence
      }
      guard pair.0.monotonicTimestampNanoseconds < pair.1.monotonicTimestampNanoseconds else {
        throw CameraDomainError.nonIncreasingTimestamp
      }
    }

    sessionID = first.sessionID
    sourceID = first.sourceID
    self.frames = frames
  }
}

/// Bounded admission policy that protects recorded frames before diagnostics.
public struct CaptureLoad: Sendable, Equatable {
  public let recordedFramesAwaiting: Int
  public let diagnosticJobsAwaiting: Int
  public let availableSlots: Int

  public init(
    recordedFramesAwaiting: Int,
    diagnosticJobsAwaiting: Int,
    availableSlots: Int
  ) throws {
    guard recordedFramesAwaiting >= 0,
      diagnosticJobsAwaiting >= 0,
      availableSlots >= 0
    else {
      throw CameraDomainError.negativeQueueCount
    }
    self.recordedFramesAwaiting = recordedFramesAwaiting
    self.diagnosticJobsAwaiting = diagnosticJobsAwaiting
    self.availableSlots = availableSlots
  }
}

public struct CaptureAdmission: Sendable, Equatable {
  public let recordedFramesAdmitted: Int
  public let diagnosticJobsAdmitted: Int
  public let recordedFramesDeferred: Int
  public let diagnosticJobsDropped: Int
}

public enum CaptureAdmissionPolicy {
  public static func decide(for load: CaptureLoad) -> CaptureAdmission {
    let recordedAdmitted = min(load.recordedFramesAwaiting, load.availableSlots)
    let remainingSlots = load.availableSlots - recordedAdmitted
    let diagnosticsAdmitted = min(load.diagnosticJobsAwaiting, remainingSlots)

    return CaptureAdmission(
      recordedFramesAdmitted: recordedAdmitted,
      diagnosticJobsAdmitted: diagnosticsAdmitted,
      recordedFramesDeferred: load.recordedFramesAwaiting - recordedAdmitted,
      diagnosticJobsDropped: load.diagnosticJobsAwaiting - diagnosticsAdmitted
    )
  }
}

public enum CameraDomainError: CodedDomainError, Equatable {
  case emptyFrameWindow
  case frameWindowTooLarge(maximum: Int)
  case mixedCaptureSessions
  case mixedCaptureSources
  case nonIncreasingSequence
  case nonIncreasingTimestamp
  case nonIncreasingIssuedTimestamp
  case sequenceNumberExhausted
  case negativeQueueCount

  public var code: String {
    switch self {
    case .emptyFrameWindow: "camera.frame_window.empty"
    case .frameWindowTooLarge: "camera.frame_window.too_large"
    case .mixedCaptureSessions: "camera.frame_window.mixed_sessions"
    case .mixedCaptureSources: "camera.frame_window.mixed_sources"
    case .nonIncreasingSequence: "camera.frame_window.sequence_not_increasing"
    case .nonIncreasingTimestamp: "camera.frame_window.timestamp_not_increasing"
    case .nonIncreasingIssuedTimestamp: "camera.frame_issuer.timestamp_not_increasing"
    case .sequenceNumberExhausted: "camera.frame_issuer.sequence_exhausted"
    case .negativeQueueCount: "camera.capture_load.negative_count"
    }
  }

  public var safeMessage: String {
    switch self {
    case .emptyFrameWindow:
      "At least one issued live frame is required."
    case .frameWindowTooLarge(let maximum):
      "A live frame window may contain at most \(maximum) frames."
    case .mixedCaptureSessions:
      "All live frames in a window must come from one capture session."
    case .mixedCaptureSources:
      "All live frames in a window must come from one capture source."
    case .nonIncreasingSequence:
      "Live frame sequence numbers must increase."
    case .nonIncreasingTimestamp:
      "Live frame timestamps must increase monotonically."
    case .nonIncreasingIssuedTimestamp:
      "A camera adapter attempted to issue an out-of-order frame timestamp."
    case .sequenceNumberExhausted:
      "The live capture sequence-number space is exhausted."
    case .negativeQueueCount:
      "Capture queue counts must not be negative."
    }
  }
}
