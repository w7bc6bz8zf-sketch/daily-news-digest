import SwiftUI

/// Первый запуск: знакомство с приложением и выбор интересов
struct OnboardingView: View {
    @EnvironmentObject private var state: AppState

    private let topics = [
        "Искусственный интеллект", "Криптовалюты", "Санкции", "Ключевая ставка",
        "Недвижимость", "Футбол", "Кино", "Илон Маск", "Автопром", "Космос",
        "Стартапы", "Энергетика",
    ]

    var body: some View {
        ScrollView {
            VStack(spacing: 22) {
                ZStack {
                    Circle()
                        .fill(Theme.prism)
                        .frame(width: 92, height: 92)
                    Image(systemName: "triangle.fill")
                        .font(.system(size: 38, weight: .bold))
                        .foregroundStyle(.white)
                }
                .padding(.top, 40)

                VStack(spacing: 8) {
                    Text("Призма")
                        .font(.system(size: 40, weight: .bold, design: .rounded))
                    Text("Одна новость — все точки зрения.\n80+ изданий, русскоязычные в приоритете.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }

                VStack(alignment: .leading, spacing: 12) {
                    Text("Что вам интересно?")
                        .font(.system(.headline, design: .rounded))
                    Text("Сюжеты по этим темам будут выше в ленте «Для вас». Можно изменить в настройках.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 150), spacing: 8)],
                              spacing: 8) {
                        ForEach(topics, id: \.self) { topic in
                            topicChip(topic)
                        }
                    }
                }
                .prizmaCard(padding: 16)

                Toggle(isOn: $state.russianOnly) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Только русскоязычные сюжеты")
                            .font(.subheadline.weight(.medium))
                        Text("Мировые новости с переводом останутся")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .prizmaCard(padding: 16)

                Button {
                    withAnimation { state.hasOnboarded = true }
                } label: {
                    Text("Начать читать")
                        .font(.system(.headline, design: .rounded))
                        .foregroundStyle(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 15)
                        .background(Theme.prism, in: Capsule())
                }
                .padding(.bottom, 24)
            }
            .padding(.horizontal, 22)
        }
        .background(Theme.background)
    }

    private func topicChip(_ topic: String) -> some View {
        let isOn = state.followedTopics.contains {
            $0.caseInsensitiveCompare(topic) == .orderedSame
        }
        return Button {
            if isOn { state.unfollowTopic(topic) } else { state.followTopic(topic) }
        } label: {
            HStack(spacing: 5) {
                Image(systemName: isOn ? "checkmark.circle.fill" : "plus.circle")
                    .font(.caption)
                Text(topic)
                    .font(.footnote.weight(.medium))
                    .lineLimit(1)
                    .minimumScaleFactor(0.8)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 9)
            .padding(.horizontal, 6)
            .background {
                if isOn {
                    Capsule().fill(Theme.prism)
                } else {
                    Capsule().fill(Theme.chip)
                }
            }
            .foregroundStyle(isOn ? .white : .primary)
        }
        .buttonStyle(.plain)
    }
}

#Preview {
    OnboardingView().environmentObject(AppState())
}
