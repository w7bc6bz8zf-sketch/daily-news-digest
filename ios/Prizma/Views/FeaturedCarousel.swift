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
        .tabViewStyle(.page(indexDisplayMode: .never))
        .frame(height: 252)
    }
}

// Текст не накладывается на фото: многие издания впечатывают заголовок
// прямо в картинку, поэтому текстовая часть живёт в подложке под изображением.
private struct FeaturedSlide: View {
    let story: Story

    var body: some View {
        VStack(spacing: 0) {
            StoryImage(url: story.image)
                .frame(height: 136)
                .frame(maxWidth: .infinity)
                .clipped()

            VStack(alignment: .leading, spacing: 6) {
                HStack(spacing: 6) {
                    CategoryPill(category: story.categoryClean)
                    if story.coverage > 1 {
                        Text(sourcesCountText(story.coverage))
                            .font(.caption2.weight(.semibold))
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    if let date = story.publishedDate {
                        Text(DateParser.relative(date))
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
                Text(story.headline)
                    .font(.system(.headline, design: .rounded, weight: .bold))
                    .lineLimit(2)
                    .multilineTextAlignment(.leading)
                    .foregroundStyle(.primary)
                Text(story.sourceNames.prefix(3).joined(separator: " · "))
                    .font(.caption2)
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
            }
            .padding(12)
            .frame(maxWidth: .infinity, minHeight: 104, alignment: .topLeading)
            .background(Theme.card)
        }
        .clipShape(RoundedRectangle(cornerRadius: 18))
        .overlay(
            RoundedRectangle(cornerRadius: 18)
                .strokeBorder(Theme.cardStroke, lineWidth: 1)
        )
        .padding(.horizontal, 16)
    }
}
