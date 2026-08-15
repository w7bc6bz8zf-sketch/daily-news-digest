package com.prizma.news

import org.jsoup.Jsoup
import org.jsoup.nodes.Element

/// Встроенная читалка: скачивает страницу целиком (со всеми редиректами,
/// в том числе из RSS-ссылок) и вычищает всё, кроме текста статьи.
object Reader {

    data class Article(val title: String, val paragraphs: List<String>)

    fun extract(html: String, baseUrl: String, fallbackTitle: String): Article {
        val doc = Jsoup.parse(html, baseUrl)
        doc.select(
            "script, style, nav, header, footer, aside, form, iframe, noscript, " +
            "svg, button, [role=navigation], [role=banner], [class*=subscribe], " +
            "[class*=related], [class*=promo], [class*=banner], [class*=comment]"
        ).remove()

        val title = doc.select("meta[property=og:title]").attr("content")
            .ifBlank { doc.title() }
            .ifBlank { fallbackTitle }

        // Ищем контейнер с максимальной суммарной длиной абзацев —
        // это и есть тело статьи
        val scores = HashMap<Element, Int>()
        for (p in doc.select("p")) {
            val len = p.text().length
            if (len < 60) continue
            val parent = p.parent() ?: continue
            scores[parent] = (scores[parent] ?: 0) + len
        }
        val best = scores.maxByOrNull { it.value }?.key

        val paragraphs = mutableListOf<String>()
        if (best != null) {
            for (el in best.children()) {
                when (el.tagName()) {
                    "p" -> {
                        val t = el.text().trim()
                        if (t.length > 25) paragraphs += t
                    }
                    "h2", "h3", "h4" -> {
                        val t = el.text().trim()
                        if (t.isNotEmpty() && t.length < 200) paragraphs += "## $t"
                    }
                    "ul", "ol" -> el.select("li").forEach { li ->
                        val t = li.text().trim()
                        if (t.isNotEmpty()) paragraphs += "• $t"
                    }
                    "blockquote" -> {
                        val t = el.text().trim()
                        if (t.length > 25) paragraphs += "« $t »"
                    }
                    else -> el.select("p").forEach { p ->
                        val t = p.text().trim()
                        if (t.length > 25 && paragraphs.lastOrNull() != t) paragraphs += t
                    }
                }
            }
        }
        // Фолбэк: все крупные абзацы страницы
        if (paragraphs.size < 2) {
            paragraphs.clear()
            doc.select("p").forEach {
                val t = it.text().trim()
                if (t.length > 60) paragraphs += t
            }
        }
        return Article(title.trim(), paragraphs)
    }
}
