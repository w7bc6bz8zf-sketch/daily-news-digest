package com.prizma.news

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color

// Дизайн-система «Призмы»: тёмный «космос» с индиго-градиентом,
// спектральный градиент призмы на акцентах, цветные категории.

object Prizma {
    val accent = Color(0xFF948AFF)
    val bgTop = Color(0xFF0E0B21)
    val bgBottom = Color(0xFF1C1437)
    val card = Color(0xFF241D3E)
    val cardStroke = Color(0x17FFFFFF)
    val chip = Color(0xFF2F284F)
    val textSecondary = Color(0xFFB3AECB)
    val textTertiary = Color(0xFF7C7695)

    val prism = Brush.linearGradient(
        listOf(Color(0xFF6659E6), Color(0xFF9E52DE), Color(0xFFE55999))
    )

    val backgroundBrush = Brush.verticalGradient(listOf(bgTop, bgBottom))

    private val categoryColors = mapOf(
        "Мир" to Color(0xFF5B9BFF),
        "Россия" to Color(0xFFFF6B6B),
        "Экономика" to Color(0xFF51C878),
        "Бизнес" to Color(0xFFC79A63),
        "Технологии" to Color(0xFF948AFF),
        "Наука" to Color(0xFF4FD8C8),
        "Спорт" to Color(0xFFFF9E4F),
        "Культура" to Color(0xFFFF7BC1),
    )

    fun categoryColor(category: String): Color =
        categoryColors[category] ?: Color(0xFF9A94B8)
}

private val darkScheme = darkColorScheme(
    primary = Prizma.accent,
    background = Prizma.bgTop,
    surface = Prizma.card,
    surfaceVariant = Prizma.chip,
    onPrimary = Color.White,
    onBackground = Color(0xFFF2F0FA),
    onSurface = Color(0xFFF2F0FA),
)

@Composable
fun PrizmaTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = darkScheme, content = content)
}
