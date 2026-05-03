import Foundation

/// Manages the com.lotus.botservice launchd agent lifecycle.
/// All methods run synchronously (they shell out to launchctl).
/// Call from a Task or background queue — never from the main thread.
final class ServiceManager: Sendable {

    static let shared = ServiceManager()
    private init() {}

    private let label = "com.lotus.botservice"

    private var serviceTarget: String {
        "gui/\(getuid())/\(label)"
    }

    // MARK: - State queries

    var isPlistInstalled: Bool {
        FileManager.default.fileExists(atPath: AppConfig.launchAgentPlist.path)
    }

    /// Reads RunAtLoad from the installed plist.
    var isStartupEnabled: Bool {
        guard let data = try? Data(contentsOf: AppConfig.launchAgentPlist),
              let plist = try? PropertyListSerialization.propertyList(
                  from: data, format: nil
              ) as? [String: Any]
        else { return false }
        return plist["RunAtLoad"] as? Bool == true
    }

    // MARK: - Lifecycle

    /// Write the launchd plist and bootstrap it for the current user session.
    func install(controlPort: Int = 40510) throws {
        let baseDir = AppConfig.baseDir
        let logFile = AppConfig.botLogFile
        let plistURL = AppConfig.launchAgentPlist

        // Resolve the Python runtime in priority order
        let programArgs = resolveProgramArgs(baseDir: baseDir)
        let argsXML = programArgs
            .map { "        <string>\($0.replacingOccurrences(of: "&", with: "&amp;"))</string>" }
            .joined(separator: "\n")

        let plist = """
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
    "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>\(label)</string>
    <key>ProgramArguments</key>
    <array>
\(argsXML)
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>WorkingDirectory</key>
    <string>\(baseDir.path)</string>
    <key>StandardOutPath</key>
    <string>\(logFile.path)</string>
    <key>StandardErrorPath</key>
    <string>\(logFile.path)</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>ANONYMIZED_TELEMETRY</key>
        <string>true</string>
        <key>LOTUS_CONTROL_PORT</key>
        <string>\(controlPort)</string>
    </dict>
</dict>
</plist>
"""
        try FileManager.default.createDirectory(
            at: plistURL.deletingLastPathComponent(),
            withIntermediateDirectories: true
        )
        try plist.write(to: plistURL, atomically: true, encoding: .utf8)

        // Unload any stale registration before bootstrapping
        _ = try? runLaunchctl(["bootout", serviceTarget])
        _ = try? runLaunchctl(["unload", plistURL.path])   // legacy fallback

        try bootstrap()
    }

    func uninstall() throws {
        _ = try? runLaunchctl(["kill", "SIGTERM", serviceTarget])
        Thread.sleep(forTimeInterval: 1)
        _ = try? runLaunchctl(["bootout", serviceTarget])
        _ = try? runLaunchctl(["unload", AppConfig.launchAgentPlist.path])
        try? FileManager.default.removeItem(at: AppConfig.launchAgentPlist)
        try? FileManager.default.removeItem(at: AppConfig.controlPortFile)
    }

    /// Bootstrap plist + kickstart the service.
    func start() throws {
        guard isPlistInstalled else { throw ServiceError.plistNotInstalled }
        try? bootstrap()        // no-op if already bootstrapped
        try kickstart()
    }

    /// Send SIGTERM via launchctl; falls back to killing by PID.
    func stop() throws {
        do {
            try runLaunchctl(["kill", "SIGTERM", serviceTarget])
        } catch {
            // Fallback: send signal directly to the PID from the PID file
            if let pid = currentPID() {
                kill(pid_t(pid), SIGTERM)
            }
        }
    }

    func setStartupEnabled(_ enabled: Bool) throws {
        guard isPlistInstalled,
              var plist = try? Data(contentsOf: AppConfig.launchAgentPlist),
              var dict = try? PropertyListSerialization.propertyList(
                  from: plist, format: nil
              ) as? [String: Any]
        else { throw ServiceError.plistNotInstalled }

        dict["RunAtLoad"] = enabled
        plist = try PropertyListSerialization.data(
            fromPropertyList: dict,
            format: .xml,
            options: 0
        )
        try plist.write(to: AppConfig.launchAgentPlist, options: .atomic)

        // Reload so launchd picks up the change
        _ = try? runLaunchctl(["bootout", serviceTarget])
        try bootstrap()
    }

    // MARK: - PID helpers

    func currentPID() -> Int? {
        guard
            let txt = try? String(contentsOf: AppConfig.pidFile, encoding: .utf8),
            let pid = Int(txt.trimmingCharacters(in: .whitespacesAndNewlines))
        else { return nil }
        return pid
    }

    func isProcessAlive() -> Bool {
        guard let pid = currentPID() else { return false }
        return kill(pid_t(pid), 0) == 0
    }

    // MARK: - Private helpers

    private func bootstrap() throws {
        try runLaunchctl(["bootstrap", "gui/\(getuid())", AppConfig.launchAgentPlist.path])
    }

    private func kickstart() throws {
        try runLaunchctl(["kickstart", serviceTarget])
    }

    /// Build the ProgramArguments array for the plist, preferring uv.
    private func resolveProgramArgs(baseDir: URL) -> [String] {
        let fm = FileManager.default
        let botScript = baseDir.appendingPathComponent("bot_service.py").path

        // 1. uv (respects the project's virtualenv)
        let uvCandidates = [
            "/opt/homebrew/bin/uv",
            "/usr/local/bin/uv",
            "\(NSHomeDirectory())/.local/bin/uv",
            "\(NSHomeDirectory())/.cargo/bin/uv",
        ]
        for uv in uvCandidates where fm.fileExists(atPath: uv) {
            return [uv, "run", "python", botScript]
        }

        // 2. project .venv
        let venvPython = baseDir.appendingPathComponent(".venv/bin/python").path
        if fm.fileExists(atPath: venvPython) {
            return [venvPython, botScript]
        }

        // 3. system python3
        return ["/usr/bin/env", "python3", botScript]
    }

    @discardableResult
    private func runLaunchctl(_ args: [String]) throws -> String {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        proc.arguments = args
        let out = Pipe(), err = Pipe()
        proc.standardOutput = out
        proc.standardError = err
        try proc.run()
        proc.waitUntilExit()
        let output = String(data: out.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        guard proc.terminationStatus == 0 else {
            let errMsg = String(data: err.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            throw ServiceError.launchctlFailed(code: proc.terminationStatus, message: errMsg.trimmingCharacters(in: .whitespacesAndNewlines))
        }
        return output
    }
}

enum ServiceError: LocalizedError {
    case plistNotInstalled
    case launchctlFailed(code: Int32, message: String)

    var errorDescription: String? {
        switch self {
        case .plistNotInstalled:
            return "Lotus service is not installed. Run install.sh first."
        case .launchctlFailed(let code, let msg):
            return "launchctl failed (exit \(code)): \(msg)"
        }
    }
}
