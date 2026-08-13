import SwiftUI

struct StoryDetailView: View {
    @EnvironmentObject private var state: AppState
    let story: Story

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if !story.image.isEmpty {
                    StoryImage(url: story.image)
                        .frame(maxWidth: .infinity)
                        .frame(height: 210)
                        .clipShape(RoundedRectangle(cornerRadius: 18))
                }

                HStack(spacing: 8) {
                    CategoryPill(category: story.categoryClean)
                    if let date = story.publishedDate {
                        Text(DateParser.relative(date))
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                Text(story.headline)
                    .font(.system(.title2, design: .rounded, weight: .bold))

                if !story.headlineEn.isEmpty && story.headlineEn != story.headline {
                    Text(story.headlineEn)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if story.coverage > 1 {
                    HStack(spacing: -6) {
                        ForEach(story.sourceNames.prefix(5), id: \.self) { source in
                            SourceAvatar(name: source, size: 26)
                                .overlay(Circle().strokeBorder(Color(.systemBackground), lineWidth: 1.5))
                        }
                        Text("Сюжет освещают \(sourcesCountText(story.coverage))")
                            .font(.footnote.weight(.medium))
                            .foregroundStyle(.secondary)
                            .padding(.leading, 14)
                    }
                }

                if !story.summary.isEmpty {
                    summaryCard
                }

                Text("Перспективы")
                    .font(.system(.headline, design: .rounded))

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

    private var summaryCard: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack(spacing: 6) {
                Image(systemName: "sparkles")
                    .font(.subheadline)
                    .foregroundStyle(Theme.prism)
                Text("Кратко")
                    .font(.system(.headline, design: .rounded))
            }
            ForEach(story.summary, id: \.self) { point in
                HStack(alignment: .top, spacing: 10) {
                    Capsule()
                        .fill(Theme.prism)
                        .frame(width: 3)
                        .padding(.vertical, 2)
                    Text(point)
                        .font(.subheadline)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.accent.opacity(0.07), in: RoundedRectangle(cornerRadius: 16))
        .overlay(
            RoundedRectangle(cornerRadius: 16)
                .strokeBorder(Theme.accent.opacity(0.15), lineWidth: 1)
        )
    }
}

private struct PerspectiveCard: View {
    let perspective: Perspective

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                SourceAvatar(name: perspective.source)
                Text(perspective.source)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
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
                        .foregroundStyle(Theme.accent)
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}
