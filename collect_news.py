#!/usr/bin/env python3
"""
collect_news.py — Part 1 of 2-part news digest pipeline.

Runs on GitHub Actions (cloud, no laptop needed):
  1. Fetches RSS from 38 sources (EN + RU)
  2. Clusters articles by topic with TF-IDF + cosine similarity
  3. Fetches full text for top stories
  4. Saves news_data.json to disk (GitHub Actions then commits it to the repo)

Part 2 (Claude in Cowork Scheduled Task) reads the JSON, translates to Russian,
generates HTML email, and sends it via Yandex SMTP.
"""

import json
import os
import random
import re
import feedparser
import requests
import trafilatura
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter
from datetime import datetime, timezone, timedelta

nltk.download("punkt",     quiet=True)
nltk.download("punkt_tab", quiet=True)

# ── Config ────────────────────────────────────────────────────────────────────
MAX_STORIES       = int(os.environ.get("MAX_STORIES", "40"))
HOURS_BACK        = int(os.environ.get("HOURS_BACK", "24"))
MAX_PERSPECTIVES  = 5      # max sources shown per story
EXCERPT_CHARS     = 400    # characters per source excerpt
FETCH_TIMEOUT     = 10
CLUSTER_THRESHOLD = 0.18
MIN_SOURCES       = 2      # skip single-source stories

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/1.0)"}

SOURCE_PRIORITY = [
    "Reuters", "AP News", "BBC World", "FT", "The Economist",
    "Bloomberg", "WSJ", "The Guardian", "Foreign Policy",
    "MIT Tech Review", "Wired", "HBR", "Adweek",
    "ТАСС", "РБК", "Коммерсант",
]

# ── RSS feeds ─────────────────────────────────────────────────────────────────
FEEDS = [
    # World & Politics
    ("Reuters",           "🌍 World",          "https://feeds.reuters.com/reuters/topNews"),
    ("AP News",           "🌍 World",          "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World",         "🌍 World",          "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian",      "🌍 World",          "https://www.theguardian.com/world/rss"),
    ("Al Jazeera",        "🌍 World",          "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Foreign Policy",    "🌍 World",          "https://foreignpolicy.com/feed/"),
    ("Politico",          "🌍 World",          "https://www.politico.com/rss/politicopicks.xml"),
    # Economics & Markets
    ("Reuters Business",  "📈 Economy",        "https://feeds.reuters.com/reuters/businessNews"),
    ("The Economist",     "📈 Economy",        "https://www.economist.com/finance-and-economics/rss.xml"),
    ("The Economist W.",  "🌍 World",          "https://www.economist.com/international/rss.xml"),
    ("The Economist B.",  "💼 Business",       "https://www.economist.com/business/rss.xml"),
    ("FT",                "📈 Economy",        "https://www.ft.com/rss/home/uk"),
    ("Bloomberg",         "📈 Economy",        "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Tech",    "💡 Tech & AI",      "https://feeds.bloomberg.com/technology/news.rss"),
    ("WSJ",               "📈 Economy",        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    # Technology & AI
    ("MIT Tech Review",   "💡 Tech & AI",      "https://www.technologyreview.com/feed/"),
    ("Ars Technica",      "💡 Tech & AI",      "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",         "💡 Tech & AI",      "https://www.theverge.com/rss/index.xml"),
    ("Wired",             "💡 Tech & AI",      "https://www.wired.com/feed/rss"),
    ("TechCrunch",        "💡 Tech & AI",      "https://techcrunch.com/feed/"),
    # Business & Strategy
    ("HBR",               "💼 Business",       "http://feeds.hbr.org/harvardbusiness"),
    ("Forbes",            "💼 Business",       "https://www.forbes.com/innovation/feed/"),
    ("Fast Company",      "💼 Business",       "https://www.fastcompany.com/latest/rss"),
    ("Inc.",              "💼 Business",       "https://www.inc.com/rss"),
    ("Business Insider",  "💼 Business",       "https://feeds.businessinsider.com/custom/all"),
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
]


# ── RSS Fetching ──────────────────────────────────────────────────────────────

def fetch_rss_entries(hours_back: int) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    entries = []
    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:20]:
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
                snippet = re.sub(r"<[^>]+>", " ", e.get("summary", e.get("description", "")))
                snippet = re.sub(r"\s+", " ", snippet).strip()[:500]
                if not title:
                    continue
                entries.append({
                    "source":    source,
                    "category":  category,
                    "title":     title,
                    "snippet":   snippet,
                    "link":      e.get("link", ""),
                    "full_text": "",
                    "lang":      "ru" if source in ("РБК", "Коммерсант", "ТАСС", "vc.ru") else "en",
                })
        except Exception as ex:
            print(f"[WARN] RSS {source}: {ex}")

    random.shuffle(entries)
    entries = entries[:600]
    print(f"[INFO] Fetched {len(entries)} entries from {len(FEEDS)} feeds")
    return entries


# ── Full Text ─────────────────────────────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
        if text:
            return text[:3000]
    except Exception as ex:
        print(f"[WARN] Fetch {url[:60]}: {ex}")
    return ""


def get_excerpt(entry: dict) -> str:
    text = entry.get("full_text") or entry.get("snippet") or entry.get("title", "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > EXCERPT_CHARS:
        cut      = text[:EXCERPT_CHARS]
        last_dot = cut.rfind(". ")
        return (cut[:last_dot + 1] if last_dot > 80 else cut) + "…"
    return text


# ── TF-IDF Clustering ─────────────────────────────────────────────────────────

def cluster_entries(entries: list[dict]) -> list[list[dict]]:
    # Use title + snippet for vectorization
    texts = [f"{e['title']} {e['snippet']}" for e in entries]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=12000,
        ngram_range=(1, 2),
        sublinear_tf=True,
        min_df=1,
    )
    matrix   = vectorizer.fit_transform(texts)
    sim      = cosine_similarity(matrix)

    assigned = [False] * len(entries)
    clusters = []

    for i in range(len(entries)):
        if assigned[i]:
            continue
        cluster = [entries[i]]
        assigned[i] = True
        for j in range(i + 1, len(entries)):
            if not assigned[j] and sim[i][j] >= CLUSTER_THRESHOLD:
                cluster.append(entries[j])
                assigned[j] = True
        clusters.append(cluster)

    # Sort by coverage (most sources first), then filter single-source
    clusters = [c for c in clusters if len(c) >= MIN_SOURCES]
    clusters.sort(key=lambda c: len(c), reverse=True)

    total_articles = sum(len(c) for c in clusters)
    print(f"[INFO] {len(clusters)} multi-source clusters · {total_articles} total articles")
    if clusters:
        print(f"[INFO] Top cluster: {clusters[0][0]['title'][:60]} ({len(clusters[0])} sources)")
    return clusters


# ── Enrich top clusters with full text ───────────────────────────────────────

def enrich_clusters(clusters: list[list[dict]], top_n: int) -> list[list[dict]]:
    top = clusters[:top_n]
    for i, cluster in enumerate(top):
        print(f"[INFO] [{i+1}/{top_n}] Fetching text: {cluster[0]['title'][:55]}")
        for entry in cluster[:MAX_PERSPECTIVES]:
            if entry["link"] and not entry["full_text"]:
                entry["full_text"] = fetch_full_text(entry["link"])
    return top


# ── Build story object ────────────────────────────────────────────────────────

def build_story(cluster: list[dict]) -> dict:
    def priority(e):
        try:
            return SOURCE_PRIORITY.index(e["source"])
        except ValueError:
            return len(SOURCE_PRIORITY)

    sorted_cluster = sorted(cluster, key=priority)
    # Prefer English headline as primary (for Claude to translate)
    en_entries = [e for e in sorted_cluster if e.get("lang") == "en"]
    headline_entry = (en_entries or sorted_cluster)[0]
    headline_en = headline_entry["title"]

    category = Counter(e["category"] for e in cluster).most_common(1)[0][0]

    seen, perspectives = set(), []
    for e in sorted_cluster:
        if e["source"] not in seen:
            excerpt = get_excerpt(e)
            if excerpt:
                perspectives.append({
                    "source":      e["source"],
                    "lang":        e.get("lang", "en"),
                    "headline":    e["title"],
                    "excerpt":     excerpt,
                    "url":         e["link"],
                })
                seen.add(e["source"])
        if len(perspectives) >= MAX_PERSPECTIVES:
            break

    return {
        "category":     category,
        "headline_en":  headline_en,   # Claude translates this to Russian
        "coverage":     len(cluster),  # total sources covering this topic
        "perspectives": perspectives,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    start_time = datetime.now(timezone.utc)
    print(f"[START] {start_time.isoformat()} — collecting news for past {HOURS_BACK}h")

    entries = fetch_rss_entries(HOURS_BACK)
    if not entries:
        print("[WARN] No entries — aborting.")
        return

    clusters = cluster_entries(entries)
    if not clusters:
        print("[WARN] No multi-source clusters — aborting.")
        return

    top_clusters = enrich_clusters(clusters, MAX_STORIES)
    stories      = [build_story(c) for c in top_clusters]

    output = {
        "collected_at":  start_time.isoformat(),
        "total_sources": len(FEEDS),
        "total_entries": len(entries),
        "story_count":   len(stories),
        "stories":       stories,
    }

    with open("news_data.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
    print(f"[DONE] Saved {len(stories)} stories to news_data.json ({elapsed:.0f}s)")


if __name__ == "__main__":
    main()
