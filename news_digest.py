#!/usr/bin/env python3
"""
Daily News Digest — fetches top stories from premium RSS feeds,
synthesises multi-source summaries via Claude, and sends an HTML email.
"""

import os
import json
import time
import smtplib
import feedparser
import anthropic
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL", "sullaro@yandex.ru")
GMAIL_USER         = os.environ.get("EMAIL_USER")
GMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
ANTHROPIC_API_KEY  = os.environ.get("ANTHROPIC_API_KEY")
MAX_STORIES        = int(os.environ.get("MAX_STORIES", "12"))   # stories in digest
HOURS_BACK         = int(os.environ.get("HOURS_BACK", "24"))    # look-back window

# ── RSS feeds ─────────────────────────────────────────────────────────────────
# Each tuple: (source_name, category, feed_url)
FEEDS = [
    # World & Politics
    ("Reuters",          "🌍 World",      "https://feeds.reuters.com/reuters/topNews"),
    ("AP News",          "🌍 World",      "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World",        "🌍 World",      "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian",     "🌍 World",      "https://www.theguardian.com/world/rss"),

    # Economics & Markets
    ("Reuters Business", "📈 Economy",    "https://feeds.reuters.com/reuters/businessNews"),
    ("The Economist",    "📈 Economy",    "https://www.economist.com/latest/rss.xml"),
    ("FT",               "📈 Economy",    "https://www.ft.com/rss/home/uk"),

    # Technology & AI
    ("MIT Tech Review",  "💡 Tech & AI", "https://www.technologyreview.com/feed/"),
    ("Ars Technica",     "💡 Tech & AI", "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",        "💡 Tech & AI", "https://www.theverge.com/rss/index.xml"),

    # Business & FMCG
    ("HBR",              "💼 Business",   "http://feeds.hbr.org/harvardbusiness"),
    ("Forbes",           "💼 Business",   "https://www.forbes.com/innovation/feed/"),
]


# ── Feed fetching ─────────────────────────────────────────────────────────────

def fetch_recent_entries(hours_back: int = 24) -> list[dict]:
    """Fetch all RSS entries from the last `hours_back` hours."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    entries = []

    for source, category, url in FEEDS:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:15]:   # limit per feed
                published = None
                for attr in ("published_parsed", "updated_parsed"):
                    if hasattr(e, attr) and getattr(e, attr):
                        published = datetime(*getattr(e, attr)[:6], tzinfo=timezone.utc)
                        break
                # include if within window OR timestamp unavailable (keep recent-looking items)
                if published and published < cutoff:
                    continue
                entries.append({
                    "source":   source,
                    "category": category,
                    "title":    e.get("title", "").strip(),
                    "summary":  e.get("summary", e.get("description", ""))[:600].strip(),
                    "link":     e.get("link", ""),
                    "published": published.isoformat() if published else "",
                })
        except Exception as ex:
            print(f"[WARN] Failed to fetch {source}: {ex}")

    print(f"[INFO] Fetched {len(entries)} entries from {len(FEEDS)} feeds")
    return entries


# ── Claude synthesis ──────────────────────────────────────────────────────────

CLUSTER_PROMPT = """You are a senior world editor. Below is a JSON list of news entries from the past 24 hours.

Your tasks:
1. Identify the {max_stories} most important, globally significant stories.
2. For each story, group all entries that cover the same event (even if from different sources).
3. Return a JSON array (no markdown, no extra text) with exactly this shape:

[
  {{
    "category": "🌍 World",        // use the most fitting category from the entries
    "headline": "Short punchy headline",
    "summary": "2–3 sentence synthesis combining perspectives from multiple sources. Be factual, balanced, mention disagreements if any.",
    "sources": [
      {{"name": "Reuters", "url": "https://..."}},
      {{"name": "BBC",     "url": "https://..."}}
    ]
  }}
]

Rules:
- Prefer stories covered by 2+ sources — that signals real importance.
- Avoid entertainment, sports, and celebrity gossip.
- Prioritise: geopolitics, macro-economy, AI/tech breakthroughs, major business moves, FMCG & consumer trends.
- Write summaries in English, neutral tone.
- Include real URLs from the entries.

Entries:
{entries_json}
"""


def synthesise_with_claude(entries: list[dict]) -> list[dict]:
    """Use Claude to cluster, rank and summarise the entries."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # Trim payload to avoid token limits
    trimmed = [
        {"source": e["source"], "category": e["category"],
         "title": e["title"], "summary": e["summary"][:400], "link": e["link"]}
        for e in entries
    ]

    prompt = CLUSTER_PROMPT.format(
        max_stories=MAX_STORIES,
        entries_json=json.dumps(trimmed, ensure_ascii=False, indent=2)
    )

    print("[INFO] Calling Claude for synthesis …")
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",   # fast + cheap for daily automation
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    raw = message.content[0].text.strip()
    # strip possible markdown code fences
    if raw.startswith("```"):
        raw = "\n".join(raw.split("\n")[1:])
        if raw.endswith("```"):
            raw = raw[:-3]

    stories = json.loads(raw)
    print(f"[INFO] Claude returned {len(stories)} stories")
    return stories


# ── HTML template ─────────────────────────────────────────────────────────────

def render_html(stories: list[dict], generated_at: str) -> str:
    story_cards = ""
    for s in stories:
        sources_html = "".join(
            f'<a href="{src["url"]}" style="display:inline-block;margin:3px 6px 3px 0;'
            f'padding:3px 10px;background:#f0f4ff;border-radius:20px;color:#2563eb;'
            f'text-decoration:none;font-size:12px;font-weight:500;">{src["name"]}</a>'
            for src in s.get("sources", [])
        )

        story_cards += f"""
      <div style="background:#fff;border-radius:12px;padding:24px 28px;margin-bottom:20px;
                  box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #2563eb;">
        <div style="font-size:11px;font-weight:700;letter-spacing:.8px;color:#64748b;
                    text-transform:uppercase;margin-bottom:8px;">{s.get('category','')}</div>
        <h2 style="margin:0 0 12px;font-size:18px;font-weight:700;color:#0f172a;
                   line-height:1.35;">{s.get('headline','')}</h2>
        <p style="margin:0 0 16px;font-size:15px;color:#334155;line-height:1.7;">
          {s.get('summary','')}
        </p>
        <div>{sources_html}</div>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Daily Digest</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Helvetica,Arial,sans-serif;">

  <!-- Header -->
  <div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:40px 32px 32px;">
    <div style="max-width:640px;margin:0 auto;">
      <div style="font-size:11px;letter-spacing:2px;color:#93c5fd;text-transform:uppercase;
                  margin-bottom:8px;">Your Daily Briefing</div>
      <h1 style="margin:0 0 6px;font-size:28px;font-weight:800;color:#fff;">
        🌐 World News Digest
      </h1>
      <div style="font-size:13px;color:#bfdbfe;">{generated_at} · Top {len(stories)} stories</div>
    </div>
  </div>

  <!-- Body -->
  <div style="max-width:640px;margin:0 auto;padding:28px 16px 48px;">
    {story_cards}

    <!-- Footer -->
    <div style="text-align:center;padding-top:16px;border-top:1px solid #e2e8f0;">
      <p style="font-size:12px;color:#94a3b8;margin:0;">
        Sources: Reuters · AP · BBC · The Economist · FT · MIT Tech Review · Ars Technica ·
        The Verge · HBR · Forbes · The Guardian<br>
        Generated automatically via GitHub Actions + Claude
      </p>
    </div>
  </div>

</body>
</html>"""


# ── Email sending ─────────────────────────────────────────────────────────────

def send_email(html_body: str, subject: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = GMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    print(f"[INFO] Sending email to {RECIPIENT_EMAIL} …")
    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
    print("[INFO] Email sent ✓")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    now_utc   = datetime.now(timezone.utc)
    # Display time in Moscow (UTC+3)
    moscow_tz = timezone(timedelta(hours=3))
    now_moscow = now_utc.astimezone(moscow_tz)
    date_str  = now_moscow.strftime("%A, %d %B %Y · %H:%M MSK")
    subject   = f"📰 Daily Digest — {now_moscow.strftime('%d %b %Y')}"

    entries = fetch_recent_entries(HOURS_BACK)
    if not entries:
        print("[WARN] No entries fetched — aborting.")
        return

    stories = synthesise_with_claude(entries)
    html    = render_html(stories, date_str)
    send_email(html, subject)
    print("[DONE] Digest delivered.")


if __name__ == "__main__":
    main()
