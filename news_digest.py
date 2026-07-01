#!/usr/bin/env python3
"""
Daily News Digest — No AI API required.
Groups articles by TF-IDF similarity, summarises with LSA extractive summarisation.
"""

import os
import random
import smtplib
import feedparser
import trafilatura
import requests
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from collections import Counter
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Download NLTK data required by sumy
for _pkg in ["punkt", "punkt_tab", "stopwords"]:
    nltk.download(_pkg, quiet=True)

# ── Config ────────────────────────────────────────────────────────────────────
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL", "sullaro@yandex.ru")
EMAIL_USER         = os.environ.get("EMAIL_USER")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
MAX_STORIES        = int(os.environ.get("MAX_STORIES", "35"))
HOURS_BACK         = int(os.environ.get("HOURS_BACK", "24"))
FULL_TEXT_CHARS    = 3000
FETCH_TIMEOUT      = 10
SUMMARY_SENTENCES  = 5      # key sentences per story
CLUSTER_THRESHOLD  = 0.20   # cosine similarity to group articles together

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/1.0)"}

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
                        published = datetime(*getattr(e, attr)[:6], tzinfo=timezone.utc)
                        break
                if published and published < cutoff:
                    continue
                entries.append({
                    "source":    source,
                    "category":  category,
                    "title":     e.get("title", "").strip(),
                    "snippet":   e.get("summary", e.get("description", ""))[:400].strip(),
                    "link":      e.get("link", ""),
                    "full_text": "",
                })
        except Exception as ex:
            print(f"[WARN] RSS {source}: {ex}")

    random.shuffle(entries)
    entries = entries[:500]
    print(f"[INFO] Fetched {len(entries)} entries from {len(FEEDS)} feeds")
    return entries


# ── Full Text Fetching ────────────────────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        text = trafilatura.extract(resp.text, include_comments=False, include_tables=False)
        if text:
            return text[:FULL_TEXT_CHARS]
    except Exception as ex:
        print(f"[WARN] Fetch {url[:60]}: {ex}")
    return ""


# ── TF-IDF Clustering ─────────────────────────────────────────────────────────

def cluster_entries(entries: list[dict]) -> list[list[dict]]:
    """Group entries about the same event using cosine similarity of TF-IDF vectors."""
    texts = [f"{e['title']} {e['snippet']}" for e in entries]

    vectorizer = TfidfVectorizer(
        stop_words="english",
        max_features=10000,
        ngram_range=(1, 2),
        sublinear_tf=True,
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

    # More sources covering a story = more important
    clusters.sort(key=lambda c: len(c), reverse=True)
    print(f"[INFO] {len(clusters)} topic clusters, top cluster has {len(clusters[0])} sources")
    return clusters


# ── Enrich top clusters with full article text ────────────────────────────────

def enrich_clusters(clusters: list[list[dict]], top_n: int) -> list[list[dict]]:
    top = clusters[:top_n]
    for i, cluster in enumerate(top):
        title_preview = cluster[0]["title"][:50]
        print(f"[INFO] [{i+1}/{top_n}] Fetching full text: {title_preview}")
        for entry in cluster[:3]:   # up to 3 sources per story
            if entry["link"]:
                entry["full_text"] = fetch_full_text(entry["link"])
    return top


# ── LSA Summarisation ─────────────────────────────────────────────────────────

def summarise_cluster(cluster: list[dict]) -> dict:
    # Headline = title of the most-covered article
    headline = cluster[0]["title"]

    # Dominant category
    category = Counter(e["category"] for e in cluster).most_common(1)[0][0]

    # Deduplicated sources
    seen, sources = set(), []
    for e in cluster:
        if e["source"] not in seen:
            sources.append({"name": e["source"], "url": e["link"]})
            seen.add(e["source"])

    # Combine available text: prefer full_text, fall back to snippet
    combined = "\n\n".join(
        e["full_text"] if e["full_text"] else e["snippet"]
        for e in cluster[:5]
        if e["full_text"] or e["snippet"]
    ).strip() or headline

    # LSA extractive summary
    try:
        parser    = PlaintextParser.from_string(combined, Tokenizer("english"))
        summariser = LsaSummarizer()
        sentences = summariser(parser.document, SUMMARY_SENTENCES)
        summary   = " ".join(str(s) for s in sentences).strip()
        if not summary:
            summary = combined[:600]
    except Exception:
        summary = combined[:600]

    return {
        "category": category,
        "headline": headline,
        "summary":  summary,
        "sources":  sources[:5],
        "coverage": len(cluster),
    }


# ── HTML Rendering ────────────────────────────────────────────────────────────

def render_html(stories: list[dict], generated_at: str) -> str:
    cards = ""
    for s in stories:
        cov = s.get("coverage", 1)
        badge = (
            f'<span style="font-size:11px;color:#94a3b8;margin-left:6px;">'
            f'{cov} sources</span>'
        ) if cov > 1 else ""

        sources_html = "".join(
            f'<a href="{src["url"]}" style="display:inline-block;margin:3px 6px 3px 0;'
            f'padding:4px 12px;background:#f0f4ff;border-radius:20px;color:#2563eb;'
            f'text-decoration:none;font-size:12px;font-weight:500;">{src["name"]}</a>'
            for src in s.get("sources", [])
        )

        cards += f"""
      <div style="background:#fff;border-radius:12px;padding:24px 28px;margin-bottom:20px;
                  box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #2563eb;">
        <div style="font-size:11px;font-weight:700;letter-spacing:.8px;color:#64748b;
                    text-transform:uppercase;margin-bottom:8px;">
          {s.get("category","")} {badge}
        </div>
        <h2 style="margin:0 0 12px;font-size:18px;font-weight:700;color:#0f172a;
                   line-height:1.35;">{s.get("headline","")}</h2>
        <p style="margin:0 0 16px;font-size:15px;color:#334155;line-height:1.75;">
          {s.get("summary","")}
        </p>
        <div>{sources_html}</div>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Daily Digest</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif;">

  <div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:40px 32px 32px;">
    <div style="max-width:660px;margin:0 auto;">
      <div style="font-size:11px;letter-spacing:2px;color:#93c5fd;
                  text-transform:uppercase;margin-bottom:8px;">Daily Briefing</div>
      <h1 style="margin:0 0 6px;font-size:28px;font-weight:800;color:#fff;">
        🌐 World News Digest
      </h1>
      <div style="font-size:13px;color:#bfdbfe;">
        {generated_at} · {len(stories)} stories
      </div>
    </div>
  </div>

  <div style="max-width:660px;margin:0 auto;padding:28px 16px 48px;">
    {cards}
    <div style="text-align:center;padding-top:16px;border-top:1px solid #e2e8f0;">
      <p style="font-size:12px;color:#94a3b8;margin:0;">
        Reuters · AP · BBC · The Economist · FT · Bloomberg · WSJ ·
        MIT Tech Review · Wired · HBR · Forbes · Adweek · Marketing Week ·
        The Drum · Retail Dive · Food Dive and more<br>
        Generated via GitHub Actions · No AI API required
      </p>
    </div>
  </div>
</body>
</html>"""


# ── Email ─────────────────────────────────────────────────────────────────────

def send_email(html_body: str, subject: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))
    print(f"[INFO] Sending to {RECIPIENT_EMAIL} …")
    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
    print("[INFO] Email sent ✓")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    moscow_tz  = timezone(timedelta(hours=3))
    now_moscow = datetime.now(timezone.utc).astimezone(moscow_tz)
    date_str   = now_moscow.strftime("%A, %d %B %Y · %H:%M MSK")
    subject    = f"📰 Daily Digest — {now_moscow.strftime('%d %b %Y')}"

    entries = fetch_rss_entries(HOURS_BACK)
    if not entries:
        print("[WARN] No entries — aborting.")
        return

    clusters = cluster_entries(entries)
    if not clusters:
        print("[WARN] No clusters — aborting.")
        return

    top_clusters = enrich_clusters(clusters, MAX_STORIES)
    stories      = [summarise_cluster(c) for c in top_clusters]

    html = render_html(stories, date_str)
    send_email(html, subject)
    print("[DONE] Digest delivered.")


if __name__ == "__main__":
    main()
