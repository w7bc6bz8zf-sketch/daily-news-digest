package com.prizma.news

import android.annotation.SuppressLint
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import org.json.JSONTokener
import kotlin.coroutines.resume

/// Фолбэк-загрузка страницы настоящим браузерным движком (WebView).
///
/// Антибот-защиты (Qrator, DDoS-Guard, Cloudflare):
///  - вычисляют WebView по маркеру «wv» в User-Agent → ставим UA как у Chrome;
///  - ставят куку и перезагружают страницу через 3-5 секунд → снимаем HTML
///    не один раз, а каждые 2 секунды, храня лучший (самый длинный) снимок.
/// View.postDelayed на неприкреплённом WebView не работает — только Handler.
object WebFetcher {

    private const val CHROME_UA =
        "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 " +
            "(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36"

    @SuppressLint("SetJavaScriptEnabled")
    suspend fun fetch(context: Context, url: String, timeoutMs: Long = 18000): String =
        withContext(Dispatchers.Main) {
            suspendCancellableCoroutine { cont ->
                val handler = Handler(Looper.getMainLooper())
                val webView = WebView(context)
                webView.settings.javaScriptEnabled = true
                webView.settings.domStorageEnabled = true
                webView.settings.loadsImagesAutomatically = false
                webView.settings.blockNetworkImage = true
                webView.settings.userAgentString = CHROME_UA
                CookieManager.getInstance().setAcceptCookie(true)
                CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
                webView.layout(0, 0, 1080, 2000)

                var best = ""
                var finished = false
                fun finish() {
                    if (finished) return
                    finished = true
                    handler.removeCallbacksAndMessages(null)
                    runCatching { webView.stopLoading(); webView.destroy() }
                    cont.resume(best)
                }

                val snapshot = object : Runnable {
                    override fun run() {
                        if (finished) return
                        runCatching {
                            webView.evaluateJavascript(
                                "document.documentElement.outerHTML"
                            ) { encoded ->
                                if (finished) return@evaluateJavascript
                                val html = runCatching {
                                    JSONTokener(encoded ?: "\"\"").nextValue() as? String
                                }.getOrNull() ?: ""
                                if (html.length > best.length) best = html
                                // Большая страница — челлендж пройден, дальше не ждём
                                if (best.length > 30000) finish()
                            }
                        }
                        if (!finished) handler.postDelayed(this, 2000)
                    }
                }

                webView.webViewClient = WebViewClient()   // редиректы внутри WebView
                handler.postDelayed(snapshot, 2500)       // первый снимок
                handler.postDelayed({ finish() }, timeoutMs)
                cont.invokeOnCancellation {
                    handler.removeCallbacksAndMessages(null)
                    runCatching { webView.stopLoading(); webView.destroy() }
                }
                webView.loadUrl(url)
            }
        }
}
