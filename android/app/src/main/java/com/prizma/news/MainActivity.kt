package com.prizma.news

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.animation.AnimatedContent
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.animation.togetherWith
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.List
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.lifecycle.viewmodel.compose.viewModel

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            PrizmaTheme {
                PrizmaApp(
                    onShare = { url ->
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, url)
                        }
                        startActivity(Intent.createChooser(intent, "Поделиться сюжетом"))
                    },
                    onOpenUrl = { url ->
                        runCatching {
                            startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        }
                    }
                )
            }
        }
    }
}

@Composable
fun PrizmaApp(onShare: (String) -> Unit, onOpenUrl: (String) -> Unit) {
    val vm: AppViewModel = viewModel()
    val context = androidx.compose.ui.platform.LocalContext.current
    val briefing = remember { Briefing(context.applicationContext) }
    var tab by remember { mutableIntStateOf(0) }
    var openStory by remember { mutableStateOf<Story?>(null) }
    var openArticle by remember { mutableStateOf<Perspective?>(null) }

    LaunchedEffect(Unit) { vm.loadInitial() }

    Crossfade(targetState = vm.hasOnboarded, label = "root") { onboarded ->
        if (!onboarded) {
            OnboardingScreen(vm)
        } else {
            BackHandler(enabled = openArticle != null || openStory != null) {
                if (openArticle != null) openArticle = null else openStory = null
            }

            AnimatedContent(
                targetState = Pair(openStory, openArticle),
                transitionSpec = {
                    (slideInHorizontally(tween(260)) { it / 3 } + fadeIn(tween(260)))
                        .togetherWith(
                            slideOutHorizontally(tween(200)) { -it / 4 } + fadeOut(tween(200))
                        )
                },
                label = "nav"
            ) { (story, article) ->
                when {
                    article != null -> Box(
                        Modifier
                            .fillMaxSize()
                            .background(Prizma.backgroundBrush)
                    ) {
                        ReaderScreen(
                            perspective = article,
                            vm = vm,
                            onBack = { openArticle = null },
                            onShare = onShare,
                            onOpenBrowser = onOpenUrl,
                        )
                    }

                    story != null -> Box(
                        Modifier
                            .fillMaxSize()
                            .background(Prizma.backgroundBrush)
                    ) {
                        DetailScreen(story, vm, onShare) { perspective ->
                            openArticle = perspective
                        }
                        LaunchedEffect(story.id) { vm.markRead(story) }
                    }

                    else -> MainTabs(vm, briefing, tab,
                        onTab = { tab = it },
                        onOpen = { openStory = it })
                }
            }
        }
    }
}

@Composable
private fun MainTabs(
    vm: AppViewModel,
    briefing: Briefing,
    tab: Int,
    onTab: (Int) -> Unit,
    onOpen: (Story) -> Unit,
) {
    Scaffold(
        containerColor = Color.Transparent,
        modifier = Modifier
            .fillMaxSize()
            .background(Prizma.backgroundBrush),
        bottomBar = {
            NavigationBar(containerColor = Prizma.card) {
                val items = listOf(
                    Triple("Лента", Icons.Filled.Home, 0),
                    Triple("Источники", Icons.AutoMirrored.Filled.List, 1),
                    Triple("Закладки", Icons.Filled.Star, 2),
                    Triple("Настройки", Icons.Filled.Settings, 3),
                )
                items.forEach { (title, icon, index) ->
                    NavigationBarItem(
                        selected = tab == index,
                        onClick = { onTab(index) },
                        icon = { Icon(icon, contentDescription = title) },
                        label = { Text(title) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = Color.White,
                            selectedTextColor = Prizma.accent,
                            unselectedIconColor = Prizma.textTertiary,
                            unselectedTextColor = Prizma.textTertiary,
                            indicatorColor = Prizma.accent.copy(alpha = 0.35f),
                        )
                    )
                }
            }
        }
    ) { padding ->
        Box(Modifier.padding(padding)) {
            Crossfade(targetState = tab, label = "tabs") { current ->
                when (current) {
                    0 -> FeedScreen(vm, briefing, onOpen)
                    1 -> MySourcesScreen(vm, onOpen)
                    2 -> BookmarksScreen(vm, onOpen)
                    else -> SettingsScreen(vm)
                }
            }
        }
    }
}
