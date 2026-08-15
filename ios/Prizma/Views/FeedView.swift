import SwiftUI

struct FeedView: View {
    @EnvironmentObject private var state: AppState
    @StateObject private var briefing = BriefingPlayer()

    var body: some View {
        NavigationStack {
            Group {
                if state.stories.isEmpty && state.isLoading {
                    ProgressView("Загружаем новости…")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let error = state.errorMessage, state.stories.isEmpty {
                    ContentUnavailableView(
                        "Нет соединения",
                        systemImage: "wifi.slash",
                        description: Text(error)
                    )
                } else {
                    feedList
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .background(Theme.background)
            .navigationTitle("Призма")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        briefing.toggle(stories: state.displayedStories)
                    } label: {
                        Image(systemName: briefing.isPlaying
                              ? "stop.circle.fill" : "headphones.circle.fill")
                            .font(.title3)
                            .foregroundStyle(Theme.prism)
                    }
                    .accessibilityLabel(briefing.isPlaying
                                        ? "Остановить аудио-брифинг" : "Аудио-брифинг")
                }
            }
            .navigationDestination(for: Story.self) { StoryDetailView(story: $0) }
            .searchable(text: $state.searchText, prompt: "Поиск по сюжетам")
            .refreshable { await state.refresh() }
        }
        .tint(Theme.accent)
    }

    /// Топ-3 сюжета с фото — в карусель, остальные — списком
    private var featuredStories: [Story] {
        Array(state.displayedStories.filter { !$0.image.isEmpty }.prefix(3))
    }

    private var listStories: [Story] {
        let featuredIDs = Set(featuredStories.map(\.id))
        return state.displayedStories.filter { !featuredIDs.contains($0.id) }
    }

    private var feedList: some View {
        List {
            Section {
                if !featuredStories.isEmpty {
                    FeaturedCarousel(stories: featuredStories)
                        .listRowInsets(EdgeInsets(top: 2, leading: 0, bottom: 6, trailing: 0))
                        .listRowSeparator(.hidden)
                        .listRowBackground(Color.clear)
                }
                ForEach(listStories) { story in
                    NavigationLink(value: story) {
                        StoryCard(story: story)
                    }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                    .listRowSeparator(.hidden)
                    .listRowBackground(Color.clear)
                }
            } header: {
                VStack(alignment: .leading, spacing: 10) {
                    Picker("Режим ленты", selection: $state.feedMode) {
                        ForEach(FeedMode.allCases) { mode in
                            Text(mode.title).tag(mode)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal, 16)

                    categoryChips

                    if let date = state.collectedAt {
                        Text("Обновлено \(DateParser.relative(date))")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 16)
                    }
                }
                .textCase(nil)
                .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 8, trailing: 0))
            }
        }
        .listStyle(.plain)
        .scrollContentBackground(.hidden)
        .overlay {
            if state.displayedStories.isEmpty && !state.stories.isEmpty {
                ContentUnavailableView(
                    "Ничего не найдено",
                    systemImage: "magnifyingglass",
                    description: Text("Попробуйте изменить фильтры или запрос")
                )
            }
        }
    }

    private var categoryChips: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                chip(title: "Все", icon: "square.grid.2x2.fill", value: nil)
                ForEach(state.availableCategories, id: \.self) { cat in
                    chip(title: cat, icon: NewsCategory.icon(for: cat), value: cat)
                }
            }
            .padding(.horizontal, 16)
        }
    }

    private func chip(title: String, icon: String, value: String?) -> some View {
        let isSelected = state.selectedCategory == value
        return Button {
            withAnimation(.snappy) { state.selectedCategory = value }
        } label: {
            Label(title, systemImage: icon)
                .font(.footnote.weight(.medium))
                .padding(.horizontal, 12)
                .padding(.vertical, 7)
                .background {
                    if isSelected {
                        Capsule().fill(Theme.prism)
                    } else {
                        Capsule().fill(Theme.chip)
                    }
                }
                .foregroundStyle(isSelected ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    FeedView().environmentObject(AppState())
}
