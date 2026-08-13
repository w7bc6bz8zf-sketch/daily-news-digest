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
        .padding(.vertical, 4)
    }
}

/// Крупная карточка главного сюжета (первый в ленте)
struct FeaturedStoryCard: View {
    @EnvironmentObject private var state: AppState
    let story: Story

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if !story.image.isEmpty {
                StoryImage(url: story.image)
                    .frame(maxWidth: .infinity)
                    .frame(height: 170)
                    .clipShape(RoundedRectangle(cornerRadius: 16))
            }

            HStack(spacing: 6) {
                CategoryPill(category: story.categoryClean)
                if story.coverage > 1 {
                    CoveragePill(coverage: story.coverage)
                }
                if let date = story.publishedDate {
                    Text(DateParser.relative(date))
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }
            }

            Text(story.headline)
                .font(.system(.title3, design: .rounded, weight: .bold))
                .lineLimit(3)
                .foregroundStyle(state.isRead(story) ? .secondary : .primary)

            if !story.preview.isEmpty {
                Text(story.preview)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }

            HStack(spacing: -6) {
                ForEach(story.sourceNames.prefix(4), id: \.self) { source in
                    SourceAvatar(name: source, size: 24)
                        .overlay(Circle().strokeBorder(Color(.systemBackground), lineWidth: 1.5))
                }
                Text(story.sourceNames.prefix(3).joined(separator: " · "))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
                    .padding(.leading, 14)
            }
        }
        .padding(.vertical, 6)
    }
}
