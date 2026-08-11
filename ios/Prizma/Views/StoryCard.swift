import SwiftUI

struct StoryCard: View {
    @EnvironmentObject private var state: AppState
    let story: Story

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    Label(story.categoryClean, systemImage: NewsCategory.icon(for: story.categoryClean))
                        .font(.caption2.weight(.semibold))
                        .foregroundStyle(.indigo)
                    if let date = story.publishedDate {
                        Text(DateParser.relative(date))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }

                Text(story.headline)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(3)
                    .foregroundStyle(state.isRead(story) ? .secondary : .primary)

                if !story.leadExcerpt.isEmpty {
                    Text(story.leadExcerpt)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(2)
                }

                HStack(spacing: 6) {
                    if story.coverage > 1 {
                        Text(sourcesCountText(story.coverage))
                            .font(.caption2.weight(.semibold))
                            .padding(.horizontal, 7)
                            .padding(.vertical, 3)
                            .background(Color.indigo.opacity(0.14), in: Capsule())
                            .foregroundStyle(.indigo)
                    }
                    Text(story.sourceNames.prefix(3).joined(separator: " · "))
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }

            if !story.image.isEmpty, let url = URL(string: story.image) {
                AsyncImage(url: url) { phase in
                    switch phase {
                    case .success(let image):
                        image.resizable().aspectRatio(contentMode: .fill)
                    default:
                        Color(.secondarySystemBackground)
                    }
                }
                .frame(width: 84, height: 84)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            }
        }
        .padding(.vertical, 4)
    }
}
