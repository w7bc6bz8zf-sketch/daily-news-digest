#!/usr/bin/env python3
"""
collect_news.py — сборщик новостей для приложения «Призма» (аналог Particle).

Полный конвейер:
  1. Параллельно забираем RSS из ~100 источников (русские — приоритет).
  2. Определяем язык каждой записи по доле кириллицы.
  3. Кластеризуем по сюжетам отдельно для RU и EN:
     TF-IDF + лёгкий стемминг для русского, best-match leader clustering.
  4. Для сюжетов с одним источником ищем дополнительное покрытие в DuckDuckGo.
  5. Параллельно скачиваем полные тексты статей (trafilatura).
  6. Собираем истории: русский заголовок приоритетно, картинка из RSS,
     до MAX_PERSPECTIVES взглядов разных изданий на один сюжет.
  7. Ранжируем (охват × вес источников × свежесть, бонус русским сюжетам)
     и пишем news_data.json + news_compact.json.

Мёртвый фид — не ошибка: он логируется и пропускается, конвейер живёт дальше.
"""

import hashlib
import json
import os
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta

import feedparser
import requests
import trafilatura
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

try:
    from duckduckgo_search import DDGS
except ImportError:
    try:
        from ddgs import DDGS  # пакет переименован
    except ImportError:
        DDGS = None

# ── Конфиг ────────────────────────────────────────────────────────────────────
MAX_STORIES      = int(os.environ.get("MAX_STORIES", "60"))
HOURS_BACK       = int(os.environ.get("HOURS_BACK", "36"))
RU_SHARE         = float(os.environ.get("RU_SHARE", "0.6"))   # доля русских сюжетов в ленте
DDG_ENABLED      = os.environ.get("DDG_ENABLED", "1") == "1"
MAX_PERSPECTIVES = 6
EXCERPT_CHARS    = 500
FETCH_TIMEOUT    = 12
RSS_WORKERS      = 20
TEXT_WORKERS     = 12
EN_THRESHOLD     = float(os.environ.get("EN_THRESHOLD", "0.15"))
RU_THRESHOLD     = float(os.environ.get("RU_THRESHOLD", "0.25"))
MIN_PERSPECTIVES = 2      # сюжет без 2 реальных источников не публикуется…
TRUSTED_WEIGHT   = 2      # …кроме одиночных новостей от источников с таким весом (добор RU-квоты)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Accept-Language": "ru,en;q=0.8",
}

# ── Источники: (название, вес 1–3, язык, категория, RSS) ─────────────────────
# Вес влияет на выбор заголовка, порядок перспектив и ранжирование сюжета.
FEEDS = [
    # ── Русскоязычные: общество и мир ──
    ("РИА Новости",        3, "ru", "Россия",      "https://ria.ru/export/rss2/archive/index.xml"),
    ("ТАСС",               3, "ru", "Россия",      "https://tass.ru/rss/v2.xml"),
    ("Интерфакс",          3, "ru", "Россия",      "https://www.interfax.ru/rss.asp"),
    ("Lenta.ru",           2, "ru", "Россия",      "https://lenta.ru/rss"),
    ("Газета.Ru",          2, "ru", "Россия",      "https://www.gazeta.ru/export/rss/lenta.xml"),
    ("Известия",           2, "ru", "Россия",      "https://iz.ru/xml/rss/all.xml"),
    ("Российская газета",  2, "ru", "Россия",      "https://rg.ru/xml/index.xml"),
    ("Фонтанка",           2, "ru", "Россия",      "https://www.fontanka.ru/fontanka.rss"),
    ("Meduza",             3, "ru", "Мир",         "https://meduza.io/rss/all"),
    ("BBC Russian",        3, "ru", "Мир",         "https://feeds.bbci.co.uk/russian/rss.xml"),
    ("DW на русском",      2, "ru", "Мир",         "https://rss.dw.com/xml/rss-ru-all"),
    ("Euronews RU",        2, "ru", "Мир",         "https://ru.euronews.com/rss"),
    ("RTVI",               2, "ru", "Мир",         "https://rtvi.com/feed/"),
    ("Новая газета",       2, "ru", "Мир",         "https://novayagazeta.ru/rss/all.xml"),
    # ── Русскоязычные: экономика и бизнес ──
    ("РБК",                3, "ru", "Экономика",   "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"),
    ("Коммерсант",         3, "ru", "Экономика",   "https://www.kommersant.ru/RSS/news.xml"),
    ("Ведомости",          3, "ru", "Экономика",   "https://www.vedomosti.ru/rss/news"),
    ("Forbes.ru",          2, "ru", "Бизнес",      "https://www.forbes.ru/newrss.xml"),
    ("The Bell",           2, "ru", "Экономика",   "https://thebell.io/feed"),
    ("BFM.ru",             2, "ru", "Экономика",   "https://www.bfm.ru/news.rss"),
    ("Банки.ру",           1, "ru", "Экономика",   "https://www.banki.ru/xml/news.rss"),
    ("Финам",              1, "ru", "Экономика",   "https://www.finam.ru/analysis/conews/rsspoint/"),
    ("Inc. Russia",        1, "ru", "Бизнес",      "https://incrussia.ru/feed/"),
    ("RB.ru",              1, "ru", "Бизнес",      "https://rb.ru/feeds/all/"),
    ("Тинькофф Журнал",    1, "ru", "Бизнес",      "https://journal.tinkoff.ru/feed/"),
    # ── Русскоязычные: технологии ──
    ("vc.ru",              2, "ru", "Технологии",  "https://vc.ru/rss"),
    ("Habr",               2, "ru", "Технологии",  "https://habr.com/ru/rss/news/"),
    ("CNews",              2, "ru", "Технологии",  "https://www.cnews.ru/inc/rss/news.xml"),
    ("3DNews",             2, "ru", "Технологии",  "https://3dnews.ru/news/rss/"),
    ("iXBT",               1, "ru", "Технологии",  "https://www.ixbt.com/export/news.rss"),
    ("Hi-Tech Mail",       1, "ru", "Технологии",  "https://hi-tech.mail.ru/rss/all/"),
    ("Хайтек",             1, "ru", "Технологии",  "https://hightech.fm/feed"),
    ("DTF",                1, "ru", "Технологии",  "https://dtf.ru/rss"),
    # ── Русскоязычные: наука ──
    ("N+1",                2, "ru", "Наука",       "https://nplus1.ru/rss"),
    ("Naked Science",      2, "ru", "Наука",       "https://naked-science.ru/feed"),
    ("Элементы",           1, "ru", "Наука",       "https://elementy.ru/rss/news"),
    # ── Русскоязычные: спорт ──
    ("Sports.ru",          2, "ru", "Спорт",       "https://www.sports.ru/rss/main.xml"),
    ("Чемпионат",          2, "ru", "Спорт",       "https://www.championat.com/rss/news/"),
    ("Спорт-Экспресс",     2, "ru", "Спорт",       "https://www.sport-express.ru/services/materials/news/se/"),
    # ── Русскоязычные: культура ──
    ("Афиша Daily",        1, "ru", "Культура",    "https://daily.afisha.ru/rss/"),
    ("Film.ru",            1, "ru", "Культура",    "https://www.film.ru/rss/all"),
    # ── Англоязычные: мир ──
    ("BBC World",          3, "en", "Мир",         "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian",       3, "en", "Мир",         "https://www.theguardian.com/world/rss"),
    ("Al Jazeera",         2, "en", "Мир",         "https://www.aljazeera.com/xml/rss/all.xml"),
    ("NPR News",           2, "en", "Мир",         "https://feeds.npr.org/1001/rss.xml"),
    ("CNN World",          2, "en", "Мир",         "http://rss.cnn.com/rss/edition_world.rss"),
    ("Sky News",           2, "en", "Мир",         "https://feeds.skynews.com/feeds/rss/world.xml"),
    ("DW English",         2, "en", "Мир",         "https://rss.dw.com/rdf/rss-en-all"),
    ("France 24",          2, "en", "Мир",         "https://www.france24.com/en/rss"),
    ("Euronews",           2, "en", "Мир",         "https://www.euronews.com/rss?format=mrss&level=theme&name=news"),
    ("Politico",           2, "en", "Мир",         "https://www.politico.com/rss/politicopicks.xml"),
    ("Time",               1, "en", "Мир",         "https://time.com/feed/"),
    ("The Atlantic",       1, "en", "Мир",         "https://www.theatlantic.com/feed/all/"),
    ("NBC News",           1, "en", "Мир",         "https://feeds.nbcnews.com/nbcnews/public/news"),
    ("CBS News",           1, "en", "Мир",         "https://www.cbsnews.com/latest/rss/main"),
    ("ABC News",           1, "en", "Мир",         "https://abcnews.go.com/abcnews/topstories"),
    ("Foreign Policy",     1, "en", "Мир",         "https://foreignpolicy.com/feed/"),
    # ── Англоязычные: экономика и бизнес ──
    ("Bloomberg",          3, "en", "Экономика",   "https://feeds.bloomberg.com/markets/news.rss"),
    ("FT",                 3, "en", "Экономика",   "https://www.ft.com/rss/home/uk"),
    ("The Economist",      3, "en", "Экономика",   "https://www.economist.com/finance-and-economics/rss.xml"),
    ("The Economist Biz",  2, "en", "Бизнес",      "https://www.economist.com/business/rss.xml"),
    ("WSJ",                3, "en", "Экономика",   "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("CNBC",               2, "en", "Экономика",   "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Axios",              2, "en", "Экономика",   "https://api.axios.com/feed/"),
    ("Yahoo Finance",      1, "en", "Экономика",   "https://finance.yahoo.com/news/rssindex"),
    ("Business Insider",   1, "en", "Бизнес",      "https://feeds.businessinsider.com/custom/all"),
    ("Fast Company",       1, "en", "Бизнес",      "https://www.fastcompany.com/latest/rss"),
    ("HBR",                1, "en", "Бизнес",      "http://feeds.hbr.org/harvardbusiness"),
    # ── Англоязычные: технологии и наука ──
    ("Bloomberg Tech",     2, "en", "Технологии",  "https://feeds.bloomberg.com/technology/news.rss"),
    ("MIT Tech Review",    2, "en", "Технологии",  "https://www.technologyreview.com/feed/"),
    ("Ars Technica",       2, "en", "Технологии",  "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",          2, "en", "Технологии",  "https://www.theverge.com/rss/index.xml"),
    ("Wired",              2, "en", "Технологии",  "https://www.wired.com/feed/rss"),
    ("TechCrunch",         2, "en", "Технологии",  "https://techcrunch.com/feed/"),
    ("VentureBeat",        1, "en", "Технологии",  "https://venturebeat.com/feed/"),
    ("Engadget",           1, "en", "Технологии",  "https://www.engadget.com/rss.xml"),
    ("ZDNet",              1, "en", "Технологии",  "https://www.zdnet.com/news/rss.xml"),
    ("Nature News",        2, "en", "Наука",       "https://www.nature.com/nature.rss"),
    ("Science Daily",      1, "en", "Наука",       "https://www.sciencedaily.com/rss/all.xml"),
    ("New Scientist",      1, "en", "Наука",       "https://www.newscientist.com/feed/home/"),
    # ── Англоязычные: спорт и культура ──
    ("BBC Sport",          2, "en", "Спорт",       "https://feeds.bbci.co.uk/sport/rss.xml"),
    ("ESPN",               1, "en", "Спорт",       "https://www.espn.com/espn/rss/news"),
    ("Variety",            1, "en", "Культура",    "https://variety.com/feed/"),
    ("Rolling Stone",      1, "en", "Культура",    "https://www.rollingstone.com/feed/"),
]

SOURCE_WEIGHT = {name: w for name, w, _, _, _ in FEEDS}

PROMO_KEYWORDS = [
    "promo code", "coupon code", "discount code", "% off", "deal of the day",
    "voucher code", "cashback", "best deals", "промокод", "скидка дня", "купон",
]

BOT_CHECK_SIGNALS = [
    "enable js", "enable javascript", "please make sure your browser",
    "click the box below", "not a robot", "please enable js",
    "just a moment", "cloudflare ray", "not a bot", "if you are not a",
    "access denied", "you don't have permission to access",
    "please click the box", "blocking the video player",
    "browser extensions seems to be blocking",
    "subscribe to unlock", "subscribe to read",
]

PAYWALL_CUTOFFS = [
    "subscribe to unlock", "subscribe to read", "subscribe to continue",
    "to continue, please", "please click the box", "register to read",
    "sign in to read", "sign up to read", "already a subscriber",
    "try unlimited access", "complete digital access",
    "подписка на издание", "доступно только подписчикам", "оформите подписку",
]

RUSSIAN_STOP_WORDS = frozenset("""
в и на с что по к за от для не но или то а же как так до при после это этот
эта эти также только уже был была были будет чтобы если когда где который
которая которые его её их он она они оно мы вы я ты нас вам нам себя свой
своя все весь вся очень более ещё об о из со во над под перед чем тем тот
тех том ту те та им ими ему ей мне которого которой которых которым потому
поэтому потом тогда здесь там теперь тут сейчас весьма сам сама само сами
один одна одно одни своего своей своих своим своими может стал стала стали
году года лет один два три из-за около между через против
""".split())

# Окончания отсортированы по убыванию длины — снимаем самое длинное.
_RU_SUFFIXES = sorted([
    "иями", "ями", "ами", "иях", "ях", "ах", "ией", "ей", "ой", "ий", "ый",
    "ая", "яя", "ое", "ее", "ого", "его", "ому", "ему", "ыми", "ими", "ым",
    "им", "ом", "ем", "ах", "ов", "ев", "ие", "ые", "ья", "ью", "ия", "ии",
    "ую", "юю", "ешь", "ишь", "ует", "ают", "яют", "ат", "ят", "ут",
    "ют", "ет", "ит", "ил", "ыл", "ял", "ила", "или", "ыла", "ыли", "яла",
    "яли", "ла", "ло", "ли", "ть", "ся", "сь", "ам", "ям", "у",
    "ю", "а", "я", "о", "е", "ы", "и", "ь",
], key=len, reverse=True)


def ru_stem(word: str) -> str:
    """Лёгкий стемминг: снять одно окончание, оставив основу ≥ 4 символов."""
    for suf in _RU_SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 4:
            return word[: -len(suf)]
    return word


def ru_analyzer(text: str) -> list[str]:
    words = re.findall(r"[а-яёa-z0-9]+", text.lower())
    toks = [ru_stem(w) for w in words
            if len(w) > 2 and w not in RUSSIAN_STOP_WORDS]
    return toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]


# ── Хелперы ───────────────────────────────────────────────────────────────────

def detect_lang(text: str) -> str:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en"
    cyr = sum(1 for c in letters if "а" <= c.lower() <= "я" or c.lower() == "ё")
    return "ru" if cyr / len(letters) > 0.3 else "en"


def is_promo(title: str, snippet: str) -> bool:
    text = (title + " " + snippet).lower()
    return any(kw in text for kw in PROMO_KEYWORDS)


def is_bot_check(text: str) -> bool:
    t = text.lower()
    return any(sig in t for sig in BOT_CHECK_SIGNALS)


def clean_html(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", text).strip()


def entry_image(e) -> str:
    for key in ("media_content", "media_thumbnail"):
        for item in (e.get(key) or []):
            url = item.get("url", "")
            if url.startswith("http"):
                return url
    for enc in (e.get("enclosures") or []):
        url = enc.get("href") or enc.get("url") or ""
        if url.startswith("http") and "image" in (enc.get("type") or "image"):
            return url
    m = re.search(r'<img[^>]+src="(http[^"]+)"', e.get("summary", "") or "")
    return m.group(1) if m else ""


# ── Сбор RSS ──────────────────────────────────────────────────────────────────

def _fetch_one_feed(feed_def, cutoff):
    source, weight, lang, category, url = feed_def
    out = []
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
        for e in feed.entries[:40]:
            published = None
            for attr in ("published_parsed", "updated_parsed"):
                if getattr(e, attr, None):
                    try:
                        published = datetime(*getattr(e, attr)[:6], tzinfo=timezone.utc)
                    except Exception:
                        pass
                    break
            if published and published < cutoff:
                continue
            title = (e.get("title") or "").strip()
            snippet = clean_html(e.get("summary", e.get("description", "")))[:500]
            if not title or is_promo(title, snippet):
                continue
            out.append({
                "source":       source,
                "weight":       weight,
                "category":     category,
                "title":        title,
                "snippet":      snippet,
                "link":         e.get("link", ""),
                "image":        entry_image(e),
                "published_at": published.isoformat() if published else None,
                "full_text":    "",
                "lang":         detect_lang(title) if lang == "ru" else lang,
            })
    except Exception as ex:
        print(f"[WARN] RSS {source}: {type(ex).__name__}: {str(ex)[:80]}")
    return source, out


def fetch_rss_entries(hours_back: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    entries, dead = [], []
    with ThreadPoolExecutor(max_workers=RSS_WORKERS) as pool:
        futures = [pool.submit(_fetch_one_feed, fd, cutoff) for fd in FEEDS]
        for fut in as_completed(futures):
            source, out = fut.result()
            if out:
                entries.extend(out)
            else:
                dead.append(source)

    # Дедупликация: одинаковые ссылки и повторы заголовков внутри источника
    seen_links, seen_titles, unique = set(), set(), []
    for e in entries:
        link_key = e["link"].split("?")[0]
        title_key = (e["source"], e["title"].lower())
        if link_key in seen_links or title_key in seen_titles:
            continue
        seen_links.add(link_key)
        seen_titles.add(title_key)
        unique.append(e)

    if dead:
        print(f"[INFO] Пустые/мёртвые фиды ({len(dead)}): {', '.join(sorted(dead))}")
    print(f"[INFO] {len(unique)} записей из {len(FEEDS) - len(dead)} живых источников")
    return unique


# ── Кластеризация ─────────────────────────────────────────────────────────────

def _cluster_group(entries: list[dict], lang: str, threshold: float) -> list[list[dict]]:
    """Best-match leader clustering: сильный источник становится «лидером»
    сюжета, каждая запись прикрепляется к самому похожему лидеру."""
    if len(entries) < 2:
        return [[e] for e in entries]
    texts = [f"{e['title']} {e['snippet'][:300]}" for e in entries]
    if lang == "ru":
        vec = TfidfVectorizer(analyzer=ru_analyzer, max_features=30000, sublinear_tf=True)
    else:
        vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2),
                              max_features=30000, sublinear_tf=True)
    sim = cosine_similarity(vec.fit_transform(texts))

    order = sorted(range(len(entries)), key=lambda i: -entries[i]["weight"])
    leaders: list[int] = []
    clusters: dict[int, list[dict]] = {}
    for i in order:
        best, best_sim = None, threshold
        for lead in leaders:
            if sim[i][lead] >= best_sim:
                best, best_sim = lead, sim[i][lead]
        if best is None:
            leaders.append(i)
            clusters[i] = [entries[i]]
        else:
            clusters[best].append(entries[i])
    return list(clusters.values())


def cluster_entries(entries: list[dict]) -> tuple[list[list[dict]], list[list[dict]]]:
    ru = [e for e in entries if e["lang"] == "ru"]
    en = [e for e in entries if e["lang"] != "ru"]
    ru_clusters = _cluster_group(ru, "ru", RU_THRESHOLD)
    en_clusters = _cluster_group(en, "en", EN_THRESHOLD)
    for cl in (ru_clusters, en_clusters):
        cl.sort(key=lambda c: len({e["source"] for e in c}), reverse=True)
    multi_ru = sum(1 for c in ru_clusters if len({e['source'] for e in c}) >= 2)
    multi_en = sum(1 for c in en_clusters if len({e['source'] for e in c}) >= 2)
    print(f"[INFO] Кластеры: RU {len(ru_clusters)} (мульти {multi_ru}) / "
          f"EN {len(en_clusters)} (мульти {multi_en})")
    return ru_clusters, en_clusters


# ── DuckDuckGo: добор источников ──────────────────────────────────────────────

def search_web_news(headline: str, existing_sources: set, category: str) -> list[dict]:
    words = re.sub(r"[^\w\s]", " ", headline).split()
    query = " ".join(words[:10])
    try:
        with DDGS() as ddgs:
            hits = list(ddgs.news(keywords=query, max_results=15, safesearch="off"))
        results = []
        for hit in hits:
            source = (hit.get("source") or hit.get("publisher") or "").strip()
            title = (hit.get("title") or "").strip()
            snippet = clean_html(hit.get("body", ""))[:500]
            url = hit.get("url", "")
            if not title or not url or not source or source in existing_sources:
                continue
            if is_promo(title, snippet):
                continue
            results.append({
                "source": source, "weight": SOURCE_WEIGHT.get(source, 1),
                "category": category, "title": title, "snippet": snippet,
                "link": url, "image": hit.get("image", "") or "",
                "published_at": None, "full_text": "",
                "lang": detect_lang(title),
            })
        return results
    except Exception as ex:
        print(f"[WARN] DDG '{query[:40]}': {type(ex).__name__}")
        return []


def boost_single_source_clusters(clusters: list[list[dict]], top_n: int) -> None:
    if not DDG_ENABLED or DDGS is None:
        print("[INFO] DDG-добор выключен или пакет не установлен")
        return
    searches = boosted = 0
    for cluster in clusters[:top_n]:
        unique = {e["source"] for e in cluster}
        if len(unique) >= 2:
            continue
        extra = search_web_news(cluster[0]["title"], unique, cluster[0]["category"])
        if extra:
            cluster.extend(extra[:4])
            boosted += 1
        searches += 1
        time.sleep(0.3)
        if searches >= 40:   # DDG банит агрессивный поток запросов
            break
    print(f"[INFO] DDG: {searches} поисков, дополнено {boosted} сюжетов")


# ── Полные тексты ─────────────────────────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT, allow_redirects=True)
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
        if text and len(text) > 80 and not is_bot_check(text):
            return text[:3000]
    except Exception:
        pass
    return ""


def enrich_clusters(clusters: list[list[dict]], top_n: int) -> list[list[dict]]:
    top = clusters[:top_n]
    jobs = []
    for cluster in top:
        for entry in cluster[:MAX_PERSPECTIVES]:
            if entry["link"] and not entry["full_text"]:
                jobs.append(entry)
    print(f"[INFO] Скачиваем полные тексты: {len(jobs)} статей")
    with ThreadPoolExecutor(max_workers=TEXT_WORKERS) as pool:
        futures = {pool.submit(fetch_full_text, e["link"]): e for e in jobs}
        for fut in as_completed(futures):
            futures[fut]["full_text"] = fut.result()
    return top


# ── Саммари ───────────────────────────────────────────────────────────────────

def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p.strip() for p in parts if 40 <= len(p.strip()) <= 300]


def _strip_title_echo(text: str, title: str) -> str:
    """RSS-сниппеты часто начинаются с копии заголовка (иногда дважды,
    с мусором вроде 'NewsFeed' или ' - Published') — вырезаем эти повторы."""
    t = text.replace(" - Published", " ").strip()
    tl = title.lower().strip()
    if not tl:
        return t
    for _ in range(3):
        idx = t.lower().find(tl)
        if idx == -1 or idx > 200:
            break
        t = (t[:idx] + t[idx + len(tl):]).strip(" \t-–—.…|")
        t = re.sub(r"^(NewsFeed|Video|Live|Опубликовано)\b[\s:—-]*", "", t,
                   flags=re.IGNORECASE).strip()
    return t


def extractive_summary(cluster: list[dict], lang: str, max_points: int = 3) -> list[str]:
    """Фолбэк без AI: 2-3 самых информативных предложения из текстов кластера
    (частотная оценка слов + отсев почти одинаковых предложений)."""
    def prep(e: dict) -> str:
        raw = clean_html(e.get("full_text") or e.get("snippet") or "")[:2000]
        return _strip_title_echo(raw, e.get("title", ""))

    texts = [prep(e) for e in cluster if e.get("lang") == lang]
    if not any(texts):
        texts = [prep(e) for e in cluster]
    sentences = []
    for t in texts:
        sentences.extend(split_sentences(t))
    if not sentences:
        return []

    def words(s: str) -> list[str]:
        ws = re.findall(r"[а-яёa-z0-9]{3,}", s.lower())
        if lang == "ru":
            ws = [ru_stem(w) for w in ws if w not in RUSSIAN_STOP_WORDS]
        return ws

    freq = Counter()
    for s in sentences:
        freq.update(set(words(s)))

    def score(s: str) -> float:
        ws = words(s)
        return sum(freq[w] for w in ws) / (len(ws) ** 0.5) if ws else 0.0

    def jaccard(a: set, b: set) -> float:
        return len(a & b) / max(len(a | b), 1)

    # RSS-сниппеты часто начинаются с копии заголовка — такие предложения
    # не несут нового и выбрасываются
    head_sets = [set(words(e.get("title", ""))) for e in cluster if e.get("title")]

    chosen: list[str] = []
    for s in sorted(dict.fromkeys(sentences), key=score, reverse=True):
        if is_bot_check(s) or is_promo(s, ""):
            continue
        sw = set(words(s))
        if any(jaccard(sw, hs) > 0.5 for hs in head_sets):
            continue
        if any(jaccard(sw, set(words(c))) > 0.35 for c in chosen):
            continue
        chosen.append(s)
        if len(chosen) >= max_points:
            break
    return chosen


def ai_enrich_stories(stories: list[dict]) -> None:
    """AI-саммари и перевод через OpenAI API (ключ в OPENAI_API_KEY).
    Экономно: батчи по 10 сюжетов, только заголовок + короткие выдержки,
    один запрос на батч. Без ключа — пропускается, остаются экстрактивные."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        print("[INFO] OPENAI_API_KEY не задан — саммари экстрактивные, без перевода")
        return
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    total_in = total_out = done = 0
    for i in range(0, len(stories), 10):
        batch = stories[i:i + 10]
        items = [{
            "id": s["id"],
            "headline": s["headline"],
            "excerpts": [p["excerpt"][:350] for p in s["perspectives"][:4]],
        } for s in batch]
        user_msg = (
            "Для каждого сюжета составь на русском языке: headline_ru — краткий "
            "новостной заголовок (переведи, если исходный не русский) и summary — "
            "2-3 пункта строго по фактам из выдержек, без воды и оценок. "
            'Верни строго JSON: {"stories":[{"id":"...","headline_ru":"...",'
            '"summary":["...","..."]}]}\n\n' + json.dumps(items, ensure_ascii=False)
        )
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}"},
                json={
                    "model": model,
                    "temperature": 0.3,
                    "max_tokens": 2500,
                    "response_format": {"type": "json_object"},
                    "messages": [
                        {"role": "system",
                         "content": "Ты редактор новостей. Пишешь кратко, нейтрально, по-русски."},
                        {"role": "user", "content": user_msg},
                    ],
                },
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            total_in += usage.get("prompt_tokens", 0)
            total_out += usage.get("completion_tokens", 0)
            result = json.loads(data["choices"][0]["message"]["content"])
            by_id = {r["id"]: r for r in result.get("stories", []) if r.get("id")}
            for s in batch:
                r = by_id.get(s["id"])
                if not r:
                    continue
                if r.get("summary"):
                    s["summary"] = [str(x).strip() for x in r["summary"] if str(x).strip()][:3]
                hru = (r.get("headline_ru") or "").strip()
                if hru:
                    s["headline"] = hru
                done += 1
        except Exception as ex:
            print(f"[WARN] OpenAI batch {i // 10 + 1}: {type(ex).__name__}: {str(ex)[:120]}")
    cost = (total_in * 0.15 + total_out * 0.60) / 1e6
    print(f"[INFO] AI: {done}/{len(stories)} сюжетов, токены {total_in}+{total_out} (~${cost:.3f})")


# ── Сборка историй ────────────────────────────────────────────────────────────

def get_excerpt(entry: dict) -> str:
    text = entry.get("full_text") or entry.get("snippet") or entry.get("title", "")
    text = clean_html(text)
    for cutoff in PAYWALL_CUTOFFS:
        idx = text.lower().find(cutoff)
        if idx > 60:
            text = text[:idx].strip().rstrip(".,;")
        elif idx >= 0:
            return ""
    if not text or is_bot_check(text):
        return ""
    if len(text) > EXCERPT_CHARS:
        cut = text[:EXCERPT_CHARS]
        dot = cut.rfind(". ")
        return (cut[:dot + 1] if dot > 80 else cut) + "…"
    return text


def story_freshness_bonus(published_iso: str | None) -> float:
    if not published_iso:
        return 0.0
    try:
        age_h = (datetime.now(timezone.utc)
                 - datetime.fromisoformat(published_iso)).total_seconds() / 3600
        return max(0.0, 6.0 - age_h / 6.0)
    except Exception:
        return 0.0


def build_story(cluster: list[dict], allow_single: bool = False) -> dict | None:
    sorted_c = sorted(cluster, key=lambda e: -e["weight"])

    seen, perspectives = set(), []
    for e in sorted_c:
        if e["source"] in seen:
            continue
        excerpt = get_excerpt(e)
        if not excerpt:
            continue
        perspectives.append({
            "source":       e["source"],
            "lang":         e["lang"],
            "headline":     e["title"],
            "excerpt":      excerpt,
            "url":          e["link"],
            "published_at": e["published_at"],
        })
        seen.add(e["source"])
        if len(perspectives) >= MAX_PERSPECTIVES:
            break

    if not perspectives:
        return None
    single = len(perspectives) < MIN_PERSPECTIVES
    if single and not (allow_single and sorted_c[0]["weight"] >= TRUSTED_WEIGHT):
        return None

    ru_entries = [e for e in sorted_c if e["lang"] == "ru" and e["source"] in seen]
    en_entries = [e for e in sorted_c if e["lang"] != "ru" and e["source"] in seen]
    headline_ru = ru_entries[0]["title"] if ru_entries else ""
    headline_en = en_entries[0]["title"] if en_entries else ""
    category = Counter(e["category"] for e in cluster).most_common(1)[0][0]
    image = next((e["image"] for e in sorted_c if e.get("image")), "")
    published = max((e["published_at"] for e in cluster if e["published_at"]),
                    default=None)

    unique_sources = {e["source"] for e in cluster}
    weight_sum = sum(SOURCE_WEIGHT.get(s, 1) for s in unique_sources)
    lang = "ru" if headline_ru else "en"
    score = (len(unique_sources) * 3.0 + weight_sum
             + story_freshness_bonus(published)
             + (4.0 if lang == "ru" else 0.0)
             - (5.0 if single else 0.0))

    return {
        "id":            hashlib.sha1(perspectives[0]["url"].encode()).hexdigest()[:12],
        "category":      category,
        "lang":          lang,
        "headline":      headline_ru or headline_en,
        "headline_en":   headline_en,
        "summary":       extractive_summary(cluster, lang),
        "coverage":      len(unique_sources),
        "single_source": single,
        "image":         image,
        "published_at":  published,
        "score":         round(score, 2),
        "perspectives":  perspectives,
    }


def collect_stories(candidates: list[list[dict]], target: int,
                    allow_single_fill: bool) -> list[dict]:
    stories = []
    # Первый проход — только полноценные мультиисточниковые сюжеты
    for c in candidates:
        s = build_story(c)
        if s:
            stories.append(s)
        if len(stories) >= target:
            return stories
    # Добор одиночными новостями от надёжных источников
    if allow_single_fill:
        used = {s["id"] for s in stories}
        for c in candidates:
            s = build_story(c, allow_single=True)
            if s and s["id"] not in used and s["single_source"]:
                stories.append(s)
                used.add(s["id"])
            if len(stories) >= target:
                break
    return stories


# ── Выгрузка ──────────────────────────────────────────────────────────────────

def write_output(stories: list[dict], total_entries: int, started: datetime) -> None:
    output = {
        "collected_at":  started.isoformat(),
        "total_sources": len(FEEDS),
        "total_entries": total_entries,
        "story_count":   len(stories),
        "stories":       stories,
    }
    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    compact = {
        "collected_at": started.isoformat(),
        "story_count":  len(stories),
        "stories": [{
            "id":       s["id"],
            "category": s["category"],
            "headline": s["headline"],
            "coverage": s["coverage"],
            "image":    s["image"],
            "sources":  [p["source"] for p in s["perspectives"]],
            "excerpt":  (s["summary"][0] if s.get("summary") else s["perspectives"][0]["excerpt"])[:200],
            "url":      s["perspectives"][0]["url"],
        } for s in stories],
    }
    with open("news_compact.json", "w", encoding="utf-8") as f:
        json.dump(compact, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[DONE] news_data.json: {os.path.getsize('news_data.json')} байт, "
          f"news_compact.json: {os.path.getsize('news_compact.json')} байт")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    started = datetime.now(timezone.utc)
    ru_target = round(MAX_STORIES * RU_SHARE)
    print(f"[START] {started.isoformat()} | {MAX_STORIES} сюжетов "
          f"(RU-квота {ru_target}) | окно {HOURS_BACK}ч | {len(FEEDS)} источников")

    entries = fetch_rss_entries(HOURS_BACK)
    if not entries:
        print("[ERROR] Ни одной записи — выходим.")
        return

    ru_clusters, en_clusters = cluster_entries(entries)

    boost_single_source_clusters(ru_clusters, top_n=ru_target * 2)
    boost_single_source_clusters(en_clusters, top_n=(MAX_STORIES - ru_target) * 2)
    # После DDG-добора язык записей мог смешаться — пересортируем по охвату
    for cl in (ru_clusters, en_clusters):
        cl.sort(key=lambda c: len({e["source"] for e in c}), reverse=True)

    ru_candidates = enrich_clusters(ru_clusters, top_n=ru_target * 3)
    en_candidates = enrich_clusters(en_clusters, top_n=(MAX_STORIES - ru_target) * 3)

    ru_stories = collect_stories(ru_candidates, ru_target, allow_single_fill=True)
    en_stories = collect_stories(en_candidates, MAX_STORIES - len(ru_stories),
                                 allow_single_fill=False)
    print(f"[INFO] Историй: {len(ru_stories)} RU + {len(en_stories)} EN")

    stories = sorted(ru_stories + en_stories, key=lambda s: -s["score"])
    ai_enrich_stories(stories)
    write_output(stories, len(entries), started)

    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    print(f"[DONE] {len(stories)} сюжетов за {elapsed:.0f}с")


if __name__ == "__main__":
    main()
