import Foundation
import SwiftUI

enum FeedMode: String, CaseIterable, Identifiable {
    case forYou, all
    var id: String { rawValue }
    var title: String {
        switch self {
        case .forYou: "Для вас"
        case .all:    "Все"
        }
    }
}

@MainActor
final class AppState: ObservableObject {

    // Лента
    @Published var stories: [Story] = []
    @Published var isLoading = false
    @Published var errorMessage: String?
    @Published var collectedAt: Date?

    // Фильтры
    @Published var selectedCategory: String?
    @Published var searchText = ""
    @Published var feedMode: FeedMode { didSet { defaults.set(feedMode.rawValue, forKey: "feedMode") } }

    // Персонализация (сохраняется между запусками)
    @Published var russianOnly: Bool { didSet { defaults.set(russianOnly, forKey: "russianOnly") } }
    @Published var hiddenSources: Set<String> { didSet { defaults.set(Array(hiddenSources), forKey: "hiddenSources") } }
    @Published var readIDs: Set<String> { didSet { defaults.set(Array(readIDs), forKey: "readIDs") } }
    @Published var bookmarkedStories: [Story] { didSet { persistBookmarks() } }
    @Published var followedTopics: [String] { didSet { defaults.set(followedTopics, forKey: "followedTopics") } }
    @Published var feedURL: String { didSet { defaults.set(feedURL, forKey: "feedURL") } }
    private(set) var profile: InterestProfile

    // Уведомления
    @Published var notifyEnabled: Bool { didSet { defaults.set(notifyEnabled, forKey: "notifyEnabled") } }
    @Published var notifyTime: Date { didSet { defaults.set(notifyTime.timeIntervalSince1970, forKey: "notifyTime") } }

    private let service = NewsService()
    private let defaults = UserDefaults.standard

    init() {
        feedMode = FeedMode(rawValue: defaults.string(forKey: "feedMode") ?? "") ?? .forYou
        russianOnly = defaults.bool(forKey: "russianOnly")
        hiddenSources = Set(defaults.stringArray(forKey: "hiddenSources") ?? [])
        readIDs = Set(defaults.stringArray(forKey: "readIDs") ?? [])
        followedTopics = defaults.stringArray(forKey: "followedTopics") ?? []
        // Миграция: если сохранён старый URL по умолчанию — заменяем на новый
        let storedURL = defaults.string(forKey: "feedURL")
        feedURL = (storedURL == nil || storedURL == NewsService.legacyFeedURL)
            ? NewsService.defaultFeedURL : storedURL!
        notifyEnabled = defaults.bool(forKey: "notifyEnabled")
        let t = defaults.double(forKey: "notifyTime")
        notifyTime = t > 0 ? Date(timeIntervalSince1970: t)
            : Calendar.current.date(bySettingHour: 8, minute: 30, second: 0, of: .now) ?? .now
        if let data = defaults.data(forKey: "bookmarks"),
           let saved = try? JSONDecoder().decode([Story].self, from: data) {
            bookmarkedStories = saved
        } else {
            bookmarkedStories = []
        }
        if let data = defaults.data(forKey: "interestProfile"),
           let saved = try? JSONDecoder().decode(InterestProfile.self, from: data) {
            profile = saved
        } else {
            profile = InterestProfile()
        }
    }

    // MARK: - Загрузка

    func loadInitial() async {
        if let cached = service.loadCached() {
            apply(cached)
        }
        await refresh()
    }

    func refresh() async {
        isLoading = true
        errorMessage = nil
        do {
            let digest = try await service.fetchDigest(from: feedURL)
            apply(digest)
        } catch {
            if stories.isEmpty {
                errorMessage = "Не удалось загрузить новости. Проверьте соединение."
            }
        }
        isLoading = false
    }

    private func apply(_ digest: NewsDigest) {
        stories = digest.stories
        collectedAt = DateParser.parse(digest.collectedAt)
    }

    // MARK: - Фильтрация и ранжирование

    var availableCategories: [String] {
        var seen = Set<String>()
        return stories.map(\.categoryClean).filter { seen.insert($0).inserted }
    }

    var allSources: [String] {
        var seen = Set<String>()
        return stories.flatMap(\.sourceNames).filter { seen.insert($0).inserted }.sorted()
    }

    var filteredStories: [Story] {
        stories.filter { story in
            if russianOnly && story.lang != "ru" { return false }
            if let cat = selectedCategory, story.categoryClean != cat { return false }
            if !hiddenSources.isEmpty
                && story.sourceNames.allSatisfy({ hiddenSources.contains($0) }) { return false }
            if !searchText.isEmpty {
                let q = searchText.lowercased()
                let haystack = (story.headline + " " + story.headlineEn + " "
                                + story.leadExcerpt).lowercased()
                if !haystack.contains(q) { return false }
            }
            return true
        }
    }

    /// Что показывает лента: «Все» — редакционный порядок,
    /// «Для вас» — переранжирование под профиль и темы.
    var displayedStories: [Story] {
        switch feedMode {
        case .all:
            return filteredStories
        case .forYou:
            return Personalization.rank(stories: filteredStories, profile: profile,
                                        topics: followedTopics, readIDs: readIDs)
        }
    }

    func matchedTopics(for story: Story) -> [String] {
        Personalization.matchedTopics(in: story, topics: followedTopics)
    }

    // MARK: - Темы

    func followTopic(_ raw: String) {
        let topic = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !topic.isEmpty,
              !followedTopics.contains(where: { $0.caseInsensitiveCompare(topic) == .orderedSame })
        else { return }
        followedTopics.append(topic)
    }

    func unfollowTopic(_ topic: String) {
        followedTopics.removeAll { $0 == topic }
    }

    // MARK: - Закладки, прочитанное, профиль

    func isBookmarked(_ story: Story) -> Bool {
        bookmarkedStories.contains { $0.id == story.id }
    }

    func toggleBookmark(_ story: Story) {
        if let idx = bookmarkedStories.firstIndex(where: { $0.id == story.id }) {
            bookmarkedStories.remove(at: idx)
        } else {
            bookmarkedStories.insert(story, at: 0)
        }
    }

    func markRead(_ story: Story) {
        guard !readIDs.contains(story.id) else { return }
        readIDs.insert(story.id)
        profile.registerRead(category: story.categoryClean, sources: story.sourceNames)
        persistProfile()
    }

    func isRead(_ story: Story) -> Bool {
        readIDs.contains(story.id)
    }

    func resetProfile() {
        profile = InterestProfile()
        persistProfile()
        objectWillChange.send()
    }

    private func persistProfile() {
        if let data = try? JSONEncoder().encode(profile) {
            defaults.set(data, forKey: "interestProfile")
        }
    }

    private func persistBookmarks() {
        if let data = try? JSONEncoder().encode(bookmarkedStories) {
            defaults.set(data, forKey: "bookmarks")
        }
    }
}
