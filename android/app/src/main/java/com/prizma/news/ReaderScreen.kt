package com.prizma.news

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.ExitToApp
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/// Встроенная читалка: страница скачивается целиком и очищается до текста
@Composable
fun ReaderScreen(
    perspective: Perspective,
    vm: AppViewModel,
    onBack: () -> Unit,
    onShare: (String) -> Unit,
    onOpenBrowser: (String) -> Unit,
) {
    var article by remember { mutableStateOf<Reader.Article?>(null) }
    var failed by remember { mutableStateOf(false) }
    var stage by remember { mutableStateOf("Загружаем статью…") }
    var diagnostics by remember { mutableStateOf("") }
    val context = androidx.compose.ui.platform.LocalContext.current

    LaunchedEffect(perspective.url) {
        // 1) Полный текст уже пришёл в RSS (content:encoded) — сеть не нужна
        if (perspective.content.length > 300) {
            val extracted = withContext(Dispatchers.IO) {
                Reader.extract(perspective.content, perspective.url, perspective.headline)
            }
            val paragraphs = extracted.paragraphs.ifEmpty {
                listOf(RssParser.stripHtml(perspective.content))
            }
            article = Reader.Article(perspective.headline, paragraphs)
            return@LaunchedEffect
        }

        // 2) Быстрый путь: прямое скачивание страницы
        val report = StringBuilder()
        var extracted: Reader.Article? = null
        val directResult = withContext(Dispatchers.IO) {
            runCatching { vm.fetch(perspective.url) }
        }
        directResult.fold(
            onSuccess = { html ->
                val e = withContext(Dispatchers.IO) {
                    Reader.extract(html, perspective.url, perspective.headline)
                }
                report.append("прямое: ${html.length} симв., абзацев ${e.paragraphs.size}")
                if (e.paragraphs.size >= 2) extracted = e
            },
            onFailure = { report.append("прямое: ${it.message?.take(50) ?: "ошибка"}") }
        )

        // 3) Сайт отдал заглушку — рендерим настоящим браузерным движком
        if (extracted == null) {
            stage = "Сайт защищается — открываем браузерным движком…"
            // Страховка снаружи: вечный спиннер невозможен
            val html = kotlinx.coroutines.withTimeoutOrNull(25_000) {
                WebFetcher.fetch(context, perspective.url)
            } ?: ""
            val fromWebView = if (html.length > 500) {
                withContext(Dispatchers.IO) {
                    Reader.extract(html, perspective.url, perspective.headline)
                }
            } else null
            report.append(" · движок: ${html.length} симв., абзацев ${fromWebView?.paragraphs?.size ?: 0}")
            if (fromWebView != null && fromWebView.paragraphs.isNotEmpty()) {
                extracted = fromWebView
            }
        }

        diagnostics = report.toString()
        val result = extracted
        if (result != null && result.paragraphs.isNotEmpty()) {
            article = result
        } else {
            failed = true
        }
    }

    Column(Modifier.fillMaxSize()) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp, vertical = 4.dp)
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.Filled.ArrowBack, "Назад", tint = Prizma.accent)
            }
            Text(
                perspective.source,
                fontSize = 15.sp, fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground,
                modifier = Modifier.weight(1f)
            )
            IconButton(onClick = { onShare(perspective.url) }) {
                Icon(Icons.Filled.Share, "Поделиться", tint = Prizma.accent)
            }
            IconButton(onClick = { onOpenBrowser(perspective.url) }) {
                Icon(Icons.Filled.ExitToApp, "Открыть в браузере", tint = Prizma.accent)
            }
        }

        when {
            article != null -> {
                val a = article!!
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                    contentPadding = PaddingValues(start = 18.dp, end = 18.dp, bottom = 24.dp)
                ) {
                    item {
                        Text(
                            a.title,
                            fontSize = 23.sp, fontWeight = FontWeight.ExtraBold,
                            lineHeight = 29.sp,
                            color = MaterialTheme.colorScheme.onBackground
                        )
                    }
                    items(a.paragraphs) { paragraph ->
                        if (paragraph.startsWith("## ")) {
                            Text(
                                paragraph.removePrefix("## "),
                                fontSize = 18.sp, fontWeight = FontWeight.Bold,
                                lineHeight = 24.sp,
                                color = MaterialTheme.colorScheme.onBackground
                            )
                        } else {
                            Text(
                                paragraph,
                                fontSize = 16.sp, lineHeight = 24.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }
            failed -> {
                Column(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 20.dp, vertical = 12.dp)
                ) {
                    Text(
                        perspective.headline,
                        fontSize = 21.sp, fontWeight = FontWeight.ExtraBold,
                        lineHeight = 27.sp,
                        color = MaterialTheme.colorScheme.onBackground
                    )
                    if (perspective.excerpt.isNotEmpty()) {
                        Spacer(Modifier.width(1.dp))
                        Text(
                            perspective.excerpt,
                            fontSize = 15.sp, lineHeight = 22.sp,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.padding(top = 12.dp)
                        )
                    }
                    Text(
                        "Сайт не отдаёт полный текст — открыть в браузере →",
                        color = Prizma.accent, fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .padding(top = 16.dp)
                            .clickable { onOpenBrowser(perspective.url) }
                    )
                    if (diagnostics.isNotEmpty()) {
                        Text(
                            diagnostics,
                            color = Prizma.textTertiary, fontSize = 11.sp,
                            modifier = Modifier.padding(top = 10.dp)
                        )
                    }
                }
            }
            else -> {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier.fillMaxSize()
                ) {
                    Spacer(Modifier.weight(1f))
                    CircularProgressIndicator(color = Prizma.accent)
                    Text(
                        stage,
                        color = Prizma.textTertiary, fontSize = 13.sp,
                        modifier = Modifier.padding(top = 14.dp)
                    )
                    Spacer(Modifier.weight(1f))
                }
            }
        }
    }
}
