import Foundation

/// HTTP client for the Lotus control API running on localhost.
/// Reads the current port from the port file written by bot_service.py.
/// All methods return nil / false / [] when the service is unreachable
/// rather than throwing, so callers can treat "service offline" as a state.
struct LotusServiceClient: Sendable {

    static let shared = LotusServiceClient()

    private let session: URLSession = {
        let cfg = URLSessionConfiguration.ephemeral
        cfg.timeoutIntervalForRequest = 3
        cfg.timeoutIntervalForResource = 5
        return URLSession(configuration: cfg)
    }()

    // MARK: - Port discovery

    private var baseURL: URL? {
        guard
            let raw = try? String(contentsOf: AppConfig.controlPortFile, encoding: .utf8),
            let port = Int(raw.trimmingCharacters(in: .whitespacesAndNewlines))
        else { return nil }
        return URL(string: "http://127.0.0.1:\(port)")
    }

    // MARK: - Endpoints

    func status() async -> ServiceStatus? {
        await get("/api/status")
    }

    func logs(lines: Int = 200) async -> [String] {
        guard let r: LogResponse = await get("/api/logs?lines=\(lines)") else { return [] }
        return r.lines
    }

    /// Returns the config dict with the token redacted.
    func config() async -> [String: String]? {
        await get("/api/config")
    }

    @discardableResult
    func updateConfig(_ fields: [String: String]) async -> Bool {
        await post("/api/config", body: fields)
    }

    @discardableResult
    func restart() async -> Bool {
        await post("/api/restart", body: EmptyBody())
    }

    @discardableResult
    func stop() async -> Bool {
        await post("/api/stop", body: EmptyBody())
    }

    // MARK: - Generics

    private func get<T: Decodable>(_ path: String) async -> T? {
        guard let base = baseURL,
              let url = URL(string: path, relativeTo: base)
        else { return nil }
        do {
            let (data, _) = try await session.data(from: url)
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            return nil
        }
    }

    private func post<B: Encodable>(_ path: String, body: B) async -> Bool {
        guard let base = baseURL,
              let url = URL(string: path, relativeTo: base),
              let bodyData = try? JSONEncoder().encode(body)
        else { return false }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.httpBody = bodyData
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        do {
            let (data, _) = try await session.data(for: req)
            // Expect {"ok": true}
            if let obj = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
                return obj["ok"] as? Bool == true
            }
        } catch {}
        return false
    }
}

private struct EmptyBody: Encodable {}
