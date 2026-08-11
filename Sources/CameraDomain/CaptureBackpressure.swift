import CaptureDomain

/// The observed capture queue state at one admission point.
public struct CaptureLoad: Sendable, Equatable {
  /// Queue depths above this cannot occur in a real capture pipeline, so a
  /// larger value is a corrupted or unvalidated count and is refused here
  /// rather than propagated into admission arithmetic.
  public static let maximumQueueDepth = 1_000_000

  public let recordedFramesAwaiting: Int
  public let diagnosticJobsAwaiting: Int
  public let availableSlots: Int
  public let pressure: CapturePressure

  public init(
    recordedFramesAwaiting: Int,
    diagnosticJobsAwaiting: Int,
    availableSlots: Int,
    pressure: CapturePressure
  ) throws {
    guard recordedFramesAwaiting >= 0,
      diagnosticJobsAwaiting >= 0,
      availableSlots >= 0
    else {
      throw CameraDomainError.negativeQueueCount
    }
    guard recordedFramesAwaiting <= Self.maximumQueueDepth,
      diagnosticJobsAwaiting <= Self.maximumQueueDepth,
      availableSlots <= Self.maximumQueueDepth
    else {
      throw CameraDomainError.queueDepthAboveSupportedMaximum(
        maximum: Self.maximumQueueDepth
      )
    }
    self.recordedFramesAwaiting = recordedFramesAwaiting
    self.diagnosticJobsAwaiting = diagnosticJobsAwaiting
    self.availableSlots = availableSlots
    self.pressure = pressure
  }
}

/// One admission outcome.
///
/// Invariant I3: diagnostic work drops before recorded frames. Only
/// `CaptureAdmissionPolicy` can construct this type, and it refuses to
/// construct one that admits diagnostic work while a recorded frame is still
/// waiting, so that state is not representable downstream.
public struct CaptureAdmission: Sendable, Equatable {
  public let recordedFramesAdmitted: Int
  public let diagnosticJobsAdmitted: Int
  public let recordedFramesDeferred: Int
  public let diagnosticJobsDropped: Int
  public let pressure: CapturePressure

  fileprivate init(
    recordedFramesAdmitted: Int,
    diagnosticJobsAdmitted: Int,
    recordedFramesDeferred: Int,
    diagnosticJobsDropped: Int,
    pressure: CapturePressure
  ) {
    self.recordedFramesAdmitted = recordedFramesAdmitted
    self.diagnosticJobsAdmitted = diagnosticJobsAdmitted
    self.recordedFramesDeferred = recordedFramesDeferred
    self.diagnosticJobsDropped = diagnosticJobsDropped
    self.pressure = pressure
  }

  /// True when a recorded frame waited while diagnostic work ran, which is the
  /// exact condition invariant I3 forbids.
  public var starvesRecordedFrames: Bool {
    recordedFramesDeferred > 0 && diagnosticJobsAdmitted > 0
  }
}

/// An admission decision together with the telemetry that records it.
public struct CaptureAdmissionDecision: Sendable, Equatable {
  public let admission: CaptureAdmission
  public let events: [OperationalEvent]

  fileprivate init(admission: CaptureAdmission, events: [OperationalEvent]) {
    self.admission = admission
    self.events = events
  }
}

public enum CaptureAdmissionPolicy {
  public static func decide(for load: CaptureLoad) -> CaptureAdmissionDecision {
    let recordedAdmitted = min(load.recordedFramesAwaiting, load.availableSlots)
    let remainingSlots = load.availableSlots - recordedAdmitted
    // Under any non-nominal pressure diagnostics take no capacity at all, so the
    // remaining margin stays available to the recorder rather than being shared
    // with work that can be redone on the next frame.
    let diagnosticsAdmitted =
      load.pressure == .nominal ? min(load.diagnosticJobsAwaiting, remainingSlots) : 0

    let admission = CaptureAdmission(
      recordedFramesAdmitted: recordedAdmitted,
      diagnosticJobsAdmitted: diagnosticsAdmitted,
      recordedFramesDeferred: load.recordedFramesAwaiting - recordedAdmitted,
      diagnosticJobsDropped: load.diagnosticJobsAwaiting - diagnosticsAdmitted,
      pressure: load.pressure
    )

    guard postconditionHolds(admission, for: load) else {
      // Fail closed: admit the recorded frames capacity allows and no
      // diagnostic work at all, then report that the two paths disagreed.
      let safeAdmission = CaptureAdmission(
        recordedFramesAdmitted: recordedAdmitted,
        diagnosticJobsAdmitted: 0,
        recordedFramesDeferred: load.recordedFramesAwaiting - recordedAdmitted,
        diagnosticJobsDropped: load.diagnosticJobsAwaiting,
        pressure: load.pressure
      )
      return CaptureAdmissionDecision(
        admission: safeAdmission,
        events: [
          .invariantViolated(
            InvariantViolationEvent(
              invariant: .diagnosticsDropBeforeRecordedFrames,
              guardIdentifier: .captureAdmissionPostcondition
            )
          ),
          event(for: safeAdmission),
        ]
      )
    }
    return CaptureAdmissionDecision(admission: admission, events: [event(for: admission)])
  }

  /// Independent re-derivation of every property an admission must have.
  ///
  /// Deliberately not factored out of `decide`, so that a change to the
  /// admission arithmetic cannot silently change its own guard.
  package static func postconditionHolds(
    _ admission: CaptureAdmission,
    for load: CaptureLoad
  ) -> Bool {
    guard !admission.starvesRecordedFrames else { return false }
    guard admission.recordedFramesAdmitted >= 0,
      admission.diagnosticJobsAdmitted >= 0,
      admission.recordedFramesDeferred >= 0,
      admission.diagnosticJobsDropped >= 0
    else {
      return false
    }
    guard
      admission.recordedFramesAdmitted + admission.recordedFramesDeferred
        == load.recordedFramesAwaiting,
      admission.diagnosticJobsAdmitted + admission.diagnosticJobsDropped
        == load.diagnosticJobsAwaiting
    else {
      return false
    }
    guard
      admission.recordedFramesAdmitted + admission.diagnosticJobsAdmitted
        <= load.availableSlots
    else {
      return false
    }
    guard admission.recordedFramesAdmitted == min(load.recordedFramesAwaiting, load.availableSlots)
    else {
      return false
    }
    guard load.pressure == .nominal || admission.diagnosticJobsAdmitted == 0 else {
      return false
    }
    return admission.pressure == load.pressure
  }

  private static func event(for admission: CaptureAdmission) -> OperationalEvent {
    .captureAdmissionDecided(
      CaptureAdmissionEvent(
        pressure: admission.pressure,
        recordedFramesAdmitted: admission.recordedFramesAdmitted,
        recordedFramesDeferred: admission.recordedFramesDeferred,
        diagnosticJobsAdmitted: admission.diagnosticJobsAdmitted,
        diagnosticJobsDropped: admission.diagnosticJobsDropped
      )
    )
  }
}
