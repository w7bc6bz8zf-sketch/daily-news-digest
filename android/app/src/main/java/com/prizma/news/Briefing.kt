package com.prizma.news

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.util.Locale

/// Аудио-брифинг: системный синтез речи читает топ-10 сюжетов.
/// isPlaying — наблюдаемое состояние для анимации кнопки.
class Briefing(context: Context) {

    var isPlaying by mutableStateOf(false)
        private set

    private var ready = false
    private val main = Handler(Looper.getMainLooper())
    private val tts: TextToSpeech = TextToSpeech(context) { status ->
        if (status == TextToSpeech.SUCCESS) ready = true
    }

    init {
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) {
                if (utteranceId == LAST_ID) main.post { isPlaying = false }
            }
            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                main.post { isPlaying = false }
            }
        })
    }

    fun toggle(stories: List<Story>) {
        if (!ready) return
        if (isPlaying) {
            tts.stop()
            isPlaying = false
            return
        }
        val top = stories.take(10)
        if (top.isEmpty()) return
        tts.language = Locale("ru", "RU")
        tts.speak("Аудио-брифинг Призмы.", TextToSpeech.QUEUE_FLUSH, null, "intro")
        top.forEachIndexed { i, story ->
            val text = "Сюжет ${i + 1}. ${story.headline}. ${story.preview.take(200)}"
            val id = if (i == top.lastIndex) LAST_ID else "story$i"
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, id)
        }
        isPlaying = true
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }

    private companion object {
        const val LAST_ID = "last"
    }
}
