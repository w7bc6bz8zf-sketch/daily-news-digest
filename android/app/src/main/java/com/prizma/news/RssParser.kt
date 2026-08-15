package com.prizma.news

import android.util.Xml
import org.xmlpull.v1.XmlPullParser
import java.io.StringReader
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

/// Парсер пользовательских RSS/Atom-лент: каждая запись становится
/// одноисточниковым сюжетом в категории «Мои источники».
object RssParser {

    fun parse(xml: String, fallbackName: String): List<Story> {
        val parser = Xml.newPullParser()
        parser.setInput(StringReader(xml))

        var channelTitle = fallbackName
        var channelTitleSet = false
        var inItem = false
        var current = ""
        var title = ""; var link = ""; var desc = ""; var pub: String? = null; var img = ""
        val stories = mutableListOf<Story>()

        var event = parser.eventType
        while (event != XmlPullParser.END_DOCUMENT) {
            when (event) {
                XmlPullParser.START_TAG -> {
                    current = parser.name?.lowercase() ?: ""
                    when (current) {
                        "item", "entry" -> {
                            inItem = true; title = ""; link = ""; desc = ""; pub = null; img = ""
                        }
                        "enclosure", "content", "thumbnail" -> if (inItem && img.isEmpty()) {
                            parser.getAttributeValue(null, "url")?.let {
                                if (it.startsWith("http")) img = it
                            }
                        }
                        "link" -> if (inItem && link.isEmpty()) {
                            // Atom: <link href="..."/>
                            parser.getAttributeValue(null, "href")?.let { link = it }
                        }
                    }
                }
                XmlPullParser.TEXT, XmlPullParser.CDSECT -> {
                    val text = parser.text?.trim().orEmpty()
                    if (text.isNotEmpty()) {
                        if (!inItem && current == "title" && !channelTitleSet) {
                            channelTitle = stripHtml(text).take(40)
                            channelTitleSet = true
                        } else if (inItem) {
                            when (current) {
                                "title" -> title += text
                                "link" -> if (link.isEmpty()) link = text
                                "description", "summary" ->
                                    if (desc.length < 100) desc = stripHtml(text)
                                "pubdate", "published", "date" -> pub = text
                            }
                        }
                    }
                }
                XmlPullParser.END_TAG -> {
                    val name = parser.name?.lowercase() ?: ""
                    if (name == "item" || name == "entry") {
                        inItem = false
                        if (title.isNotBlank()) {
                            val cleanTitle = stripHtml(title)
                            val lang = detectLang(cleanTitle)
                            stories += Story(
                                id = link.ifEmpty { cleanTitle },
                                category = "Мои источники",
                                lang = lang,
                                headline = cleanTitle,
                                coverage = 1,
                                singleSource = true,
                                image = img,
                                publishedAt = parseRssDate(pub),
                                perspectives = listOf(
                                    Perspective(
                                        source = channelTitle,
                                        lang = lang,
                                        headline = cleanTitle,
                                        excerpt = desc.take(400),
                                        url = link,
                                    )
                                ),
                            )
                        }
                    }
                    current = ""
                }
            }
            event = parser.next()
        }
        return stories.take(15)
    }

    fun stripHtml(raw: String): String =
        raw.replace(Regex("<[^>]+>"), " ")
            .replace(Regex("&[a-z#0-9]+;"), " ")
            .replace(Regex("\\s+"), " ")
            .trim()

    fun detectLang(text: String): String {
        val letters = text.filter { it.isLetter() }
        if (letters.isEmpty()) return "ru"
        val cyr = letters.count { it in 'а'..'я' || it in 'А'..'Я' || it == 'ё' || it == 'Ё' }
        return if (cyr.toDouble() / letters.length > 0.3) "ru" else "en"
    }

    private fun parseRssDate(raw: String?): String? {
        if (raw.isNullOrBlank()) return null
        return runCatching {
            ZonedDateTime.parse(raw, DateTimeFormatter.RFC_1123_DATE_TIME)
                .toOffsetDateTime().toString()
        }.getOrElse {
            runCatching { ZonedDateTime.parse(raw).toOffsetDateTime().toString() }.getOrNull()
        }
    }
}
