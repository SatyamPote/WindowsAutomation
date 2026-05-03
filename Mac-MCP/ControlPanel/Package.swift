// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Lotus",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "Lotus",
            path: "Sources/Lotus"
        )
    ]
)
