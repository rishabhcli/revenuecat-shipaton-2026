// swift-tools-version: 6.0

import PackageDescription

let strictSwiftSettings: [SwiftSetting] = [
  .unsafeFlags([
    "-warnings-as-errors",
    "-strict-concurrency=complete",
    "-warn-concurrency",
  ])
]

let package = Package(
  name: "CaptureInstrument",
  platforms: [
    .iOS(.v17),
    .macOS(.v14),
  ],
  products: [
    .library(
      name: "CaptureFoundation",
      targets: [
        "CaptureDomain",
        "RuntimeConfiguration",
        "CameraDomain",
        "AnalysisDomain",
        "MetalDomain",
        "PurchasesDomain",
        "ExportDomain",
        "EvaluationDomain",
        "UIDomain",
      ]
    )
  ],
  targets: [
    .target(
      name: "CaptureDomain",
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "RuntimeConfiguration",
      dependencies: ["CaptureDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "CameraDomain",
      dependencies: ["CaptureDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "AnalysisDomain",
      dependencies: ["CaptureDomain", "CameraDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "MetalDomain",
      dependencies: ["CaptureDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "PurchasesDomain",
      dependencies: ["CaptureDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "ExportDomain",
      dependencies: [
        "CaptureDomain",
        "MetalDomain",
        "PurchasesDomain",
      ],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "EvaluationDomain",
      dependencies: ["CaptureDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .target(
      name: "UIDomain",
      dependencies: ["CaptureDomain", "AnalysisDomain", "PurchasesDomain"],
      swiftSettings: strictSwiftSettings
    ),
    .testTarget(
      name: "FoundationPropertyTests",
      dependencies: [
        "CaptureDomain",
        "RuntimeConfiguration",
        "CameraDomain",
        "AnalysisDomain",
        "MetalDomain",
        "PurchasesDomain",
        "ExportDomain",
        "EvaluationDomain",
        "UIDomain",
      ],
      swiftSettings: strictSwiftSettings
    ),
  ],
  swiftLanguageModes: [.v6]
)
