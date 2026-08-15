import SwiftUI

// Дизайн-система «Призмы».
// Метафора бренда: призма раскладывает свет на спектр — как приложение
// раскладывает новость на перспективы разных изданий.

enum Theme {
    /// Фирменный акцент: в тёмной теме ярче, чтобы светился на глубоком фоне
    static let accent = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0.58, green: 0.52, blue: 1.00, alpha: 1)
            : UIColor(red: 0.40, green: 0.35, blue: 0.90, alpha: 1)
    })

    // Поверхности: тёмная тема — фирменный «космос», светлая — мягкая лаванда
    static let bgTop = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0.055, green: 0.045, blue: 0.130, alpha: 1)
            : UIColor(red: 0.965, green: 0.955, blue: 0.995, alpha: 1)
    })
    static let bgBottom = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0.110, green: 0.080, blue: 0.215, alpha: 1)
            : UIColor(red: 0.925, green: 0.925, blue: 0.985, alpha: 1)
    })
    static let card = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0.140, green: 0.115, blue: 0.245, alpha: 1)
            : UIColor.white
    })
    static let cardStroke = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(white: 1, alpha: 0.09)
            : UIColor(white: 0, alpha: 0.05)
    })
    static let chip = Color(uiColor: UIColor { trait in
        trait.userInterfaceStyle == .dark
            ? UIColor(red: 0.185, green: 0.160, blue: 0.310, alpha: 1)
            : UIColor(red: 0.905, green: 0.900, blue: 0.960, alpha: 1)
    })

    /// Градиентный фон всех экранов
    static var background: some View {
        LinearGradient(colors: [bgTop, bgBottom], startPoint: .top, endPoint: .bottom)
            .ignoresSafeArea()
    }

    /// Спектральный градиент призмы — для выделенных элементов
    static let prism = LinearGradient(
        colors: [
            Color(red: 0.40, green: 0.35, blue: 0.90),
            Color(red: 0.62, green: 0.32, blue: 0.87),
            Color(red: 0.90, green: 0.35, blue: 0.60),
        ],
        startPoint: .topLeading, endPoint: .bottomTrailing
    )

    /// Цветовое кодирование категорий
    private static let categoryColors: [String: Color] = [
        "Мир":        .blue,
        "Россия":     .red,
        "Экономика":  .green,
        "Бизнес":     .brown,
        "Технологии": .indigo,
        "Наука":      .teal,
        "Спорт":      .orange,
        "Культура":   .pink,
    ]

    static func color(for category: String) -> Color {
        categoryColors[category] ?? .gray
    }
}

// MARK: - Карточка-поверхность

struct PrizmaCard: ViewModifier {
    var padding: CGFloat

    func body(content: Content) -> some View {
        content
            .padding(padding)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.card, in: RoundedRectangle(cornerRadius: 18))
            .overlay(
                RoundedRectangle(cornerRadius: 18)
                    .strokeBorder(Theme.cardStroke, lineWidth: 1)
            )
    }
}

extension View {
    func prizmaCard(padding: CGFloat = 14) -> some View {
        modifier(PrizmaCard(padding: padding))
    }
}

// MARK: - Переиспользуемые элементы

/// Плашка категории в цвете категории
struct CategoryPill: View {
    let category: String

    var body: some View {
        Label(category, systemImage: NewsCategory.icon(for: category))
            .font(.caption2.weight(.bold))
            .padding(.horizontal, 9)
            .padding(.vertical, 4)
            .background(Theme.color(for: category).opacity(0.14), in: Capsule())
            .foregroundStyle(Theme.color(for: category))
    }
}

/// Плашка «N источников»
struct CoveragePill: View {
    let coverage: Int

    var body: some View {
        Label(sourcesCountText(coverage), systemImage: "square.stack.3d.up.fill")
            .font(.caption2.weight(.semibold))
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Theme.accent.opacity(0.12), in: Capsule())
            .foregroundStyle(Theme.accent)
    }
}

/// Круглый аватар издания с первой буквой на спектральном градиенте
struct SourceAvatar: View {
    let name: String
    var size: CGFloat = 28

    var body: some View {
        Text(String(name.prefix(1)).uppercased())
            .font(.system(size: size * 0.45, weight: .bold, design: .rounded))
            .foregroundStyle(.white)
            .frame(width: size, height: size)
            .background(Theme.prism, in: Circle())
    }
}

/// Картинка сюжета с плейсхолдером
struct StoryImage: View {
    let url: String

    var body: some View {
        if let imageURL = URL(string: url), !url.isEmpty {
            AsyncImage(url: imageURL) { phase in
                switch phase {
                case .success(let image):
                    image.resizable().aspectRatio(contentMode: .fill)
                default:
                    ZStack {
                        Rectangle().fill(Theme.accent.opacity(0.08))
                        Image(systemName: "newspaper")
                            .font(.title2)
                            .foregroundStyle(Theme.accent.opacity(0.4))
                    }
                }
            }
        }
    }
}
