package com.prizma.news

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

/// Аудио-брифинг: системный синтез речи читает топ-10 сюжетов
class Briefing(context: Context) {
    private var ready = false
    private val tts: TextToSpeech = TextToSpeech(context) { status ->
        if (status == TextToSpeech.SUCCESS) {
            ready = true
        }
    }

    fun toggle(stories: List<Story>) {
        if (!ready) return
        if (tts.isSpeaking) {
            tts.stop()
            return
        }
        tts.language = Locale("ru", "RU")
        tts.speak("Аудио-брифинг Призмы.", TextToSpeech.QUEUE_FLUSH, null, "intro")
        stories.take(10).forEachIndexed { i, story ->
            val text = "Сюжет ${i + 1}. ${story.headline}. ${story.preview.take(200)}"
            tts.speak(text, TextToSpeech.QUEUE_ADD, null, "story$i")
        }
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }
}
