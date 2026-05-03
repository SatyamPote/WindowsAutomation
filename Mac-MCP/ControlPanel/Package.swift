// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "Lotus",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "Lotus",
            path: "Sources/Lotus",
            resources: [
                .process("Resources/bot_service.py"),
                .process("Resources/pyproject.toml"),
                .process("Resources/uv.lock"),
                .copy("Resources/src"),
            ]
        )
    ]
)
