package com.prizma.news

import android.annotation.SuppressLint
import android.content.Context
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
object WebFetcher {

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun fetch(context: Context, url: String, timeoutMs: Long = 15000): String =
        withContext(Dispatchers.Main) {
            suspendCancellableCoroutine { cont ->
                val webView = WebView(context)
                webView.settings.javaScriptEnabled = true
                webView.settings.domStorageEnabled = true
                webView.settings.loadsImagesAutomatically = false
                webView.settings.blockNetworkImage = true

                var finished = false
                fun finish(html: String) {
                    if (finished) return
                    finished = true
                    runCatching { webView.stopLoading(); webView.destroy() }
                    cont.resume(html)
                }

                webView.webViewClient = object : WebViewClient() {
                    override fun onPageFinished(view: WebView?, loadedUrl: String?) {
                        // Небольшая пауза: даём JS-челленджам и ленивому
                        // контенту дорендериться
                        view?.postDelayed({
                            if (finished) return@postDelayed
                            view.evaluateJavascript(
                                "document.documentElement.outerHTML"
                            ) { encoded ->
                                val html = runCatching {
                                    JSONTokener(encoded ?: "\"\"").nextValue() as? String
                                }.getOrNull() ?: ""
                                finish(html)
                            }
                        }, 1500)
                    }
                }

                webView.postDelayed({ finish("") }, timeoutMs)
                cont.invokeOnCancellation {
                    runCatching { webView.stopLoading(); webView.destroy() }
                }
                webView.loadUrl(url)
            }
        }
}
