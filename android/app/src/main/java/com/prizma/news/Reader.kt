package com.prizma.news

import org.jsoup.Jsoup
import org.jsoup.nodes.Document
import org.jsoup.nodes.Element

/// Встроенная читалка: очищает страницу до текста статьи.
///
/// Важно: никаких удалений по подстрокам классов ([class*=comment] и т.п.) —
/// контейнер статьи запросто называется «comments-opened», и такая «чистка»
/// сносила весь текст. Удаляем только заведомо нетекстовые теги, а мусор
/// отсекаем выбором контейнера с максимумом абзацев.
object Reader {

    data class Article(val title: String, val paragraphs: List<String>)

    private val BLOCK_TAGS = setOf("p", "div", "ul", "ol", "blockquote", "section", "article", "table")

    fun extract(html: String, baseUrl: String, fallbackTitle: String): Article {
        val doc = Jsoup.parse(html, baseUrl)
        doc.select("script, style, noscript, iframe, svg, form, button, nav, video, audio").remove()

        // Заголовок из RSS точнее, чем og:title (сайты часто ставят общий)
        val title = fallbackTitle.ifBlank {
            doc.select("meta[property=og:title]").attr("content").ifBlank { doc.title() }
        }

        // Скоуп: тег <article>, если есть — иначе вся страница
        val scope: Element = doc.selectFirst("article") ?: doc.body() ?: doc

        // План А: контейнер с максимальной суммой длинных <p>
        var paragraphs = byParagraphMass(scope)
        // План Б: «листовые» блоки скоупа — работает и на div-вёрстке
        if (paragraphs.size < 2) paragraphs = leafBlocks(scope)
        // План В: то же по всему документу
        if (paragraphs.size < 2 && scope !== doc.body()) {
            paragraphs = leafBlocks(doc.body() ?: doc)
        }

        return Article(title.trim(), paragraphs.take(200))
    }

    private fun byParagraphMass(scope: Element): List<String> {
        val scores = HashMap<Element, Int>()
        for (p in scope.select("p")) {
            val len = p.text().length
            if (len < 60) continue
            val parent = p.parent() ?: continue
            scores[parent] = (scores[parent] ?: 0) + len
        }
        val best = scores.maxByOrNull { it.value }?.key ?: return emptyList()

        val out = mutableListOf<String>()
        for (el in best.children()) {
            when (el.tagName()) {
                "p" -> {
                    val t = el.text().trim()
                    if (t.length > 25) out += t
                }
                "h2", "h3", "h4" -> {
                    val t = el.text().trim()
                    if (t.isNotEmpty() && t.length < 200) out += "## $t"
                }
                "ul", "ol" -> el.select("li").forEach { li ->
                    val t = li.text().trim()
                    if (t.isNotEmpty()) out += "• $t"
                }
                "blockquote" -> {
                    val t = el.text().trim()
                    if (t.length > 25) out += "« $t »"
                }
                else -> el.select("p").forEach { p ->
                    val t = p.text().trim()
                    if (t.length > 25 && out.lastOrNull() != t) out += t
                }
            }
        }
        return dedupe(out)
    }

    /// «Листовые» блоки: элементы с длинным собственным текстом, внутри
    /// которых нет других блочных элементов. Ловит статьи на div-вёрстке.
    private fun leafBlocks(scope: Element): List<String> {
        val out = mutableListOf<String>()
        for (el in scope.select("p, div, li, blockquote, h2, h3")) {
            if (el.children().any { it.tagName() in BLOCK_TAGS }) continue
            val t = el.text().trim()
            if (t.length < 80) continue
            out += if (el.tagName() == "h2" || el.tagName() == "h3") "## $t" else t
        }
        return dedupe(out)
    }

    private fun dedupe(list: List<String>): List<String> {
        val seen = HashSet<String>()
        return list.filter { seen.add(it) }
    }
}
