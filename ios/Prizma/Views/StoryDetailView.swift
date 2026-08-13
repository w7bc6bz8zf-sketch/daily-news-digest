import SwiftUI

struct StoryDetailView: View {
    @EnvironmentObject private var state: AppState
    let story: Story

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if !story.image.isEmpty, let url = URL(string: story.image) {
                    AsyncImage(url: url) { phase in
                        if case .success(let image) = phase {
                            image.resizable().aspectRatio(contentMode: .fill)
                        }
                    }
                    .frame(maxWidth: .infinity)
                    .frame(height: 200)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
                }

                HStack(spacing: 8) {
                    Label(story.categoryClean, systemImage: NewsCategory.icon(for: story.categoryClean))
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.indigo)
                    if let date = story.publishedDate {
                        Text(DateParser.relative(date))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Text(story.headline)
                    .font(.title2.weight(.bold))

                if !story.headlineEn.isEmpty && story.headlineEn != story.headline {
                    Text(story.headlineEn)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if story.coverage > 1 {
                    Label("Сюжет освещают \(sourcesCountText(story.coverage))",
                          systemImage: "eyes")
                        .font(.footnote.weight(.medium))
                        .foregroundStyle(.secondary)
                }

                if !story.summary.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Кратко")
                            .font(.headline)
                        ForEach(story.summary, id: \.self) { point in
                            HStack(alignment: .top, spacing: 8) {
                                Circle()
                                    .fill(Color.indigo)
                                    .frame(width: 6, height: 6)
                                    .padding(.top, 6)
                                Text(point)
                                    .font(.subheadline)
                            }
                        }
                    }
                    .padding(14)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(Color.indigo.opacity(0.08),
                                in: RoundedRectangle(cornerRadius: 14))
                }

                Divider()

                Text("Перспективы")
                    .font(.headline)

                ForEach(story.perspectives) { perspective in
                    PerspectiveCard(perspective: perspective)
                }
            }
            .padding(16)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItemGroup(placement: .topBarTrailing) {
                Button {
                    state.toggleBookmark(story)
                } label: {
                    Image(systemName: state.isBookmarked(story) ? "bookmark.fill" : "bookmark")
                }
                if let url = URL(string: story.perspectives.first?.url ?? "") {
                    ShareLink(item: url) { Image(systemName: "square.and.arrow.up") }
                }
            }
        }
        .onAppear { state.markRead(story) }
    }
}

private struct PerspectiveCard: View {
    let perspective: Perspective

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(perspective.source)
                    .font(.subheadline.weight(.bold))
                Spacer()
                Text(perspective.lang == "ru" ? "RU" : "EN")
                    .font(.caption2.weight(.bold))
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color(.tertiarySystemBackground), in: Capsule())
                    .foregroundStyle(.secondary)
            }

            Text(perspective.headline)
                .font(.footnote.weight(.semibold))

            if !perspective.excerpt.isEmpty {
                Text(perspective.excerpt)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            if let url = URL(string: perspective.url) {
                Link(destination: url) {
                    Label("Читать в источнике", systemImage: "arrow.up.right.square")
                        .font(.caption.weight(.semibold))
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 14))
    }
}
