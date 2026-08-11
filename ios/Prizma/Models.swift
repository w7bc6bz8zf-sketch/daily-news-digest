import Foundation

// MARK: - Модель данных news_data.json

struct NewsDigest: Codable {
    let collectedAt: String?
    let storyCount: Int?
    let stories: [Story]

    enum CodingKeys: String, CodingKey {
        case collectedAt = "collected_at"
        case storyCount = "story_count"
        case stories
    }
}

struct Story: Codable, Identifiable, Hashable {
    let id: String
    let category: String
    let lang: String
    let headline: String
    let headlineEn: String
    let coverage: Int
    let singleSource: Bool
    let image: String
    let publishedAt: String?
    let perspectives: [Perspective]

    enum CodingKeys: String, CodingKey {
        case id, category, lang, headline, coverage, image, perspectives
        case headlineEn = "headline_en"
        case singleSource = "single_source"
        case publishedAt = "published_at"
    }

    // Терпимое декодирование: поддерживает и старый формат ленты (headline_en без id)
    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        category = try c.decodeIfPresent(String.self, forKey: .category) ?? "Новости"
        headlineEn = try c.decodeIfPresent(String.self, forKey: .headlineEn) ?? ""
        perspectives = try c.decodeIfPresent([Perspective].self, forKey: .perspectives) ?? []
        headline = try c.decodeIfPresent(String.self, forKey: .headline) ?? headlineEn
        id = try c.decodeIfPresent(String.self, forKey: .id)
            ?? perspectives.first?.url ?? headline
        lang = try c.decodeIfPresent(String.self, forKey: .lang)
            ?? (headline.containsCyrillic ? "ru" : "en")
        coverage = try c.decodeIfPresent(Int.self, forKey: .coverage) ?? perspectives.count
        singleSource = try c.decodeIfPresent(Bool.self, forKey: .singleSource) ?? (perspectives.count < 2)
        image = try c.decodeIfPresent(String.self, forKey: .image) ?? ""
        publishedAt = try c.decodeIfPresent(String.self, forKey: .publishedAt)
    }

    var publishedDate: Date? { DateParser.parse(publishedAt) }

    var sourceNames: [String] { perspectives.map(\.source) }

    var leadExcerpt: String { perspectives.first?.excerpt ?? "" }

    var categoryClean: String {
        // Старый формат содержал эмодзи в категории ("🌍 World") — убираем
        category.unicodeScalars
            .filter { !$0.properties.isEmojiPresentation }
            .reduce(into: "") { $0.append(Character($1)) }
            .trimmingCharacters(in: .whitespaces)
    }
}

struct Perspective: Codable, Hashable, Identifiable {
    let source: String
    let lang: String
    let headline: String
    let excerpt: String
    let url: String
    let publishedAt: String?

    var id: String { url.isEmpty ? source + headline : url }

    enum CodingKeys: String, CodingKey {
        case source, lang, headline, excerpt, url
        case publishedAt = "published_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        source = try c.decodeIfPresent(String.self, forKey: .source) ?? "Источник"
        headline = try c.decodeIfPresent(String.self, forKey: .headline) ?? ""
        excerpt = try c.decodeIfPresent(String.self, forKey: .excerpt) ?? ""
        url = try c.decodeIfPresent(String.self, forKey: .url) ?? ""
        lang = try c.decodeIfPresent(String.self, forKey: .lang)
            ?? (headline.containsCyrillic ? "ru" : "en")
        publishedAt = try c.decodeIfPresent(String.self, forKey: .publishedAt)
    }
}

// MARK: - Категории

enum NewsCategory {
    static let icons: [String: String] = [
        "Мир": "globe.europe.africa.fill",
        "Россия": "building.columns.fill",
        "Экономика": "chart.line.uptrend.xyaxis",
        "Бизнес": "briefcase.fill",
        "Технологии": "cpu.fill",
        "Наука": "atom",
        "Спорт": "figure.run",
        "Культура": "theatermasks.fill",
    ]

    static func icon(for category: String) -> String {
        icons[category] ?? "newspaper.fill"
    }
}

// MARK: - Утилиты

enum DateParser {
    private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()
    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    static func parse(_ string: String?) -> Date? {
        guard var s = string, !s.isEmpty else { return nil }
        // Python isoformat даёт 6 знаков микросекунд — ISO8601DateFormatter ждёт 3
        if let dotRange = s.range(of: #"\.\d{4,6}"#, options: .regularExpression) {
            let ms = String(s[dotRange].prefix(4))
            s.replaceSubrange(dotRange, with: ms)
        }
        return iso.date(from: s) ?? isoFractional.date(from: s)
    }

    static func relative(_ date: Date?) -> String {
        guard let date else { return "" }
        let f = RelativeDateTimeFormatter()
        f.locale = Locale(identifier: "ru_RU")
        f.unitsStyle = .short
        return f.localizedString(for: date, relativeTo: .now)
    }
}

extension String {
    var containsCyrillic: Bool {
        range(of: "[а-яА-ЯёЁ]", options: .regularExpression) != nil
    }
}

func sourcesCountText(_ n: Int) -> String {
    let mod10 = n % 10, mod100 = n % 100
    let word: String
    if mod10 == 1 && mod100 != 11 { word = "источник" }
    else if (2...4).contains(mod10) && !(12...14).contains(mod100) { word = "источника" }
    else { word = "источников" }
    return "\(n) \(word)"
}
