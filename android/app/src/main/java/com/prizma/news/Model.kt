package com.prizma.news

import android.text.format.DateUtils
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import java.time.OffsetDateTime

@Serializable
data class NewsDigest(
    @SerialName("collected_at") val collectedAt: String? = null,
    @SerialName("story_count") val storyCount: Int = 0,
    val stories: List<Story> = emptyList(),
)

@Serializable
data class Story(
    val id: String = "",
    val category: String = "Новости",
    val lang: String = "ru",
    val headline: String = "",
    @SerialName("headline_en") val headlineEn: String = "",
    val summary: List<String> = emptyList(),
    val coverage: Int = 1,
    @SerialName("single_source") val singleSource: Boolean = false,
    val image: String = "",
    @SerialName("published_at") val publishedAt: String? = null,
    val perspectives: List<Perspective> = emptyList(),
) {
    val preview: String
        get() = summary.firstOrNull() ?: perspectives.firstOrNull()?.excerpt ?: ""

    val sourceNames: List<String>
        get() = perspectives.map { it.source }
}

@Serializable
data class Perspective(
    val source: String = "",
    val lang: String = "ru",
    val headline: String = "",
    val excerpt: String = "",
    val url: String = "",
    @SerialName("published_at") val publishedAt: String? = null,
    // Полный HTML статьи из RSS (content:encoded) — читалка показывает его
    // без похода на сайт. В основной ленте поля нет — остаётся пустым.
    val content: String = "",
)

fun relativeTime(iso: String?): String {
    if (iso.isNullOrEmpty()) return ""
    return try {
        val millis = OffsetDateTime.parse(iso).toInstant().toEpochMilli()
        DateUtils.getRelativeTimeSpanString(
            millis, System.currentTimeMillis(), DateUtils.MINUTE_IN_MILLIS
        ).toString()
    } catch (e: Exception) {
        ""
    }
}

fun sourcesCountText(n: Int): String {
    val mod10 = n % 10
    val mod100 = n % 100
    val word = when {
        mod10 == 1 && mod100 != 11 -> "источник"
        mod10 in 2..4 && mod100 !in 12..14 -> "источника"
        else -> "источников"
    }
    return "$n $word"
}
