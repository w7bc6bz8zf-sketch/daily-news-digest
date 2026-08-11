import SwiftUI

struct BookmarksView: View {
    @EnvironmentObject private var state: AppState

    var body: some View {
        NavigationStack {
            Group {
                if state.bookmarkedStories.isEmpty {
                    ContentUnavailableView(
                        "Пока пусто",
                        systemImage: "bookmark",
                        description: Text("Сохраняйте сюжеты кнопкой закладки — они будут доступны даже офлайн")
                    )
                } else {
                    List {
                        ForEach(state.bookmarkedStories) { story in
                            NavigationLink(value: story) {
                                StoryCard(story: story)
                            }
                        }
                        .onDelete { indexSet in
                            state.bookmarkedStories.remove(atOffsets: indexSet)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle("Закладки")
            .navigationDestination(for: Story.self) { StoryDetailView(story: $0) }
        }
    }
}
