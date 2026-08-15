package com.prizma.news

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
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

    LaunchedEffect(Unit) { vm.loadInitial() }

    val story = openStory
    if (story != null) {
        BackHandler { openStory = null }
        androidx.compose.foundation.layout.Box(
            Modifier
                .fillMaxSize()
                .background(Prizma.backgroundBrush)
        ) {
            DetailScreen(story, vm, onShare, onOpenUrl)
        }
        LaunchedEffect(story.id) { vm.markRead(story) }
        return
    }

    Scaffold(
        containerColor = Color.Transparent,
        modifier = Modifier
            .fillMaxSize()
            .background(Prizma.backgroundBrush),
        bottomBar = {
            NavigationBar(containerColor = Prizma.card) {
                val items = listOf(
                    Triple("Лента", Icons.Filled.Home, 0),
                    Triple("Закладки", Icons.Filled.Star, 1),
                    Triple("Настройки", Icons.Filled.Settings, 2),
                )
                items.forEach { (title, icon, index) ->
                    NavigationBarItem(
                        selected = tab == index,
                        onClick = { tab = index },
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
        androidx.compose.foundation.layout.Box(Modifier.padding(padding)) {
            when (tab) {
                0 -> FeedScreen(vm, briefing) { openStory = it }
                1 -> BookmarksScreen(vm) { openStory = it }
                else -> SettingsScreen(vm)
            }
        }
    }
}
