import SwiftUI

/// Пейджинг-карусель главных сюжетов с фото
struct FeaturedCarousel: View {
    let stories: [Story]

    var body: some View {
        TabView {
            ForEach(stories) { story in
                NavigationLink(value: story) {
                    FeaturedSlide(story: story)
                }
                .buttonStyle(.plain)
            }
        }
        .tabViewStyle(.page(indexDisplayMode: stories.count > 1 ? .automatic : .never))
        .frame(height: 240)
    }
}

private struct FeaturedSlide: View {
    let story: Story

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            StoryImage(url: story.image)
                .frame(height: 224)
                .frame(maxWidth: .infinity)
                .clipped()

            LinearGradient(
                colors: [.clear, .black.opacity(0.15), .black.opacity(0.82)],
                startPoint: .top, endPoint: .bottom
            )

            VStack(alignment: .leading, spacing: 7) {
                HStack(spacing: 6) {
                    Text(story.categoryClean)
                        .font(.caption2.weight(.bold))
                        .padding(.horizontal, 9)
                        .padding(.vertical, 4)
                        .background(Theme.color(for: story.categoryClean).opacity(0.92),
                                    in: Capsule())
                        .foregroundStyle(.white)
                    if story.coverage > 1 {
                        Text(sourcesCountText(story.coverage))
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.white.opacity(0.85))
                    }
                }
                Text(story.headline)
                    .font(.system(.title3, design: .rounded, weight: .bold))
                    .foregroundStyle(.white)
                    .lineLimit(3)
                    .multilineTextAlignment(.leading)
                Text(story.sourceNames.prefix(3).joined(separator: " · "))
                    .font(.caption2)
                    .foregroundStyle(.white.opacity(0.7))
                    .lineLimit(1)
            }
            .padding(14)
        }
        .frame(height: 224)
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .padding(.horizontal, 16)
    }
}
