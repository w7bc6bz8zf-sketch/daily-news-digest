package com.prizma.news

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.Star
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage

// ─── Общие элементы ──────────────────────────────────────────────────────────

@Composable
fun CategoryPill(category: String) {
    val color = Prizma.categoryColor(category)
    Text(
        category,
        fontSize = 11.sp,
        fontWeight = FontWeight.Bold,
        color = color,
        modifier = Modifier
            .background(color.copy(alpha = 0.16f), CircleShape)
            .padding(horizontal = 9.dp, vertical = 3.dp)
    )
}

@Composable
fun CoveragePill(coverage: Int) {
    Text(
        sourcesCountText(coverage),
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        color = Prizma.accent,
        modifier = Modifier
            .background(Prizma.accent.copy(alpha = 0.14f), CircleShape)
            .padding(horizontal = 8.dp, vertical = 3.dp)
    )
}

@Composable
fun SourceAvatar(name: String, size: Int = 26) {
    Box(
        contentAlignment = Alignment.Center,
        modifier = Modifier
            .size(size.dp)
            .background(Prizma.prism, CircleShape)
    ) {
        Text(
            name.take(1).uppercase(),
            color = Color.White,
            fontSize = (size * 0.42).sp,
            fontWeight = FontWeight.Bold
        )
    }
}

fun Modifier.prizmaCard(): Modifier = this
    .background(Prizma.card, RoundedCornerShape(18.dp))
    .border(1.dp, Prizma.cardStroke, RoundedCornerShape(18.dp))

// ─── Карточка сюжета ─────────────────────────────────────────────────────────

@Composable
fun StoryCard(story: Story, vm: AppViewModel, onOpen: (Story) -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .prizmaCard()
            .clickable { onOpen(story) }
            .padding(12.dp)
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                CategoryPill(story.category)
                Spacer(Modifier.width(6.dp))
                Text(
                    relativeTime(story.publishedAt),
                    fontSize = 11.sp, color = Prizma.textTertiary
                )
            }
            Spacer(Modifier.height(6.dp))
            Text(
                story.headline,
                fontSize = 15.sp,
                fontWeight = FontWeight.Bold,
                lineHeight = 20.sp,
                maxLines = 3,
                overflow = TextOverflow.Ellipsis,
                color = if (vm.isRead(story)) Prizma.textSecondary
                        else MaterialTheme.colorScheme.onSurface
            )
            if (story.preview.isNotEmpty()) {
                Spacer(Modifier.height(4.dp))
                Text(
                    story.preview,
                    fontSize = 12.sp, lineHeight = 16.sp,
                    maxLines = 2, overflow = TextOverflow.Ellipsis,
                    color = Prizma.textSecondary
                )
            }
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                val topic = vm.matchedTopics(story).firstOrNull()
                if (topic != null) {
                    Text(
                        "#$topic",
                        fontSize = 11.sp, fontWeight = FontWeight.SemiBold,
                        color = Color(0xFFFFB04F), maxLines = 1,
                        modifier = Modifier
                            .background(Color(0x28FFB04F), CircleShape)
                            .padding(horizontal = 7.dp, vertical = 2.dp)
                    )
                    Spacer(Modifier.width(6.dp))
                }
                if (story.coverage > 1) {
                    CoveragePill(story.coverage)
                    Spacer(Modifier.width(6.dp))
                }
                Text(
                    story.sourceNames.take(2).joinToString(" · "),
                    fontSize = 11.sp, color = Prizma.textTertiary,
                    maxLines = 1, overflow = TextOverflow.Ellipsis
                )
            }
        }
        if (story.image.isNotEmpty()) {
            Spacer(Modifier.width(10.dp))
            AsyncImage(
                model = story.image,
                contentDescription = null,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(84.dp)
                    .background(Prizma.chip, RoundedCornerShape(14.dp))
                    .border(1.dp, Prizma.cardStroke, RoundedCornerShape(14.dp))
            )
        }
    }
}

// ─── Лента ───────────────────────────────────────────────────────────────────

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FeedScreen(vm: AppViewModel, briefing: Briefing, onOpen: (Story) -> Unit) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 10.dp)
        ) {
            Text(
                "Призма",
                fontSize = 28.sp,
                fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Spacer(Modifier.weight(1f))
            IconButton(onClick = { briefing.toggle(vm.displayedStories) }) {
                Icon(
                    Icons.Filled.PlayArrow, contentDescription = "Аудио-брифинг",
                    tint = Prizma.accent
                )
            }
        }

        OutlinedTextField(
            value = vm.searchText,
            onValueChange = { vm.searchText = it },
            placeholder = { Text("Поиск по сюжетам", color = Prizma.textTertiary) },
            leadingIcon = {
                Icon(Icons.Filled.Search, null, tint = Prizma.textTertiary)
            },
            trailingIcon = {
                if (vm.searchText.isNotEmpty()) {
                    IconButton(onClick = { vm.searchText = "" }) {
                        Icon(Icons.Filled.Clear, null, tint = Prizma.textTertiary)
                    }
                }
            },
            singleLine = true,
            shape = RoundedCornerShape(14.dp),
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = Prizma.card,
                unfocusedContainerColor = Prizma.card,
                focusedBorderColor = Prizma.accent,
                unfocusedBorderColor = Prizma.cardStroke,
            ),
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp)
        )

        Spacer(Modifier.height(10.dp))

        Row(modifier = Modifier.padding(horizontal = 16.dp)) {
            ModeChip("Для вас", vm.forYou) { vm.setFeedMode(true) }
            Spacer(Modifier.width(8.dp))
            ModeChip("Все", !vm.forYou) { vm.setFeedMode(false) }
        }

        Spacer(Modifier.height(8.dp))

        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 16.dp)
        ) {
            item {
                CategoryChip("Все", vm.selectedCategory == null) {
                    vm.selectedCategory = null
                }
            }
            items(vm.availableCategories) { category ->
                CategoryChip(category, vm.selectedCategory == category) {
                    vm.selectedCategory = if (vm.selectedCategory == category) null else category
                }
            }
        }

        Spacer(Modifier.height(8.dp))

        val list = vm.displayedStories
        val ptrState = androidx.compose.material3.pulltorefresh.rememberPullToRefreshState()
        if (ptrState.isRefreshing) {
            androidx.compose.runtime.LaunchedEffect(true) {
                vm.refreshAndWait()      // ждём полного окончания загрузки…
                ptrState.endRefresh()    // …и гарантированно убираем индикатор
            }
        }

        Box(
            Modifier
                .fillMaxSize()
                .nestedScroll(ptrState.nestedScrollConnection)
        ) {
            if (list.isEmpty()) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text(
                        vm.error ?: if (vm.isLoading) "Загружаем новости…" else "Ничего не найдено",
                        color = Prizma.textSecondary
                    )
                }
            } else {
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(
                        start = 16.dp, end = 16.dp, bottom = 16.dp
                    ),
                    modifier = Modifier.fillMaxSize()
                ) {
                    item {
                        Text(
                            "Обновлено ${relativeTime(vm.collectedAt)} · потяните вниз, чтобы обновить",
                            fontSize = 11.sp, color = Prizma.textTertiary
                        )
                    }
                    items(list) { story ->
                        StoryCard(story, vm, onOpen)
                    }
                }
            }
            androidx.compose.material3.pulltorefresh.PullToRefreshContainer(
                state = ptrState,
                containerColor = Prizma.card,
                contentColor = Prizma.accent,
                modifier = Modifier.align(Alignment.TopCenter)
            )
        }
    }
}

@Composable
private fun ModeChip(title: String, selected: Boolean, onClick: () -> Unit) {
    val base = Modifier.clickable(onClick = onClick)
    val mod = if (selected) base.background(Prizma.prism, CircleShape)
              else base.background(Prizma.chip, CircleShape)
    Text(
        title,
        fontSize = 13.sp,
        fontWeight = FontWeight.SemiBold,
        color = if (selected) Color.White else Prizma.textSecondary,
        modifier = mod.padding(horizontal = 16.dp, vertical = 7.dp)
    )
}

@Composable
private fun CategoryChip(title: String, selected: Boolean, onClick: () -> Unit) {
    val color = if (title == "Все") Prizma.accent else Prizma.categoryColor(title)
    Text(
        title,
        fontSize = 12.sp,
        fontWeight = FontWeight.Medium,
        color = if (selected) Color.White else Prizma.textSecondary,
        modifier = Modifier
            .clickable(onClick = onClick)
            .background(if (selected) color else Prizma.chip, CircleShape)
            .padding(horizontal = 12.dp, vertical = 6.dp)
    )
}

// ─── Сюжет ───────────────────────────────────────────────────────────────────

@Composable
fun DetailScreen(
    story: Story,
    vm: AppViewModel,
    onShare: (String) -> Unit,
    onRead: (Perspective) -> Unit,
) {
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(14.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        if (story.image.isNotEmpty()) {
            item {
                AsyncImage(
                    model = story.image,
                    contentDescription = null,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(200.dp)
                        .background(Prizma.chip, RoundedCornerShape(18.dp))
                        .border(1.dp, Prizma.cardStroke, RoundedCornerShape(18.dp))
                )
            }
        }
        item {
            Column {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CategoryPill(story.category)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        relativeTime(story.publishedAt),
                        fontSize = 12.sp, color = Prizma.textTertiary
                    )
                    Spacer(Modifier.weight(1f))
                    IconButton(onClick = { vm.toggleBookmark(story) }) {
                        Icon(
                            if (vm.isBookmarked(story)) Icons.Filled.Star else Icons.Outlined.Star,
                            contentDescription = "Закладка",
                            tint = Prizma.accent
                        )
                    }
                    IconButton(onClick = {
                        story.perspectives.firstOrNull()?.url?.let(onShare)
                    }) {
                        Icon(Icons.Filled.Share, contentDescription = "Поделиться",
                             tint = Prizma.accent)
                    }
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    story.headline,
                    fontSize = 22.sp, fontWeight = FontWeight.ExtraBold, lineHeight = 28.sp,
                    color = MaterialTheme.colorScheme.onBackground
                )
                if (story.headlineEn.isNotEmpty() && story.headlineEn != story.headline) {
                    Spacer(Modifier.height(4.dp))
                    Text(story.headlineEn, fontSize = 13.sp, color = Prizma.textSecondary)
                }
                if (story.coverage > 1) {
                    Spacer(Modifier.height(8.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        story.sourceNames.take(5).forEach { source ->
                            SourceAvatar(source, 24)
                            Spacer(Modifier.width(2.dp))
                        }
                        Spacer(Modifier.width(6.dp))
                        Text(
                            "Сюжет освещают ${sourcesCountText(story.coverage)}",
                            fontSize = 12.sp, color = Prizma.textSecondary
                        )
                    }
                }
            }
        }
        if (story.summary.isNotEmpty()) {
            item {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(Prizma.accent.copy(alpha = 0.09f), RoundedCornerShape(16.dp))
                        .border(1.dp, Prizma.accent.copy(alpha = 0.18f), RoundedCornerShape(16.dp))
                        .padding(14.dp)
                ) {
                    Text(
                        "✦ Кратко",
                        fontSize = 16.sp, fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    story.summary.forEach { point ->
                        Spacer(Modifier.height(8.dp))
                        Row {
                            Box(
                                Modifier
                                    .padding(top = 4.dp)
                                    .width(3.dp)
                                    .height(14.dp)
                                    .background(Prizma.prism, CircleShape)
                            )
                            Spacer(Modifier.width(10.dp))
                            Text(
                                point, fontSize = 14.sp, lineHeight = 19.sp,
                                color = MaterialTheme.colorScheme.onSurface
                            )
                        }
                    }
                }
            }
        }
        item {
            Text(
                "Перспективы",
                fontSize = 17.sp, fontWeight = FontWeight.Bold,
                color = MaterialTheme.colorScheme.onBackground
            )
        }
        items(story.perspectives) { perspective ->
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .clickable { if (perspective.url.isNotEmpty()) onRead(perspective) }
                    .padding(14.dp)
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    SourceAvatar(perspective.source)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        perspective.source,
                        fontSize = 14.sp, fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Spacer(Modifier.weight(1f))
                    Text(
                        if (perspective.lang == "ru") "RU" else "EN",
                        fontSize = 10.sp, fontWeight = FontWeight.Bold,
                        color = Prizma.textTertiary,
                        modifier = Modifier
                            .background(Prizma.chip, CircleShape)
                            .padding(horizontal = 6.dp, vertical = 2.dp)
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    perspective.headline,
                    fontSize = 13.sp, fontWeight = FontWeight.SemiBold, lineHeight = 18.sp,
                    color = MaterialTheme.colorScheme.onSurface
                )
                if (perspective.excerpt.isNotEmpty()) {
                    Spacer(Modifier.height(4.dp))
                    Text(
                        perspective.excerpt,
                        fontSize = 13.sp, lineHeight = 18.sp,
                        color = Prizma.textSecondary
                    )
                }
                Spacer(Modifier.height(6.dp))
                Text(
                    "Читать в приложении →",
                    fontSize = 12.sp, fontWeight = FontWeight.SemiBold,
                    color = Prizma.accent
                )
            }
        }
    }
}

// ─── Закладки ────────────────────────────────────────────────────────────────

@Composable
fun BookmarksScreen(vm: AppViewModel, onOpen: (Story) -> Unit) {
    Column(Modifier.fillMaxSize()) {
        Text(
            "Закладки",
            fontSize = 28.sp, fontWeight = FontWeight.ExtraBold,
            color = MaterialTheme.colorScheme.onBackground,
            modifier = Modifier.padding(16.dp)
        )
        if (vm.bookmarks.isEmpty()) {
            Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text(
                    "Пока пусто.\nСохраняйте сюжеты звёздочкой — они доступны офлайн.",
                    color = Prizma.textSecondary,
                    fontSize = 14.sp,
                    lineHeight = 20.sp
                )
            }
        } else {
            LazyColumn(
                verticalArrangement = Arrangement.spacedBy(10.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(
                    start = 16.dp, end = 16.dp, bottom = 16.dp
                )
            ) {
                items(vm.bookmarks) { story ->
                    StoryCard(story, vm, onOpen)
                }
            }
        }
    }
}

// ─── Настройки ───────────────────────────────────────────────────────────────

@Composable
fun SettingsScreen(vm: AppViewModel) {
    var newTopic = androidx.compose.runtime.remember {
        androidx.compose.runtime.mutableStateOf("")
    }
    LazyColumn(
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        modifier = Modifier.fillMaxSize()
    ) {
        item {
            Text(
                "Настройки",
                fontSize = 28.sp, fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onBackground
            )
        }
        item {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(horizontal = 14.dp, vertical = 6.dp)
            ) {
                Text(
                    "Только русскоязычные сюжеты",
                    fontSize = 14.sp,
                    color = MaterialTheme.colorScheme.onSurface,
                    modifier = Modifier.weight(1f)
                )
                Switch(
                    checked = vm.russianOnly,
                    onCheckedChange = { vm.setRussianOnlyMode(it) }
                )
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(14.dp)
            ) {
                Text(
                    "Мои темы",
                    fontSize = 16.sp, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "Сюжеты с этими словами поднимаются в «Для вас»",
                    fontSize = 12.sp, color = Prizma.textSecondary
                )
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = newTopic.value,
                        onValueChange = { newTopic.value = it },
                        placeholder = { Text("Новая тема", color = Prizma.textTertiary) },
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Prizma.chip,
                            unfocusedContainerColor = Prizma.chip,
                            focusedBorderColor = Prizma.accent,
                            unfocusedBorderColor = Prizma.cardStroke,
                        ),
                        modifier = Modifier.weight(1f)
                    )
                    IconButton(onClick = {
                        vm.followTopic(newTopic.value)
                        newTopic.value = ""
                    }) {
                        Icon(Icons.Filled.Add, "Добавить", tint = Prizma.accent)
                    }
                }
                vm.topics.forEach { topic ->
                    Spacer(Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            topic, fontSize = 14.sp,
                            color = MaterialTheme.colorScheme.onSurface,
                            modifier = Modifier.weight(1f)
                        )
                        IconButton(onClick = { vm.unfollowTopic(topic) }) {
                            Icon(Icons.Filled.Clear, "Удалить", tint = Prizma.textTertiary)
                        }
                    }
                }
            }
        }
        item {
            val newFeed = androidx.compose.runtime.remember {
                androidx.compose.runtime.mutableStateOf("")
            }
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(14.dp)
            ) {
                Text(
                    "Мои RSS-источники",
                    fontSize = 16.sp, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(4.dp))
                Text(
                    "Записи из ваших лент появятся в категории «Мои источники»",
                    fontSize = 12.sp, color = Prizma.textSecondary
                )
                Spacer(Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    OutlinedTextField(
                        value = newFeed.value,
                        onValueChange = { newFeed.value = it },
                        placeholder = {
                            Text("https://site.ru/rss", color = Prizma.textTertiary)
                        },
                        singleLine = true,
                        shape = RoundedCornerShape(12.dp),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedContainerColor = Prizma.chip,
                            unfocusedContainerColor = Prizma.chip,
                            focusedBorderColor = Prizma.accent,
                            unfocusedBorderColor = Prizma.cardStroke,
                        ),
                        modifier = Modifier.weight(1f)
                    )
                    IconButton(onClick = {
                        vm.addCustomFeed(newFeed.value)
                        newFeed.value = ""
                    }) {
                        Icon(Icons.Filled.Add, "Добавить", tint = Prizma.accent)
                    }
                }
                vm.customFeeds.forEach { feedUrl ->
                    Spacer(Modifier.height(6.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                feedUrl, fontSize = 12.sp,
                                color = MaterialTheme.colorScheme.onSurface,
                                maxLines = 1, overflow = TextOverflow.Ellipsis
                            )
                            val status = vm.customFeedStatus[feedUrl] ?: "загружается…"
                            Text(
                                status, fontSize = 11.sp,
                                color = if (status.startsWith("ошибка") || status.startsWith("лента пуста"))
                                    androidx.compose.ui.graphics.Color(0xFFFF6B6B)
                                else Prizma.textTertiary
                            )
                        }
                        IconButton(onClick = { vm.removeCustomFeed(feedUrl) }) {
                            Icon(Icons.Filled.Clear, "Удалить", tint = Prizma.textTertiary)
                        }
                    }
                }
                if (vm.customFeeds.isNotEmpty()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        "Записи из ваших лент — в чипе «Мои источники» в начале списка категорий",
                        fontSize = 11.sp, color = Prizma.textTertiary
                    )
                }
            }
        }
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(14.dp)
            ) {
                Text(
                    "О приложении",
                    fontSize = 16.sp, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(6.dp))
                Text("Призма 1.0 · сюжетов в ленте: ${vm.stories.size}",
                     fontSize = 13.sp, color = Prizma.textSecondary)
                Text("Обновлено ${relativeTime(vm.collectedAt)}",
                     fontSize = 13.sp, color = Prizma.textSecondary)
                Spacer(Modifier.height(10.dp))
                Text(
                    "Сбросить прочитанное",
                    fontSize = 14.sp, fontWeight = FontWeight.SemiBold,
                    color = Color(0xFFFF6B6B),
                    modifier = Modifier.clickable { vm.resetRead() }
                )
            }
        }
    }
}
