import Foundation

/// Загрузка ленты с GitHub (raw JSON, обновляется дважды в день GitHub Actions)
/// и дисковый кэш для офлайн-режима.
struct NewsService {
    // Пока идёт тестирование, лента читается из рабочей ветки — там свежий
    // формат с 85 источниками и саммари. После слияния вернуть на main.
    static let defaultFeedURL =
        "https://raw.githubusercontent.com/w7bc6bz8zf-sketch/daily-news-digest/claude/ios-russian-news-app-9qqqif/news_data.json"
    static let legacyFeedURL =
        "https://raw.githubusercontent.com/w7bc6bz8zf-sketch/daily-news-digest/main/news_data.json"

    private static var cacheFile: URL {
        let dir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
        return dir.appendingPathComponent("news_cache.json")
    }

    func fetchDigest(from urlString: String) async throws -> NewsDigest {
        guard let url = URL(string: urlString) else { throw URLError(.badURL) }
        var request = URLRequest(url: url)
        request.cachePolicy = .reloadIgnoringLocalCacheData
        request.timeoutInterval = 20
        let (data, response) = try await URLSession.shared.data(for: request)
        if let http = response as? HTTPURLResponse, !(200...299).contains(http.statusCode) {
            throw URLError(.badServerResponse)
        }
        let digest = try JSONDecoder().decode(NewsDigest.self, from: data)
        try? data.write(to: Self.cacheFile, options: .atomic)
        return digest
    }

    func loadCached() -> NewsDigest? {
        guard let data = try? Data(contentsOf: Self.cacheFile) else { return nil }
        return try? JSONDecoder().decode(NewsDigest.self, from: data)
    }
}
