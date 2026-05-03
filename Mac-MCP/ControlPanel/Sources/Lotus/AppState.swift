import Foundation
import Combine

@MainActor
final class AppState: ObservableObject {

    static let shared = AppState()
    private init() {
        config = AppConfig.load()
    }

    // MARK: - Published state

    @Published var config: AppConfig?
    @Published var serviceStatus: ServiceStatus?
    @Published var logLines: [String] = []
    @Published var ollamaModels: [String] = []
    @Published var startupEnabled = false

    @Published var isStarting = false
    @Published var isStopping = false
    @Published var lastError: String?

    // MARK: - Derived

    /// True when baseDir cannot be found — triggers folder picker
    var baseDirMissing: Bool {
        !FileManager.default.fileExists(
            atPath: AppConfig.baseDir.appendingPathComponent("bot_service.py").path
        )
    }

    // MARK: - Polling

    private var statusTask: Task<Void, Never>?
    private var logTask: Task<Void, Never>?

    func startPolling() {
        guard statusTask == nil else { return }

        statusTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.pollStatus()
                try? await Task.sleep(for: .seconds(5))
            }
        }

        logTask = Task { [weak self] in
            while !Task.isCancelled {
                if self?.serviceStatus?.running == true {
                    await self?.pollLogs()
                }
                try? await Task.sleep(for: .seconds(1))
            }
        }
    }

    func stopPolling() {
        statusTask?.cancel(); statusTask = nil
        logTask?.cancel();    logTask = nil
    }

    // MARK: - Bot control

    func startBot() async {
        guard !isStarting else { return }
        isStarting = true
        lastError = nil
        appendLog("▶ Starting Lotus bot service…")

        do {
            try await Task.detached(priority: .userInitiated) {
                let sm = ServiceManager.shared
                if !sm.isPlistInstalled { try sm.install() }
                try sm.start()
            }.value
            appendLog("✅ Start signal sent — waiting for service…")
            try? await Task.sleep(for: .seconds(3))
            await pollStatus()
        } catch {
            lastError = error.localizedDescription
            appendLog("❌ \(error.localizedDescription)")
        }
        isStarting = false
    }

    func stopBot() async {
        guard !isStopping else { return }
        isStopping = true
        lastError = nil
        appendLog("⏹ Stopping bot service…")

        let ok = await LotusServiceClient.shared.stop()
        if !ok {
            do {
                try await Task.detached(priority: .userInitiated) {
                    try ServiceManager.shared.stop()
                }.value
            } catch {
                lastError = error.localizedDescription
                appendLog("❌ \(error.localizedDescription)")
                isStopping = false
                return
            }
        }
        appendLog("⏹ Stop signal sent.")
        try? await Task.sleep(for: .seconds(2))
        await pollStatus()
        isStopping = false
    }

    // MARK: - Config management

    func saveConfig(_ newConfig: AppConfig) async {
        let wasRunning = serviceStatus?.running == true
        lastError = nil
        do {
            try newConfig.save()
            config = newConfig
            appendLog("💾 Config saved.")
            if wasRunning {
                appendLog("⟳ Restarting service to apply new settings…")
                _ = await LotusServiceClient.shared.restart()
                try? await Task.sleep(for: .seconds(3))
                await startBot()
            }
        } catch {
            lastError = error.localizedDescription
            appendLog("❌ Save failed: \(error.localizedDescription)")
        }
    }

    func resetConfig() async {
        if serviceStatus?.running == true { await stopBot() }
        try? config?.delete()
        config = nil
        serviceStatus = nil
        logLines = []
        lastError = nil
        appendLog("🔄 Config reset.")
    }

    func reloadConfig() {
        config = AppConfig.load()
    }

    // MARK: - Startup toggle

    func refreshStartupEnabled() {
        startupEnabled = ServiceManager.shared.isStartupEnabled
    }

    func toggleStartup(_ enabled: Bool) async {
        do {
            try await Task.detached(priority: .userInitiated) {
                try ServiceManager.shared.setStartupEnabled(enabled)
            }.value
            startupEnabled = enabled
            appendLog(enabled ? "🚀 Start on login enabled." : "Start on login disabled.")
        } catch {
            lastError = error.localizedDescription
            appendLog("❌ \(error.localizedDescription)")
        }
    }

    // MARK: - Ollama

    func fetchOllamaModels() async {
        let models = await OllamaClient.shared.fetchModels()
        ollamaModels = models
    }

    // MARK: - Log helpers

    func appendLog(_ message: String) {
        let ts = DateFormatter.localizedString(from: Date(), dateStyle: .none, timeStyle: .medium)
        logLines.append("[\(ts)] \(message)")
        if logLines.count > 500 { logLines.removeFirst(logLines.count - 500) }
    }

    // MARK: - Private

    private func pollStatus() async {
        serviceStatus = await LotusServiceClient.shared.status()
    }

    private func pollLogs() async {
        let fetched = await LotusServiceClient.shared.logs(lines: 200)
        guard !fetched.isEmpty else { return }
        // Append only lines not already shown (match by prefix count)
        let alreadyShown = logLines.filter { $0.first != "[" || $0.count < 5 ? false : true }.count
        let newLines = Array(fetched.dropFirst(max(0, alreadyShown)))
        if !newLines.isEmpty {
            logLines.append(contentsOf: newLines)
            if logLines.count > 500 { logLines.removeFirst(logLines.count - 500) }
        }
    }
}
