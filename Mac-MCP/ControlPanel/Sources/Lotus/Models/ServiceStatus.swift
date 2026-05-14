import Foundation

/// Decoded response from GET /api/status
struct ServiceStatus: Decodable, Sendable {
    let running: Bool
    let pid: Int
    let uptime_seconds: Int
    let telegram_connected: Bool
    let ollama_model: String
    let ollama_reachable: Bool
    let service_version: String
    let control_port: Int

    var uptimeFormatted: String {
        let s = uptime_seconds
        if s < 60 { return "\(s)s" }
        if s < 3600 { return "\(s / 60)m \(s % 60)s" }
        return "\(s / 3600)h \(s % 3600 / 60)m"
    }
}

/// Decoded response from GET /api/logs
struct LogResponse: Decodable, Sendable {
    let lines: [String]
}
