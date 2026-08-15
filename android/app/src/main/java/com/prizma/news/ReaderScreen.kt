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

    LaunchedEffect(perspective.url) {
        withContext(Dispatchers.IO) {
            try {
                val html = vm.fetch(perspective.url)
                val extracted = Reader.extract(html, perspective.url, perspective.headline)
                withContext(Dispatchers.Main) {
                    if (extracted.paragraphs.isEmpty()) failed = true else article = extracted
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { failed = true }
            }
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
                    horizontalAlignment = Alignment.CenterHorizontally,
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(24.dp)
                ) {
                    Spacer(Modifier.weight(1f))
                    Text(
                        "Не удалось извлечь текст статьи",
                        color = Prizma.textSecondary, fontSize = 15.sp
                    )
                    Spacer(Modifier.width(8.dp))
                    Text(
                        "Открыть в браузере",
                        color = Prizma.accent, fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        modifier = Modifier
                            .padding(top = 12.dp)
                            .clickable { onOpenBrowser(perspective.url) }
                    )
                    Spacer(Modifier.weight(1f))
                }
            }
            else -> {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(color = Prizma.accent)
                }
            }
        }
    }
}
