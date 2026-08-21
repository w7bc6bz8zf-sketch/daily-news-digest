package com.prizma.news

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/// Первый запуск: брендинг, выбор тем интересов, режим «только русское»
@Composable
fun OnboardingScreen(vm: AppViewModel) {
    val topics = listOf(
        "Искусственный интеллект", "Криптовалюты", "Санкции", "Ключевая ставка",
        "Недвижимость", "Футбол", "Кино", "Илон Маск", "Автопром", "Космос",
        "Стартапы", "Энергетика",
    )

    Box(
        Modifier
            .fillMaxSize()
            .background(Prizma.backgroundBrush)
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 22.dp)
        ) {
            Spacer(Modifier.height(48.dp))
            Box(
                contentAlignment = Alignment.Center,
                modifier = Modifier
                    .size(92.dp)
                    .background(Prizma.prism, CircleShape)
            ) {
                Text("▲", fontSize = 40.sp, color = Color.White)
            }
            Spacer(Modifier.height(16.dp))
            Text(
                "Призма",
                fontSize = 40.sp, fontWeight = FontWeight.ExtraBold,
                color = MaterialTheme.colorScheme.onBackground
            )
            Text(
                "Одна новость — все точки зрения.\n90 изданий, русскоязычные в приоритете.",
                fontSize = 14.sp, lineHeight = 20.sp,
                textAlign = TextAlign.Center,
                color = Prizma.textSecondary
            )
            Spacer(Modifier.height(22.dp))

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(16.dp)
            ) {
                Text(
                    "Что вам интересно?",
                    fontSize = 17.sp, fontWeight = FontWeight.Bold,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    "Эти темы будут выше в ленте «Для вас». Можно изменить в настройках.",
                    fontSize = 12.sp, color = Prizma.textSecondary
                )
                Spacer(Modifier.height(10.dp))
                topics.chunked(2).forEach { pair ->
                    Row(Modifier.fillMaxWidth()) {
                        pair.forEach { topic ->
                            OnboardingTopicChip(vm, topic, Modifier.weight(1f))
                        }
                        if (pair.size == 1) Spacer(Modifier.weight(1f))
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }

            Spacer(Modifier.height(12.dp))

            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .prizmaCard()
                    .padding(horizontal = 16.dp, vertical = 6.dp)
            ) {
                Column(Modifier.weight(1f)) {
                    Text(
                        "Только русскоязычные сюжеты",
                        fontSize = 14.sp, fontWeight = FontWeight.Medium,
                        color = MaterialTheme.colorScheme.onSurface
                    )
                    Text(
                        "Мировые новости с переводом останутся",
                        fontSize = 12.sp, color = Prizma.textSecondary
                    )
                }
                Switch(
                    checked = vm.russianOnly,
                    onCheckedChange = { vm.setRussianOnlyMode(it) }
                )
            }

            Spacer(Modifier.height(20.dp))

            Text(
                "Начать читать",
                fontSize = 17.sp, fontWeight = FontWeight.Bold,
                color = Color.White,
                textAlign = TextAlign.Center,
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Prizma.prism, CircleShape)
                    .clickable { vm.completeOnboarding() }
                    .padding(vertical = 15.dp)
            )
            Spacer(Modifier.height(28.dp))
        }
    }
}

@Composable
private fun OnboardingTopicChip(vm: AppViewModel, topic: String, modifier: Modifier) {
    val isOn = vm.topics.any { it.equals(topic, ignoreCase = true) }
    Text(
        text = (if (isOn) "✓ " else "+ ") + topic,
        fontSize = 13.sp, fontWeight = FontWeight.Medium,
        color = if (isOn) Color.White else Prizma.textSecondary,
        textAlign = TextAlign.Center,
        maxLines = 1,
        modifier = modifier
            .padding(horizontal = 4.dp)
            .background(
                if (isOn) Prizma.accent else Prizma.chip,
                RoundedCornerShape(12.dp)
            )
            .clickable { if (isOn) vm.unfollowTopic(topic) else vm.followTopic(topic) }
            .padding(vertical = 10.dp, horizontal = 6.dp)
    )
}
