import Foundation
import SwiftUI

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

    // Персонализация (сохраняется между запусками)
    @Published var russianOnly: Bool { didSet { defaults.set(russianOnly, forKey: "russianOnly") } }
    @Published var hiddenSources: Set<String> { didSet { defaults.set(Array(hiddenSources), forKey: "hiddenSources") } }
    @Published var readIDs: Set<String> { didSet { defaults.set(Array(readIDs), forKey: "readIDs") } }
    @Published var bookmarkedStories: [Story] { didSet { persistBookmarks() } }
    @Published var feedURL: String { didSet { defaults.set(feedURL, forKey: "feedURL") } }

    private let service = NewsService()
    private let defaults = UserDefaults.standard

    init() {
        russianOnly = defaults.bool(forKey: "russianOnly")
        hiddenSources = Set(defaults.stringArray(forKey: "hiddenSources") ?? [])
        readIDs = Set(defaults.stringArray(forKey: "readIDs") ?? [])
        feedURL = defaults.string(forKey: "feedURL") ?? NewsService.defaultFeedURL
        if let data = defaults.data(forKey: "bookmarks"),
           let saved = try? JSONDecoder().decode([Story].self, from: data) {
            bookmarkedStories = saved
        } else {
            bookmarkedStories = []
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

    // MARK: - Фильтрация

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

    // MARK: - Закладки и прочитанное

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
        readIDs.insert(story.id)
    }

    func isRead(_ story: Story) -> Bool {
        readIDs.contains(story.id)
    }

    private func persistBookmarks() {
        if let data = try? JSONEncoder().encode(bookmarkedStories) {
            defaults.set(data, forKey: "bookmarks")
        }
    }
}
