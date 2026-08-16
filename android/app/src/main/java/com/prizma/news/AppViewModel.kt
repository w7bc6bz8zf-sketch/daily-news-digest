package com.prizma.news

import android.app.Application
import android.content.Context
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.builtins.ListSerializer
import kotlinx.serialization.builtins.MapSerializer
import kotlinx.serialization.builtins.serializer
import kotlinx.serialization.json.Json
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File

class AppViewModel(app: Application) : AndroidViewModel(app) {

    companion object {
        const val FEED_URL =
            "https://raw.githubusercontent.com/w7bc6bz8zf-sketch/daily-news-digest/main/news_data.json"
    }

    private val prefs = app.getSharedPreferences("prizma", Context.MODE_PRIVATE)
    private val cacheFile = File(app.cacheDir, "news_cache.json")
    private val json = Json { ignoreUnknownKeys = true }
    private val http = OkHttpClient()

    var stories by mutableStateOf<List<Story>>(emptyList()); private set
    var isLoading by mutableStateOf(false); private set
    var error by mutableStateOf<String?>(null); private set
    var collectedAt by mutableStateOf<String?>(null); private set

    var searchText by mutableStateOf("")
    var selectedCategory by mutableStateOf<String?>(null)

    var forYou by mutableStateOf(prefs.getBoolean("forYou", true))
        private set
    var russianOnly by mutableStateOf(prefs.getBoolean("russianOnly", false))
        private set
    var readIds by mutableStateOf<Set<String>>(prefs.getStringSet("readIds", emptySet())!!.toSet())
        private set
    var topics by mutableStateOf<List<String>>(loadStringList("topics"))
        private set
    var bookmarks by mutableStateOf<List<Story>>(loadBookmarks())
        private set
    var customFeeds by mutableStateOf<List<String>>(loadStringList("customFeeds"))
        private set
    private var customStories by mutableStateOf<List<Story>>(emptyList())
    private var categoryWeights: MutableMap<String, Double> = loadWeights()

    // MARK: загрузка ленты

    fun loadInitial() {
        if (cacheFile.exists()) {
            runCatching { applyDigest(json.decodeFromString<NewsDigest>(cacheFile.readText())) }
        }
        refresh()
    }

    var customFeedStatus by mutableStateOf<Map<String, String>>(emptyMap())
        private set

    fun refresh() {
        viewModelScope.launch { refreshAndWait() }
    }

    /// Для pull-to-refresh: возвращается только после полного окончания
    /// загрузки, чтобы индикатор гарантированно закрылся
    suspend fun refreshAndWait() {
        if (isLoading) {
            while (isLoading) kotlinx.coroutines.delay(100)
            return
        }
        isLoading = true
        error = null
        try {
            withContext(Dispatchers.IO) {
                try {
                    val body = fetch(FEED_URL)
                    val digest = json.decodeFromString<NewsDigest>(body)
                    cacheFile.writeText(body)
                    withContext(Dispatchers.Main) { applyDigest(digest) }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        if (stories.isEmpty()) error = "Не удалось загрузить новости. Проверьте соединение."
                    }
                }
                // Пользовательские RSS-ленты — каждая независимо, со статусом
                val custom = mutableListOf<Story>()
                val status = mutableMapOf<String, String>()
                for (feedUrl in customFeeds) {
                    try {
                        val (items, note) = loadCustomFeed(feedUrl)
                        custom += items
                        status[feedUrl] = if (items.isEmpty())
                            "RSS не найден по этому адресу"
                        else
                            "✓ записей: ${items.size}$note"
                    } catch (e: Exception) {
                        status[feedUrl] = "ошибка: ${e.message?.take(60) ?: e.javaClass.simpleName}"
                    }
                }
                withContext(Dispatchers.Main) {
                    customStories = custom
                    customFeedStatus = status
                }
            }
        } finally {
            isLoading = false   // гарантированно, что бы ни случилось
        }
    }

    /// Загрузка пользовательской ленты. Если по адресу оказалась обычная
    /// страница сайта — ищем в её HTML ссылку на RSS и берём её.
    private fun loadCustomFeed(feedUrl: String): Pair<List<Story>, String> {
        val body = fetch(feedUrl)
        var items = RssParser.parse(body, feedUrl)
        if (items.isNotEmpty()) return items to ""

        val discovered =
            Regex("""<link[^>]+type=["']application/(?:rss|atom)\+xml["'][^>]*href=["']([^"']+)""",
                  RegexOption.IGNORE_CASE).find(body)?.groupValues?.get(1)
                ?: Regex("""<link[^>]+href=["']([^"']+)["'][^>]*type=["']application/(?:rss|atom)\+xml""",
                         RegexOption.IGNORE_CASE).find(body)?.groupValues?.get(1)
        if (discovered != null) {
            val resolved = java.net.URL(java.net.URL(feedUrl), discovered).toString()
            items = RssParser.parse(fetch(resolved), resolved)
            if (items.isNotEmpty()) return items to " (RSS найден автоматически)"
        }
        return emptyList<Story>() to ""
    }

    fun fetch(url: String): String {
        val request = Request.Builder().url(url)
            .header(
                "User-Agent",
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 " +
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"
            )
            .header("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .header("Accept-Language", "ru-RU,ru;q=0.9,en;q=0.7")
            .build()
        return http.newCall(request).execute().use { resp ->
            if (!resp.isSuccessful) throw RuntimeException("HTTP ${resp.code}")
            resp.body!!.string()
        }
    }

    private fun applyDigest(digest: NewsDigest) {
        stories = digest.stories
        collectedAt = digest.collectedAt
    }

    // MARK: фильтрация и «Для вас»

    val availableCategories: List<String>
        get() = (stories + customStories).map { it.category }.distinct()
            .sortedByDescending { it == "Мои источники" }   // свои ленты — первым чипом

    val displayedStories: List<Story>
        get() {
            var list = (stories + customStories).filter { story ->
                if (russianOnly && story.lang != "ru") return@filter false
                selectedCategory?.let { if (story.category != it) return@filter false }
                if (searchText.isNotBlank()) {
                    val haystack = (story.headline + " " + story.headlineEn + " " + story.preview)
                        .lowercase()
                    if (!haystack.contains(searchText.trim().lowercase())) return@filter false
                }
                true
            }
            if (forYou) {
                val total = categoryWeights.values.sum()
                list = list.withIndex().sortedByDescending { (idx, story) ->
                    var score = -idx * 0.1
                    score += matchedTopics(story).size * 6.0
                    if (story.category == "Мои источники") score += 2.0
                    if (total > 0) score += (categoryWeights[story.category] ?: 0.0) / total * 3.0
                    if (readIds.contains(story.id)) score -= 12.0
                    score
                }.map { it.value }
            }
            return list
        }

    /// Для вкладки «Мои источники»: записи пользовательских лент, свежие сверху
    val customStoriesSorted: List<Story>
        get() = customStories.sortedByDescending { it.publishedAt ?: "" }

    fun matchedTopics(story: Story): List<String> {
        if (topics.isEmpty()) return emptyList()
        val haystack = (story.headline + " " + story.headlineEn + " " + story.preview).lowercase()
        return topics.filter { it.isNotBlank() && haystack.contains(it.trim().lowercase()) }
    }

    // MARK: действия

    fun setFeedMode(forYouMode: Boolean) {
        forYou = forYouMode
        prefs.edit().putBoolean("forYou", forYouMode).apply()
    }

    fun setRussianOnlyMode(value: Boolean) {
        russianOnly = value
        prefs.edit().putBoolean("russianOnly", value).apply()
    }

    fun markRead(story: Story) {
        if (readIds.contains(story.id)) return
        readIds = readIds + story.id
        prefs.edit().putStringSet("readIds", readIds).apply()
        categoryWeights[story.category] = (categoryWeights[story.category] ?: 0.0) + 1.0
        saveWeights()
    }

    fun isRead(story: Story) = readIds.contains(story.id)

    fun resetRead() {
        readIds = emptySet()
        prefs.edit().putStringSet("readIds", readIds).apply()
    }

    fun isBookmarked(story: Story) = bookmarks.any { it.id == story.id }

    fun toggleBookmark(story: Story) {
        bookmarks = if (isBookmarked(story)) {
            bookmarks.filterNot { it.id == story.id }
        } else {
            listOf(story) + bookmarks
        }
        prefs.edit().putString(
            "bookmarks", json.encodeToString(ListSerializer(Story.serializer()), bookmarks)
        ).apply()
    }

    fun followTopic(raw: String) {
        val topic = raw.trim()
        if (topic.isEmpty() || topics.any { it.equals(topic, ignoreCase = true) }) return
        topics = topics + topic
        saveStringList("topics", topics)
    }

    fun unfollowTopic(topic: String) {
        topics = topics.filterNot { it == topic }
        saveStringList("topics", topics)
    }

    fun addCustomFeed(raw: String) {
        var url = raw.trim()
        if (url.isEmpty()) return
        if (!url.startsWith("http")) url = "https://$url"
        if (customFeeds.any { it.equals(url, ignoreCase = true) }) return
        customFeeds = customFeeds + url
        saveStringList("customFeeds", customFeeds)
        refresh()
    }

    fun removeCustomFeed(url: String) {
        customFeeds = customFeeds.filterNot { it == url }
        saveStringList("customFeeds", customFeeds)
        customStories = emptyList()   // пересоберётся в refresh() из оставшихся лент
        refresh()
    }

    // MARK: persistence

    private fun loadBookmarks(): List<Story> = runCatching {
        json.decodeFromString(
            ListSerializer(Story.serializer()), prefs.getString("bookmarks", null) ?: "[]"
        )
    }.getOrDefault(emptyList())

    private fun loadStringList(key: String): List<String> = runCatching {
        json.decodeFromString(
            ListSerializer(String.serializer()), prefs.getString(key, null) ?: "[]"
        )
    }.getOrDefault(emptyList())

    private fun saveStringList(key: String, value: List<String>) {
        prefs.edit().putString(
            key, json.encodeToString(ListSerializer(String.serializer()), value)
        ).apply()
    }

    private fun loadWeights(): MutableMap<String, Double> = runCatching {
        json.decodeFromString(
            MapSerializer(String.serializer(), Double.serializer()),
            prefs.getString("categoryWeights", null) ?: "{}"
        ).toMutableMap()
    }.getOrDefault(mutableMapOf())

    private fun saveWeights() {
        prefs.edit().putString(
            "categoryWeights",
            json.encodeToString(
                MapSerializer(String.serializer(), Double.serializer()), categoryWeights
            )
        ).apply()
    }
}
