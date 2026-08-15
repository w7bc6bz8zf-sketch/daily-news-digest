import Foundation

// Он-девайс персонализация в духе Particle «For You»:
// профиль интересов строится из прочитанных сюжетов (категории и источники),
// подписки на темы — простое совпадение ключевых слов. Никаких серверов.

struct InterestProfile: Codable {
    var categoryWeights: [String: Double] = [:]
    var sourceWeights: [String: Double] = [:]

    mutating func registerRead(category: String, sources: [String]) {
        categoryWeights[category, default: 0] += 1
        for s in sources {
            sourceWeights[s, default: 0] += 0.5
        }
    }

    func categoryAffinity(_ category: String) -> Double {
        let total = categoryWeights.values.reduce(0, +)
        guard total > 0 else { return 0 }
        return (categoryWeights[category] ?? 0) / total
    }

    func sourceAffinity(_ sources: [String]) -> Double {
        let total = sourceWeights.values.reduce(0, +)
        guard total > 0 else { return 0 }
        let hit = sources.reduce(0.0) { $0 + (sourceWeights[$1] ?? 0) }
        return min(hit / total, 1.0)
    }
}

enum Personalization {

    /// Темы из подписок, которые встречаются в сюжете.
    static func matchedTopics(in story: Story, topics: [String]) -> [String] {
        guard !topics.isEmpty else { return [] }
        let haystack = (story.headline + " " + story.headlineEn + " " + story.leadExcerpt)
            .lowercased()
        return topics.filter { topic in
            let t = topic.trimmingCharacters(in: .whitespaces).lowercased()
            return !t.isEmpty && haystack.contains(t)
        }
    }

    /// Ранжирующий балл для ленты «Для вас».
    /// position — позиция в исходной ленте (сохраняет редакционный порядок как базу).
    static func score(story: Story, position: Int, profile: InterestProfile,
                      topics: [String], isRead: Bool) -> Double {
        var s = -Double(position) * 0.1
        s += Double(matchedTopics(in: story, topics: topics).count) * 6.0
        s += profile.categoryAffinity(story.categoryClean) * 3.0
        s += profile.sourceAffinity(story.sourceNames) * 1.5
        // Штраф сильнее любых бонусов: прочитанный сюжет всегда уходит вниз
        if isRead { s -= 12.0 }
        return s
    }

    /// Переранжирование ленты под профиль пользователя.
    static func rank(stories: [Story], profile: InterestProfile,
                     topics: [String], readIDs: Set<String>) -> [Story] {
        stories.enumerated()
            .map { (idx, story) in
                (story, score(story: story, position: idx, profile: profile,
                              topics: topics, isRead: readIDs.contains(story.id)))
            }
            .sorted { $0.1 > $1.1 }
            .map { $0.0 }
    }
}
