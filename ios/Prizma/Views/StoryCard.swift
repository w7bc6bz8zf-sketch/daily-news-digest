import SwiftUI

/// Компактная карточка сюжета в ленте
struct StoryCard: View {
    @EnvironmentObject private var state: AppState
    let story: Story

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    CategoryPill(category: story.categoryClean)
                    if let date = story.publishedDate {
                        Text(DateParser.relative(date))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                Text(story.headline)
                    .font(.system(.subheadline, design: .rounded, weight: .bold))
                    .lineLimit(3)
                    .foregroundStyle(state.isRead(story) ? .secondary : .primary)

                if !story.preview.isEmpty {
                    Text(story.preview)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                HStack(spacing: 6) {
                    if let topic = state.matchedTopics(for: story).first {
                        Text("#\(topic)")
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 7)
                            .padding(.vertical, 3)
                            .background(Color.orange.opacity(0.15), in: Capsule())
                            .foregroundStyle(.orange)
                            .lineLimit(1)
                    }
                    if story.coverage > 1 {
                        CoveragePill(coverage: story.coverage)
                    }
                    Text(story.sourceNames.prefix(2).joined(separator: " · "))
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }

            if !story.image.isEmpty {
                StoryImage(url: story.image)
                    .frame(width: 84, height: 84)
                    .clipShape(RoundedRectangle(cornerRadius: 14))
                    .overlay(
                        RoundedRectangle(cornerRadius: 14)
                            .strokeBorder(.quaternary, lineWidth: 0.5)
                    )
            }
        }
        .prizmaCard(padding: 12)
    }
}

