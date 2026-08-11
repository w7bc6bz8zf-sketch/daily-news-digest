import SwiftUI

struct FeedView: View {
    @EnvironmentObject private var state: AppState

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
            .navigationTitle("Призма")
            .navigationDestination(for: Story.self) { StoryDetailView(story: $0) }
            .searchable(text: $state.searchText, prompt: "Поиск по сюжетам")
            .refreshable { await state.refresh() }
        }
    }

    private var feedList: some View {
        List {
            Section {
                ForEach(state.filteredStories) { story in
                    NavigationLink(value: story) {
                        StoryCard(story: story)
                    }
                    .listRowInsets(EdgeInsets(top: 6, leading: 16, bottom: 6, trailing: 16))
                }
            } header: {
                VStack(alignment: .leading, spacing: 10) {
                    categoryChips
                    if let date = state.collectedAt {
                        Text("Обновлено \(DateParser.relative(date))")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                .textCase(nil)
                .listRowInsets(EdgeInsets(top: 4, leading: 0, bottom: 8, trailing: 0))
            }
        }
        .listStyle(.plain)
        .overlay {
            if state.filteredStories.isEmpty && !state.stories.isEmpty {
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
                .background(isSelected ? Color.indigo : Color(.secondarySystemBackground),
                            in: Capsule())
                .foregroundStyle(isSelected ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    FeedView().environmentObject(AppState())
}
