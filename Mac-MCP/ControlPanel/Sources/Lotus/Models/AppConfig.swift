import Foundation

struct AppConfig: Codable, Sendable {
    var name: String
    var telegram_token: String
    var allowed_user_id: String
    var model_name: String
    var created_at: String

    // MARK: - Paths

    /// bot_service.py bundled inside the app; dev walk-up as fallback.
    static var botScriptURL: URL {
        if let url = Bundle.module.url(forResource: "bot_service", withExtension: "py") {
            return url
        }
        return _devBaseDir.appendingPathComponent("bot_service.py")
    }

    /// Directory that contains bot_service.py — used as working directory for uv.
    static var botScriptDir: URL {
        botScriptURL.deletingLastPathComponent()
    }

    /// Assets directory for logo images.
    static var assetsDir: URL? {
        // Bundle (when app is packaged)
        if let res = Bundle.module.resourceURL {
            let dir = res.appendingPathComponent("assets")
            if FileManager.default.fileExists(atPath: dir.path) { return dir }
        }
        // Dev fallback
        let dir = _devBaseDir.appendingPathComponent("assets")
        return FileManager.default.fileExists(atPath: dir.path) ? dir : nil
    }

    /// Development fallback: walk up from the executable until bot_service.py is found.
    static let _devBaseDir: URL = {
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
        if let stored = UserDefaults.standard.string(forKey: "com.lotus.basedir") {
            return URL(fileURLWithPath: stored)
        }
        return URL(fileURLWithPath: FileManager.default.currentDirectoryPath)
    }()

    // MARK: - App data (writable)

    static var appDataDir: URL {
        FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/Lotus")
    }

    /// Config is stored in the writable appDataDir, never inside the app bundle.
    static var configURL: URL {
        appDataDir.appendingPathComponent("config.json")
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
        // Try canonical writable location first
        if let data = try? Data(contentsOf: configURL),
           let cfg  = try? JSONDecoder().decode(AppConfig.self, from: data) {
            return cfg
        }
        // Migrate from legacy Mac-MCP/config.json (dev tree or old install)
        let legacyURL = _devBaseDir.appendingPathComponent("config.json")
        if legacyURL != configURL,
           let data = try? Data(contentsOf: legacyURL),
           let cfg  = try? JSONDecoder().decode(AppConfig.self, from: data) {
            try? cfg.save()   // write to canonical path for next launch
            return cfg
        }
        return nil
    }

    func save() throws {
        try FileManager.default.createDirectory(
            at: AppConfig.appDataDir, withIntermediateDirectories: true)
        let enc = JSONEncoder()
        enc.outputFormatting = [.prettyPrinted]
        let data = try enc.encode(self)
        try data.write(to: AppConfig.configURL, options: .atomic)
    }

    func delete() throws {
        try FileManager.default.removeItem(at: AppConfig.configURL)
    }
}
