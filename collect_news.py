#!/usr/bin/env python3
"""
collect_news.py — Part 1 of news digest pipeline.

For every story, we REQUIRE at least 2 sources with real text.
If a cluster has only 1 source, we actively search DuckDuckGo
for additional coverage before giving up.

Flow:
  1. Fetch RSS from 55+ sources
  2. TF-IDF cluster
  3. Top candidates with 1 source → search DuckDuckGo for more coverage
  4. Fetch full text
  5. Build stories — skip any with < MIN_PERSPECTIVES real excerpts
  6. Save news_data.json and commit to repo
"""

import json
import os
import random
import re
import time
import feedparser
import requests
import trafilatura
import nltk
from duckduckgo_search import DDGS
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from datetime import datetime, timezone, timedelta

nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)

# ── Config ────────────────────────────────────────────────────────────────────
MAX_STORIES       = int(os.environ.get("MAX_STORIES", "40"))
HOURS_BACK        = int(os.environ.get("HOURS_BACK", "36"))
MAX_PERSPECTIVES  = 5
EXCERPT_CHARS     = 400
FETCH_TIMEOUT     = 10
CLUSTER_THRESHOLD = 0.15
MIN_PERSPECTIVES  = 2   # HARD RULE — story skipped if fewer real excerpts

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/1.0)"}

PROMO_KEYWORDS = [
    "promo code", "coupon code", "discount code", "% off",
    "deal of the day", "voucher code", "cashback", "best deals",
    "промокод", "скидка", "купон",
]

BOT_CHECK_SIGNALS = [
    "enable js", "enable javascript", "please make sure your browser",
    "click the box below", "not a robot", "please enable js",
    "just a moment", "cloudflare ray",
    # TASS bot-check format: "Datetime: 2026-07-02 ... IP: ... ID: ... not a bot"
    "not a bot", "if you are not a",
    # Sky News / Akamai
    "access denied", "you don't have permission to access",
    # Bloomberg "please click the box"
    "please click the box",
]

# Russian stop words — prevents common function words from creating false clusters
RUSSIAN_STOP_WORDS = frozenset([
    "в", "и", "на", "с", "что", "по", "к", "за", "от", "для",
    "не", "но", "или", "то", "а", "же", "как", "так", "до",
    "при", "после", "это", "этот", "эта", "эти", "также",
    "только", "уже", "был", "была", "были", "будет", "чтобы",
    "если", "когда", "где", "который", "которая", "которые",
    "его", "её", "их", "он", "она", "они", "оно", "мы", "вы",
    "я", "ты", "нас", "вам", "нам", "себя", "свой", "своя",
    "все", "весь", "вся", "очень", "более", "ещё", "ещe",
    "об", "о", "из", "со", "во", "над", "под", "перед",
    "со", "чем", "тем", "тот", "тех", "тем", "том", "ту",
    "те", "та", "им", "их", "ими", "ему", "ей", "мне",
    "который", "которого", "которой", "которых", "которым",
    "потому", "поэтому", "потом", "тогда", "здесь", "там",
    "теперь", "тут", "сейчас", "очень", "весьма", "сам",
    "сама", "само", "сами", "один", "одна", "одно", "одни",
    "своего", "своей", "своих", "своим", "своими",
])

SOURCE_PRIORITY = [
    "Reuters", "AP News", "BBC World", "FT", "The Economist",
    "Bloomberg", "WSJ", "The Guardian", "Foreign Policy", "NPR News",
    "MIT Tech Review", "Wired", "HBR", "Adweek",
    "ТАСС", "РБК", "Коммерсант",
]

# ── RSS Feeds (55+ sources) ────────────────────────────────────────────────────
FEEDS = [
    # World & Politics
    ("Reuters",           "🌍 World",          "https://feeds.reuters.com/reuters/topNews"),
    ("AP News",           "🌍 World",          "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World",         "🌍 World",          "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian",      "🌍 World",          "https://www.theguardian.com/world/rss"),
    ("Al Jazeera",        "🌍 World",          "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Foreign Policy",    "🌍 World",          "https://foreignpolicy.com/feed/"),
    ("Politico",          "🌍 World",          "https://www.politico.com/rss/politicopicks.xml"),
    ("NPR News",          "🌍 World",          "https://feeds.npr.org/1001/rss.xml"),
    ("Time",              "🌍 World",          "https://time.com/feed/"),
    ("The Atlantic",      "🌍 World",          "https://www.theatlantic.com/feed/all/"),
    ("CNN World",         "🌍 World",          "http://rss.cnn.com/rss/edition_world.rss"),
    ("NBC News",          "🌍 World",          "https://feeds.nbcnews.com/nbcnews/public/news"),
    ("CBS News",          "🌍 World",          "https://www.cbsnews.com/latest/rss/main"),
    ("ABC News",          "🌍 World",          "https://abcnews.go.com/abcnews/topstories"),
    ("Sky News",          "🌍 World",          "https://feeds.skynews.com/feeds/rss/world.xml"),
    ("DW English",        "🌍 World",          "https://rss.dw.com/rdf/rss-en-all"),
    ("France 24",         "🌍 World",          "https://www.france24.com/en/rss"),
    ("Euronews",          "🌍 World",          "https://www.euronews.com/rss?format=mrss&level=theme&name=news"),
    # Economics & Markets
    ("Reuters Business",  "📈 Economy",        "https://feeds.reuters.com/reuters/businessNews"),
    ("The Economist",     "📈 Economy",        "https://www.economist.com/finance-and-economics/rss.xml"),
    ("The Economist W.",  "🌍 World",          "https://www.economist.com/international/rss.xml"),
    ("The Economist B.",  "💼 Business",       "https://www.economist.com/business/rss.xml"),
    ("FT",                "📈 Economy",        "https://www.ft.com/rss/home/uk"),
    ("Bloomberg",         "📈 Economy",        "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Tech",    "💡 Tech & AI",      "https://feeds.bloomberg.com/technology/news.rss"),
    ("WSJ",               "📈 Economy",        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("Axios",             "📈 Economy",        "https://api.axios.com/feed/"),
    ("CNBC",              "📈 Economy",        "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("Yahoo Finance",     "📈 Economy",        "https://finance.yahoo.com/news/rssindex"),
    # Technology & AI
    ("MIT Tech Review",   "💡 Tech & AI",      "https://www.technologyreview.com/feed/"),
    ("Ars Technica",      "💡 Tech & AI",      "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",         "💡 Tech & AI",      "https://www.theverge.com/rss/index.xml"),
    ("Wired",             "💡 Tech & AI",      "https://www.wired.com/feed/rss"),
    ("TechCrunch",        "💡 Tech & AI",      "https://techcrunch.com/feed/"),
    ("VentureBeat",       "💡 Tech & AI",      "https://venturebeat.com/feed/"),
    ("Engadget",          "💡 Tech & AI",      "https://www.engadget.com/rss.xml"),
    ("ZDNet",             "💡 Tech & AI",      "https://www.zdnet.com/news/rss.xml"),
    # Business & Strategy
    ("HBR",               "💼 Business",       "http://feeds.hbr.org/harvardbusiness"),
    ("Forbes",            "💼 Business",       "https://www.forbes.com/innovation/feed/"),
    ("Fast Company",      "💼 Business",       "https://www.fastcompany.com/latest/rss"),
    ("Inc.",              "💼 Business",       "https://www.inc.com/rss"),
    ("Business Insider",  "💼 Business",       "https://feeds.businessinsider.com/custom/all"),
    ("Quartz",            "💼 Business",       "https://qz.com/rss"),
    # Marketing & Advertising
    ("Adweek",            "📣 Marketing",      "https://www.adweek.com/feed/"),
    ("Marketing Week",    "📣 Marketing",      "https://www.marketingweek.com/feed/"),
    ("The Drum",          "📣 Marketing",      "https://www.thedrum.com/rss.xml"),
    ("Campaign",          "📣 Marketing",      "https://www.campaignlive.co.uk/rss"),
    ("Ad Age",            "📣 Marketing",      "https://adage.com/rss"),
    # FMCG & Retail
    ("Retail Dive",       "🛒 FMCG & Retail",  "https://www.retaildive.com/feeds/news/"),
    ("Food Dive",         "🛒 FMCG & Retail",  "https://www.fooddive.com/feeds/news/"),
    ("Grocery Dive",      "🛒 FMCG & Retail",  "https://www.grocerydive.com/feeds/news/"),
    ("Consumer Goods",    "🛒 FMCG & Retail",  "https://www.consumergoods.com/rss.xml"),
    # Russian sources
    ("РБК",               "🌍 World",          "https://rssexport.rbc.ru/rbcnews/news/20/full.rss"),
    ("Коммерсант",        "💼 Business",       "https://www.kommersant.ru/RSS/main.xml"),
    ("ТАСС",              "🌍 World",          "https://tass.ru/rss/v2.xml"),
    ("vc.ru",             "💡 Tech & AI",      "https://vc.ru/rss"),
    ("Meduza",            "🌍 World",          "https://meduza.io/rss/all"),
    ("Lenta.ru",          "🌍 World",          "https://lenta.ru/rss"),
    ("Interfax",          "🌍 World",          "https://www.interfax.ru/rss.asp"),
]

KNOWN_SOURCES = {s for s, _, _ in FEEDS}


# ── Helpers ───────────────────────────────────────────────────────────────────

def is_promo(title: str, snippet: str) -> bool:
    text = (title + " " + snippet).lower()
    return any(kw in text for kw in PROMO_KEYWORDS)


def is_bot_check(text: str) -> bool:
    t = text.lower()
    return any(sig in t for sig in BOT_CHECK_SIGNALS)


def clean_snippet(raw: str) -> str:
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text).strip()[:500]


# ── RSS Fetching ──────────────────────────────────────────────────────────────

def fetch_rss_entries(hours_back: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    entries = []
    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:30]:
                published = None
                for attr in ("published_parsed", "updated_parsed"):
                    if hasattr(e, attr) and getattr(e, attr):
                        try:
                            published = datetime(*getattr(e, attr)[:6], tzinfo=timezone.utc)
                        except Exception:
                            pass
                        break
                if published and published < cutoff:
                    continue
                title   = e.get("title", "").strip()
                snippet = clean_snippet(e.get("summary", e.get("description", "")))
                if not title or is_promo(title, snippet):
                    continue
                entries.append({
                    "source":    source,
                    "category":  category,
                    "title":     title,
                    "snippet":   snippet,
                    "link":      e.get("link", ""),
                    "full_text": "",
                    "lang":      "ru" if source in ("РБК", "Коммерсант", "ТАСС", "vc.ru",
                                                    "Meduza", "Lenta.ru", "Interfax") else "en",
                })
        except Exception as ex:
            print(f"[WARN] RSS {source}: {ex}")

    random.shuffle(entries)
    entries = entries[:1500]
    print(f"[INFO] Fetched {len(entries)} entries after promo filter")
    return entries


# ── Web search for missing sources ────────────────────────────────────────────

def search_web_news(headline: str, existing_sources: set, category: str) -> list[dict]:
    """
    Search DuckDuckGo news for a headline and return articles
    from sources NOT already in the cluster.
    BUG FIX: iterate hits INSIDE the 'with DDGS()' block so the
    session is still open when the generator is consumed.
    """
    words = re.sub(r"[^\w\s]", " ", headline).split()
    query = " ".join(words[:10])
    try:
        results = []
        with DDGS() as ddgs:
            # Force evaluation inside context manager — session must be open
            hits = list(ddgs.news(keywords=query, max_results=20, safesearch="off"))

        for hit in hits:
            source  = hit.get("source", hit.get("publisher", "Unknown")).strip()
            title   = hit.get("title", "").strip()
            snippet = clean_snippet(hit.get("body", ""))
            url     = hit.get("url", "")

            if not title or not url:
                continue
            if source in existing_sources:
                continue
            if is_promo(title, snippet):
                continue

            results.append({
                "source":    source,
                "category":  category,
                "title":     title,
                "snippet":   snippet,
                "link":      url,
                "full_text": "",
                "lang":      "en",
            })
        return results
    except Exception as ex:
        print(f"[WARN] DDG search '{query[:40]}': {ex}")
        return []


def boost_single_source_clusters(clusters: list[list[dict]], top_n: int) -> None:
    """
    For each top candidate cluster with < 2 unique sources,
    do a web news search to find additional coverage.
    Modifies clusters in-place.
    """
    candidates = clusters[:top_n]
    searches   = 0
    boosted    = 0
    for cluster in candidates:
        unique = {e["source"] for e in cluster}
        if len(unique) >= 2:
            continue
        headline = cluster[0]["title"]
        category = cluster[0]["category"]
        print(f"[SEARCH] Only 1 source — searching DDG: {headline[:55]}")
        additional = search_web_news(headline, unique, category)
        if additional:
            cluster.extend(additional[:4])
            boosted += 1
            print(f"[SEARCH] → found {min(len(additional), 4)} more sources "
                  f"({', '.join(a['source'] for a in additional[:4])})")
        else:
            print(f"[SEARCH] → no additional sources found")
        searches += 1
        time.sleep(0.3)   # gentle rate limiting

    print(f"[INFO] DDG: {searches} searches, {boosted} clusters boosted")


# ── Full Text ─────────────────────────────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT,
                            allow_redirects=True)
        text = trafilatura.extract(resp.text, include_comments=False,
                                   include_tables=False)
        if text and len(text) > 80 and not is_bot_check(text):
            return text[:3000]
    except Exception as ex:
        print(f"[WARN] Fetch {url[:60]}: {ex}")
    return ""


def get_excerpt(entry: dict) -> str:
    text = entry.get("full_text") or entry.get("snippet") or entry.get("title", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if is_bot_check(text):
        return ""
    if len(text) > EXCERPT_CHARS:
        cut = text[:EXCERPT_CHARS]
        dot = cut.rfind(". ")
        return (cut[:dot + 1] if dot > 80 else cut) + "…"
    return text


# ── TF-IDF Clustering ─────────────────────────────────────────────────────────

def _cluster_group(entries: list[dict], stop_words, threshold: float) -> list[list[dict]]:
    """Cluster a group of same-language entries with given stop words and threshold."""
    if not entries:
        return []
    texts    = [f"{e['title']} {e['snippet']}" for e in entries]
    sw       = stop_words if isinstance(stop_words, str) else list(stop_words)
    vec      = TfidfVectorizer(stop_words=sw, max_features=15000,
                               ngram_range=(1, 2), sublinear_tf=True, min_df=1)
    matrix   = vec.fit_transform(texts)
    sim      = cosine_similarity(matrix)
    assigned = [False] * len(entries)
    clusters = []
    for i in range(len(entries)):
        if assigned[i]:
            continue
        cluster    = [entries[i]]
        assigned[i] = True
        for j in range(i + 1, len(entries)):
            if not assigned[j] and sim[i][j] >= threshold:
                cluster.append(entries[j])
                assigned[j] = True
        clusters.append(cluster)
    return clusters


def cluster_entries(entries: list[dict]) -> list[list[dict]]:
    """
    Cluster entries separately by language to avoid false cross-language similarity.
    English uses English stop words and threshold 0.15.
    Russian uses Russian stop words and a stricter threshold 0.30 (fewer false positives).
    """
    en_entries = [e for e in entries if e.get("lang") != "ru"]
    ru_entries = [e for e in entries if e.get("lang") == "ru"]

    clusters  = _cluster_group(en_entries, "english", CLUSTER_THRESHOLD)
    clusters += _cluster_group(ru_entries, RUSSIAN_STOP_WORDS, 0.30)

    clusters.sort(key=lambda c: len(c), reverse=True)
    multi_source = sum(1 for c in clusters if len({e["source"] for e in c}) >= 2)
    print(f"[INFO] {len(clusters)} clusters total ({len(en_entries)} EN, {len(ru_entries)} RU), "
          f"{multi_source} already have ≥2 sources")
    return clusters


# ── Enrich with full text ─────────────────────────────────────────────────────

def enrich_clusters(clusters: list[list[dict]], top_n: int) -> list[list[dict]]:
    top = clusters[:top_n]
    for i, cluster in enumerate(top):
        print(f"[INFO] [{i+1}/{len(top)}] Fetching: {cluster[0]['title'][:55]}")
        for entry in cluster[:MAX_PERSPECTIVES]:
            if entry["link"] and not entry["full_text"]:
                entry["full_text"] = fetch_full_text(entry["link"])
    return top


# ── Build story ───────────────────────────────────────────────────────────────

def build_story(cluster: list[dict]) -> dict | None:
    def priority(e):
        try:    return SOURCE_PRIORITY.index(e["source"])
        except: return len(SOURCE_PRIORITY)

    sorted_c   = sorted(cluster, key=priority)
    en_entries = [e for e in sorted_c if e.get("lang") == "en"]
    headline   = (en_entries or sorted_c)[0]["title"]
    category   = Counter(e["category"] for e in cluster).most_common(1)[0][0]

    seen, perspectives = set(), []
    for e in sorted_c:
        if e["source"] not in seen:
            excerpt = get_excerpt(e)
            if excerpt:
                perspectives.append({
                    "source":   e["source"],
                    "lang":     e.get("lang", "en"),
                    "headline": e["title"],
                    "excerpt":  excerpt,
                    "url":      e["link"],
                })
                seen.add(e["source"])
        if len(perspectives) >= MAX_PERSPECTIVES:
            break

    # HARD RULE: must have real text from at least 2 different sources
    if len(perspectives) < MIN_PERSPECTIVES:
        return None

    return {
        "category":     category,
        "headline_en":  headline,
        "coverage":     len({e["source"] for e in cluster}),
        "perspectives": perspectives,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    start = datetime.now(timezone.utc)
    print(f"[START] {start.isoformat()} | target {MAX_STORIES} stories | {HOURS_BACK}h window")

    entries = fetch_rss_entries(HOURS_BACK)
    if not entries:
        print("[WARN] No entries — aborting.")
        return

    clusters = cluster_entries(entries)

    # For single-source clusters in top candidates, search DuckDuckGo
    boost_single_source_clusters(clusters, top_n=MAX_STORIES * 3)

    # Re-sort after boosting (some clusters grew)
    clusters.sort(key=lambda c: len({e["source"] for e in c}), reverse=True)

    # Fetch full text for top candidates (3x quota to survive MIN_PERSPECTIVES filter)
    candidates = enrich_clusters(clusters, top_n=MAX_STORIES * 3)

    # Build stories, enforce hard MIN_PERSPECTIVES rule
    stories = []
    for c in candidates:
        s = build_story(c)
        if s:
            stories.append(s)
        if len(stories) >= MAX_STORIES:
            break

    print(f"[INFO] {len(stories)} stories with ≥{MIN_PERSPECTIVES} real perspectives")
    if len(stories) < 25:
        print("[WARN] Fewer than 25 stories — DDG may be rate-limiting or sources are thin today")

    output = {
        "collected_at":  start.isoformat(),
        "total_sources": len(FEEDS),
        "total_entries": len(entries),
        "story_count":   len(stories),
        "stories":       stories,
    }
    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    print(f"[DONE] {len(stories)} stories → news_data.json ({elapsed:.0f}s)")


if __name__ == "__main__":
    main()
