package com.prizma.news

import android.annotation.SuppressLint
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.json.JSONTokener
import kotlin.coroutines.resume

/// Фолбэк-загрузка страницы через настоящий браузерный движок (WebView):
/// проходит антибот-проверки, которые режут обычные HTTP-клиенты, и
/// возвращает итоговый HTML после исполнения JavaScript.
///
/// Важно: WebView не прикреплён к экрану, поэтому View.postDelayed на нём
/// НЕ выполняется (копится до показа). Все отложенные действия — только
/// через отдельный Handler главного потока.
object WebFetcher {

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun fetch(context: Context, url: String, timeoutMs: Long = 15000): String =
        withContext(Dispatchers.Main) {
            suspendCancellableCoroutine { cont ->
                val handler = Handler(Looper.getMainLooper())
                val webView = WebView(context)
                webView.settings.javaScriptEnabled = true
                webView.settings.domStorageEnabled = true
                webView.settings.loadsImagesAutomatically = false
                webView.settings.blockNetworkImage = true
                // Виртуальный вьюпорт, чтобы движок рендерил страницу
                webView.layout(0, 0, 1080, 2000)

                var finished = false
                fun finish(html: String) {
                    if (finished) return
                    finished = true
                    handler.removeCallbacksAndMessages(null)
                    runCatching { webView.stopLoading(); webView.destroy() }
                    cont.resume(html)
                }

                webView.webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView?, loadedUrl: String?) {
                        if (finished || view == null) return
                        // Пауза: даём JS-челленджам и контенту дорендериться
                        handler.postDelayed({
                            if (finished) return@postDelayed
                            runCatching {
                                view.evaluateJavascript(
                                    "document.documentElement.outerHTML"
                                ) { encoded ->
                                    val html = runCatching {
                                        JSONTokener(encoded ?: "\"\"").nextValue() as? String
                                    }.getOrNull() ?: ""
                                    finish(html)
                                }
                            }.onFailure { finish("") }
                        }, 1500)
                    }
                }

                handler.postDelayed({ finish("") }, timeoutMs)
                cont.invokeOnCancellation {
                    handler.removeCallbacksAndMessages(null)
                    runCatching { webView.stopLoading(); webView.destroy() }
                }
                webView.loadUrl(url)
            }
        }
}
