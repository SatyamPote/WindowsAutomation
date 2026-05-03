import Foundation

struct OllamaClient: Sendable {
    static let shared = OllamaClient()

    private let session: URLSession = {
        let c = URLSessionConfiguration.ephemeral
        c.timeoutIntervalForRequest = 3
        return URLSession(configuration: c)
    }()

    func fetchModels() async -> [String] {
        guard let url = URL(string: "http://localhost:11434/api/tags") else { return [] }
        do {
            let (data, _) = try await session.data(from: url)
            let resp = try JSONDecoder().decode(TagsResponse.self, from: data)
            return resp.models.map(\.name).sorted()
        } catch {
            return []
        }
    }

    func isReachable() async -> Bool {
        !(await fetchModels()).isEmpty
    }
}

private struct TagsResponse: Decodable {
    let models: [ModelEntry]
}
private struct ModelEntry: Decodable {
    let name: String
}
