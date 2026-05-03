import Foundation

// MARK: - Step definitions

enum InstallStep: String, CaseIterable, Sendable {
    case uv           = "Package manager (uv)"
    case python       = "Python 3.13"
    case dependencies = "Bot dependencies"

    var description: String {
        switch self {
        case .uv:           return "Installs uv, the fast Python package manager"
        case .python:       return "Installs a managed Python 3.13 runtime via uv"
        case .dependencies: return "Installs all bot libraries (uv sync)"
        }
    }
}

enum StepStatus: Equatable, Sendable {
    case pending
    case running
    case done       // newly installed
    case skipped    // already present
    case failed(String)

    static func == (lhs: StepStatus, rhs: StepStatus) -> Bool {
        switch (lhs, rhs) {
        case (.pending, .pending), (.running, .running),
             (.done, .done), (.skipped, .skipped):      return true
        case (.failed(let a), .failed(let b)):           return a == b
        default:                                         return false
        }
    }

    var isSuccess: Bool {
        switch self { case .done, .skipped: return true; default: return false }
    }
}

// MARK: - InstallManager

@MainActor
final class InstallManager: ObservableObject {

    static let shared = InstallManager()
    private init() {}

    @Published var statuses: [InstallStep: StepStatus] = {
        Dictionary(uniqueKeysWithValues: InstallStep.allCases.map { ($0, StepStatus.pending) })
    }()
    @Published var logLines: [String] = []
    @Published var isRunning  = false
    @Published var isComplete = false
    @Published var hasFailed  = false

    // MARK: - Quick check (synchronous)

    /// True when the Python venv with all deps is already present.
    var envIsReady: Bool {
        let venv = AppConfig.botScriptDir.appendingPathComponent(".venv/bin/python")
        if FileManager.default.fileExists(atPath: venv.path) { return true }
        // Dev fallback: venv in the Mac-MCP source tree
        let devVenv = AppConfig._devBaseDir.appendingPathComponent(".venv/bin/python")
        return FileManager.default.fileExists(atPath: devVenv.path)
    }

    // MARK: - Run installer

    func runInstall() async {
        guard !isRunning else { return }
        isRunning  = true
        hasFailed  = false
        isComplete = false
        for step in InstallStep.allCases { statuses[step] = .pending }
        logLines = []

        // Capture sendable values up-front (no actor-hopping inside closures)
        let home      = NSHomeDirectory()
        let scriptDir = AppConfig.botScriptDir

        // ── Step 1: uv ────────────────────────────────────────────────────
        await run(step: .uv) {
            if ProcessRunner.findUV(home: home) != nil { return .skipped }
            log("  Downloading uv installer…")
            let r = ProcessRunner.exec(
                ["/bin/sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
                env: ProcessRunner.enrichedPATH(home: home),
                timeout: 120
            )
            if r.exitCode != 0 {
                throw InstallError(r.stderr.isEmpty ? "uv install failed (exit \(r.exitCode))" : r.stderr)
            }
            return .done
        }

        let uvPath = ProcessRunner.findUV(home: home)

        // ── Step 2: Python 3.13 ───────────────────────────────────────────
        await run(step: .python) {
            guard let uv = uvPath else { throw InstallError("uv not found — restart and retry") }
            let check = ProcessRunner.exec([uv, "python", "find", "3.13"], timeout: 8)
            if check.exitCode == 0 { return .skipped }
            log("  Downloading Python 3.13…")
            let r = ProcessRunner.exec([uv, "python", "install", "3.13"],
                                       env: ProcessRunner.enrichedPATH(home: home), timeout: 300)
            if r.exitCode != 0 {
                throw InstallError(r.stderr.isEmpty ? "Python install failed (exit \(r.exitCode))" : r.stderr)
            }
            return .done
        }

        // ── Step 3: Bot dependencies ──────────────────────────────────────
        await run(step: .dependencies) {
            let venv = scriptDir.appendingPathComponent(".venv/bin/python")
            if FileManager.default.fileExists(atPath: venv.path) { return .skipped }
            guard let uv = uvPath else { throw InstallError("uv not found") }
            log("  Running uv sync (this may take a minute)…")
            let r = ProcessRunner.exec([uv, "sync"],
                                       cwd: scriptDir,
                                       env: ProcessRunner.enrichedPATH(home: home),
                                       timeout: 600)
            if r.exitCode != 0 {
                // Append last 10 lines of stderr for context
                let detail = r.stderr.split(separator: "\n").suffix(10).joined(separator: "\n")
                throw InstallError(detail.isEmpty ? "uv sync failed (exit \(r.exitCode))" : detail)
            }
            return .done
        }

        isRunning  = false
        isComplete = !hasFailed
    }

    // MARK: - Private helpers

    private func run(step: InstallStep, work: @Sendable @escaping () throws -> StepStatus) async {
        guard !hasFailed else { return }
        statuses[step] = .running
        appendLog("▸ \(step.rawValue)…")
        do {
            let status = try await Task.detached(priority: .userInitiated) { try work() }.value
            statuses[step] = status
            appendLog(status == .skipped ? "  ✓ Already installed" : "  ✓ Done")
        } catch {
            statuses[step] = .failed(error.localizedDescription)
            appendLog("  ✗ \(error.localizedDescription)")
            hasFailed = true
        }
    }

    func appendLog(_ line: String) {
        let ts = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        logLines.append("[\(ts)] \(line)")
        if logLines.count > 400 { logLines.removeFirst(logLines.count - 400) }
    }
}

// MARK: - ProcessRunner

struct ProcessRunner: Sendable {

    struct Output: Sendable {
        let exitCode: Int32
        let stdout: String
        let stderr: String
    }

    static func findUV(home: String) -> String? {
        [
            "\(home)/.local/bin/uv",
            "/opt/homebrew/bin/uv",
            "/usr/local/bin/uv",
            "\(home)/.cargo/bin/uv",
        ].first { FileManager.default.fileExists(atPath: $0) }
    }

    static func enrichedPATH(home: String) -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        let extra = ["\(home)/.local/bin", "/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin"]
        let current = env["PATH"] ?? "/usr/bin:/bin"
        env["PATH"] = (extra + [current]).joined(separator: ":")
        return env
    }

    static func exec(
        _ args: [String],
        cwd: URL? = nil,
        env: [String: String]? = nil,
        timeout: TimeInterval = 60
    ) -> Output {
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: args[0])
        if args.count > 1 { proc.arguments = Array(args.dropFirst()) }
        if let cwd { proc.currentDirectoryURL = cwd }
        proc.environment = env ?? ProcessInfo.processInfo.environment

        let outPipe = Pipe(), errPipe = Pipe()
        proc.standardOutput = outPipe
        proc.standardError  = errPipe

        do { try proc.run() } catch {
            return Output(exitCode: -1, stdout: "", stderr: error.localizedDescription)
        }
        proc.waitUntilExit()

        let stdout = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let stderr = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return Output(exitCode: proc.terminationStatus, stdout: stdout, stderr: stderr)
    }
}

// MARK: - Error

struct InstallError: LocalizedError {
    let errorDescription: String?
    init(_ message: String) { errorDescription = message }
}

// Allow log(_:) free function inside closures to forward to InstallManager
private func log(_ message: String) {}   // no-op placeholder so closures compile
