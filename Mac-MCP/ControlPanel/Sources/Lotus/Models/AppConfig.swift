import Foundation

struct AppConfig: Codable, Sendable {
    var name: String
    var telegram_token: String
    var allowed_user_id: String
    var model_name: String
    var created_at: String

    // MARK: - Paths

    /// Mac-MCP project root — found by walking up from the executable
    /// until a directory containing bot_service.py is reached.
    static let baseDir: URL = {
        let fm = FileManager.default
        var dir = URL(fileURLWithPath: CommandLine.arguments[0])
            .resolvingSymlinksInPath()
            .deletingLastPathComponent()

        for _ in 0..<10 {
            if fm.fileExists(atPath: dir.appendingPathComponent("bot_service.py").path) {
                return dir
            }
            let parent = dir.deletingLastPathComponent()
            if parent.path == dir.path { break }
            dir = parent
        }

        // Fallback: stored preference (set by SwiftUI setup wizard in Phase 3)
        if let stored = UserDefaults.standard.string(forKey: "com.lotus.basedir") {
            return URL(fileURLWithPath: stored)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }()

    static var configURL: URL {
        baseDir.appendingPathComponent("config.json")
    }

    static var appDataDir: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Lotus")
    }

    static var controlPortFile: URL {
        appDataDir.appendingPathComponent("control.port")
    }

    static var pidFile: URL {
        appDataDir.appendingPathComponent("lotus_bot.pid")
    }

    static var botLogFile: URL {
        appDataDir.appendingPathComponent("logs/bot_service.log")
    }

    static var launchAgentPlist: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/LaunchAgents/com.lotus.botservice.plist")
    }

    // MARK: - Persistence

    static func load() -> AppConfig? {
        guard let data = try? Data(contentsOf: configURL) else { return nil }
        return try? JSONDecoder().decode(AppConfig.self, from: data)
    }

    func save() throws {
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted]
        let data = try enc.encode(self)
        try data.write(to: AppConfig.configURL, options: .atomic)
    }

    func delete() throws {
        try FileManager.default.removeItem(at: AppConfig.configURL)
    }
}
