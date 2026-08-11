import Foundation

// Компилируется на CI вместе с ios/Prizma/Models.swift:
//   swiftc -parse-as-library -o decode_test ios/Prizma/Models.swift ci/DecodeTest.swift
// Проверяет декодирование реального news_data.json, совместимость со старым
// форматом ленты, roundtrip закладок и утилиты.

@main
struct DecodeTest {
    static var failures = 0

    static func check(_ cond: Bool, _ msg: String) {
        if cond { print("PASS \(msg)") } else { failures += 1; print("FAIL \(msg)") }
    }

    static func main() throws {
        // 1. Реальный news_data.json из репозитория
        let path = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "news_data.json"
        let data = try Data(contentsOf: URL(fileURLWithPath: path))
        let digest = try JSONDecoder().decode(NewsDigest.self, from: data)
        check(!digest.stories.isEmpty, "news_data.json: декодировано \(digest.stories.count) сюжетов")
        if let first = digest.stories.first {
            check(!first.headline.isEmpty, "headline не пустой")
            check(!first.perspectives.isEmpty, "перспективы присутствуют")
            check(!first.id.isEmpty, "id присутствует")
        }

        // 2. Новый формат (вывод переписанного collect_news.py)
        let newJSON = """
        {"collected_at":"2026-08-11T05:00:00.123456+00:00","story_count":1,"stories":[{"id":"abc123","category":"Экономика","lang":"ru","headline":"ЦБ сохранил ставку","headline_en":"","coverage":3,"single_source":false,"image":"https://example.com/i.jpg","published_at":"2026-08-11T04:00:00+00:00","score":20.5,"perspectives":[{"source":"РБК","lang":"ru","headline":"ЦБ сохранил ставку","excerpt":"Текст","url":"https://rbc.ru/1","published_at":"2026-08-11T04:00:00+00:00"}]}]}
        """
        let d2 = try JSONDecoder().decode(NewsDigest.self, from: Data(newJSON.utf8))
        check(d2.stories[0].id == "abc123", "новый формат: id")
        check(d2.stories[0].publishedDate != nil, "новый формат: published_at распарсен")
        check(DateParser.parse(d2.collectedAt) != nil, "collected_at с микросекундами распарсен")

        // 3. Старый формат (без id/lang/headline) — обратная совместимость
        let oldJSON = """
        {"collected_at":"2026-08-10T03:35:22.581371+00:00","story_count":1,"stories":[{"category":"🌍 World","headline_en":"Test story","coverage":2,"perspectives":[{"source":"BBC","lang":"en","headline":"Test story","excerpt":"Body","url":"https://bbc.com/x"}]}]}
        """
        let d3 = try JSONDecoder().decode(NewsDigest.self, from: Data(oldJSON.utf8))
        check(d3.stories[0].headline == "Test story", "старый формат: headline берётся из headline_en")
        check(d3.stories[0].id == "https://bbc.com/x", "старый формат: id из url перспективы")
        check(d3.stories[0].categoryClean == "World", "старый формат: эмодзи убраны из категории")
        check(d3.stories[0].lang == "en", "старый формат: язык определён по заголовку")

        // 4. Roundtrip кодирования — так хранятся закладки
        let encoded = try JSONEncoder().encode(digest.stories)
        let decoded = try JSONDecoder().decode([Story].self, from: encoded)
        check(decoded.count == digest.stories.count, "закладки: encode/decode без потерь")
        check(decoded.first?.headline == digest.stories.first?.headline, "закладки: headline сохранился")

        // 5. Утилиты
        check(sourcesCountText(1) == "1 источник", "плюрализация: 1 источник")
        check(sourcesCountText(3) == "3 источника", "плюрализация: 3 источника")
        check(sourcesCountText(11) == "11 источников", "плюрализация: 11 источников")
        check(sourcesCountText(21) == "21 источник", "плюрализация: 21 источник")
        check("Привет".containsCyrillic && !"Hello".containsCyrillic, "определение кириллицы")

        // 6. Персонализация «Для вас»
        func makeStory(_ headline: String, category: String, source: String, url: String) throws -> Story {
            let json = """
            {"id":"\(url)","category":"\(category)","lang":"ru","headline":"\(headline)","headline_en":"","coverage":2,"single_source":false,"image":"","perspectives":[{"source":"\(source)","lang":"ru","headline":"\(headline)","excerpt":"Текст","url":"https://x.ru/\(url)"}]}
            """
            return try JSONDecoder().decode(Story.self, from: Data(json.utf8))
        }
        let tech = try makeStory("Новый чип для ИИ представлен", category: "Технологии", source: "Habr", url: "a")
        let sport = try makeStory("Футбольный матч завершился", category: "Спорт", source: "Sports.ru", url: "b")
        let crypto = try makeStory("Биткоин обновил максимум, криптовалюты растут", category: "Экономика", source: "РБК", url: "c")

        var profile = InterestProfile()
        profile.registerRead(category: "Технологии", sources: ["Habr"])
        profile.registerRead(category: "Технологии", sources: ["Habr"])
        check(profile.categoryAffinity("Технологии") == 1.0, "профиль: аффинити категории")

        let ranked = Personalization.rank(stories: [sport, tech], profile: profile,
                                          topics: [], readIDs: [])
        check(ranked.first?.id == tech.id, "«Для вас»: любимая категория поднимается выше")

        let topics = Personalization.matchedTopics(in: crypto, topics: ["Криптовалюты", "Футбол"])
        check(topics == ["Криптовалюты"], "темы: находится совпадение по ключевому слову")

        let rankedTopics = Personalization.rank(stories: [tech, sport, crypto], profile: profile,
                                                topics: ["криптовалюты"], readIDs: [])
        check(rankedTopics.first?.id == crypto.id, "«Для вас»: подписка на тему сильнее аффинити")

        let rankedRead = Personalization.rank(stories: [tech, sport], profile: profile,
                                              topics: [], readIDs: [tech.id])
        check(rankedRead.first?.id == sport.id, "«Для вас»: прочитанное опускается вниз")

        if failures > 0 {
            print("ПРОВАЛЕНО: \(failures)")
            exit(1)
        }
        print("Все проверки пройдены")
    }
}
