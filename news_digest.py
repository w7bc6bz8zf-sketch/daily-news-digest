#!/usr/bin/env python3
"""
Daily News Digest — двухпроходный агрегатор:
  Проход 1: отбор топ-историй из RSS по заголовкам (Google Gemini)
  Проход 2: загрузка полного текста → глубокий анализ (Google Gemini)
"""

import os
import json
import time
import random
import smtplib
import feedparser
import trafilatura
import requests
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── Config ────────────────────────────────────────────────────────────────────
RECIPIENT_EMAIL    = os.environ.get("RECIPIENT_EMAIL", "sullaro@yandex.ru")
EMAIL_USER         = os.environ.get("EMAIL_USER")
EMAIL_APP_PASSWORD = os.environ.get("EMAIL_APP_PASSWORD")
YANDEX_API_KEY     = os.environ.get("YANDEX_API_KEY")
YANDEX_FOLDER_ID   = os.environ.get("YANDEX_FOLDER_ID")
MAX_STORIES        = int(os.environ.get("MAX_STORIES", "35"))
HOURS_BACK         = int(os.environ.get("HOURS_BACK", "24"))
FULL_TEXT_CHARS    = 2000
FETCH_TIMEOUT      = 12

YANDEX_GPT_URL = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

def call_llm(prompt: str, max_tokens: int = 8000) -> str:
    resp = requests.post(
        YANDEX_GPT_URL,
        headers={
            "Authorization": f"Api-Key {YANDEX_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt/latest",
            "completionOptions": {
                "stream": False,
                "temperature": 0.3,
                "maxTokens": str(max_tokens),
            },
            "messages": [{"role": "user", "text": prompt}],
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["result"]["alternatives"][0]["message"]["text"].strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/1.0)"
}

# ── RSS feeds ─────────────────────────────────────────────────────────────────
FEEDS = [
    # World & Politics
    ("Reuters",           "🌍 Мир",            "https://feeds.reuters.com/reuters/topNews"),
    ("AP News",           "🌍 Мир",            "https://feeds.apnews.com/rss/apf-topnews"),
    ("BBC World",         "🌍 Мир",            "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("The Guardian",      "🌍 Мир",            "https://www.theguardian.com/world/rss"),
    ("Al Jazeera",        "🌍 Мир",            "https://www.aljazeera.com/xml/rss/all.xml"),
    ("Foreign Policy",    "🌍 Мир",            "https://foreignpolicy.com/feed/"),
    ("Politico",          "🌍 Мир",            "https://www.politico.com/rss/politicopicks.xml"),

    # Economics & Markets
    ("Reuters Business",  "📈 Экономика",      "https://feeds.reuters.com/reuters/businessNews"),
    ("The Economist",     "📈 Экономика",      "https://www.economist.com/finance-and-economics/rss.xml"),
    ("The Economist W.",  "🌍 Мир",            "https://www.economist.com/international/rss.xml"),
    ("The Economist B.",  "💼 Бизнес",         "https://www.economist.com/business/rss.xml"),
    ("FT",                "📈 Экономика",      "https://www.ft.com/rss/home/uk"),
    ("Bloomberg",         "📈 Экономика",      "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Tech",    "💡 Технологии",     "https://feeds.bloomberg.com/technology/news.rss"),
    ("WSJ",               "📈 Экономика",      "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),

    # Technology & AI
    ("MIT Tech Review",   "💡 Технологии",     "https://www.technologyreview.com/feed/"),
    ("Ars Technica",      "💡 Технологии",     "https://feeds.arstechnica.com/arstechnica/index"),
    ("The Verge",         "💡 Технологии",     "https://www.theverge.com/rss/index.xml"),
    ("Wired",             "💡 Технологии",     "https://www.wired.com/feed/rss"),
    ("TechCrunch",        "💡 Технологии",     "https://techcrunch.com/feed/"),

    # Business, Strategy & Trends
    ("HBR",               "💼 Бизнес",         "http://feeds.hbr.org/harvardbusiness"),
    ("Forbes",            "💼 Бизнес",         "https://www.forbes.com/innovation/feed/"),
    ("McKinsey",          "💼 Бизнес",         "https://www.mckinsey.com/insights/rss"),
    ("Fast Company",      "💼 Бизнес",         "https://www.fastcompany.com/latest/rss"),
    ("Inc.",              "💼 Бизнес",         "https://www.inc.com/rss"),
    ("Business Insider",  "💼 Бизнес",         "https://feeds.businessinsider.com/custom/all"),

    # Marketing & Advertising
    ("Adweek",            "📣 Маркетинг",      "https://www.adweek.com/feed/"),
    ("Marketing Week",    "📣 Маркетинг",      "https://www.marketingweek.com/feed/"),
    ("The Drum",          "📣 Маркетинг",      "https://www.thedrum.com/rss.xml"),
    ("Campaign",          "📣 Маркетинг",      "https://www.campaignlive.co.uk/rss"),
    ("Ad Age",            "📣 Маркетинг",      "https://adage.com/rss"),

    # FMCG & Retail
    ("Retail Dive",       "🛒 FMCG & Ритейл", "https://www.retaildive.com/feeds/news/"),
    ("Food Dive",         "🛒 FMCG & Ритейл", "https://www.fooddive.com/feeds/news/"),
    ("Grocery Dive",      "🛒 FMCG & Ритейл", "https://www.grocerydive.com/feeds/news/"),
    ("Consumer Goods",    "🛒 FMCG & Ритейл", "https://www.consumergoods.com/rss.xml"),
]


# ── Проход 1: сбор RSS ────────────────────────────────────────────────────────

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
                    "source":   source,
                    "category": category,
                    "title":    e.get("title", "").strip(),
                    "snippet":  e.get("summary", e.get("description", ""))[:300].strip(),
                    "link":     e.get("link", ""),
                })
        except Exception as ex:
            print(f"[WARN] RSS {source}: {ex}")

    print(f"[INFO] Собрано {len(entries)} записей из {len(FEEDS)} фидов")

    # Перемешиваем, чтобы ни один источник не доминировал при обрезке
    random.shuffle(entries)
    return entries[:500]


# ── Проход 1: отбор топ-историй Claude ───────────────────────────────────────

SELECT_PROMPT = """Ты — редактор мирового новостного дайджеста. Ниже JSON-список новостных записей за 24 часа.

Задача: выбери {max_stories} самых важных историй и сгруппируй их по событию.
Для каждой истории верни список URL всех источников, которые её освещают.

Верни JSON-массив (без markdown, без лишнего текста):
[
  {{
    "category": "🌍 Мир",
    "working_title": "Рабочий заголовок события",
    "sources": [
      {{"name": "Reuters", "url": "https://..."}},
      {{"name": "BBC",     "url": "https://..."}}
    ]
  }}
]

Правила отбора:
- Предпочитай истории, освещённые 2+ источниками.
- Исключи: спорт, светскую хронику, развлечения, локальные новости.
- Обязательно включи истории из категорий: маркетинг, бизнес-тренды, FMCG/ритейл, технологии/AI — если они есть.
- Используй только реальные URL из данных.

Записи:
{entries_json}
"""

def select_stories(entries: list[dict]) -> list[dict]:
    payload = [{"source": e["source"], "category": e["category"],
                "title": e["title"], "snippet": e["snippet"], "url": e["link"]}
               for e in entries]

    prompt = SELECT_PROMPT.format(
        max_stories=MAX_STORIES,
        entries_json=json.dumps(payload, ensure_ascii=False)
    )

    print("[INFO] Проход 1: отбор историй …")
    raw = call_llm(prompt, max_tokens=4000)
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    selected = json.loads(raw)
    print(f"[INFO] Отобрано {len(selected)} историй")
    return selected


# ── Проход 2: загрузка полного текста ────────────────────────────────────────

def fetch_full_text(url: str) -> str:
    """Загружает полный текст статьи через trafilatura."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=FETCH_TIMEOUT)
        text = trafilatura.extract(resp.text, include_comments=False,
                                   include_tables=False, no_fallback=False)
        if text:
            return text[:FULL_TEXT_CHARS]
    except Exception as ex:
        print(f"[WARN] Не удалось загрузить {url}: {ex}")
    return ""

def enrich_with_full_text(selected: list[dict], rss_entries: list[dict]) -> list[dict]:
    """Добавляет полный текст к каждому источнику. Fallback — RSS-сниппет."""
    # Строим индекс сниппетов по URL для быстрого поиска
    snippet_index = {e["link"]: e.get("snippet", "") for e in rss_entries}

    for story in selected:
        for src in story.get("sources", []):
            print(f"[INFO] Загружаю: {src['name']} — {src['url'][:70]}")
            full = fetch_full_text(src["url"])
            if full:
                src["content"] = full
            else:
                # Fallback: сниппет из RSS или заголовок
                fallback = snippet_index.get(src["url"], "")
                src["content"] = fallback if fallback else "[полный текст недоступен]"
                print(f"[INFO]   → использую RSS-сниппет для {src['name']}")
    return selected


# ── Проход 2: глубокий анализ Claude ─────────────────────────────────────────

ANALYSE_PROMPT = """Ты — аналитик мирового уровня, пишущий ежедневный дайджест для образованного читателя.

Ниже JSON с {n} историями. У каждой истории есть поле "content" — полный текст или сниппет из RSS.

КРИТИЧЕСКИ ВАЖНО: верни ровно {n} историй — по одной на каждую запись во входных данных. Не пропускай ни одну, даже если content короткий или помечен как недоступный — в таком случае пиши по заголовку и общему контексту.

Верни JSON-массив (без markdown, без лишнего текста):
[
  {{
    "category": "🌍 Мир",
    "headline": "Точный, информативный заголовок на русском (не кликбейт)",
    "summary": "4–6 предложений на русском. Объясни: что произошло, почему это важно, какие последствия, как оценивают разные источники. Пиши аналитически — добавляй контекст, причины, возможные сценарии. Тон: умный журнал уровня The Economist.",
    "sources": [
      {{"name": "Reuters", "url": "https://..."}},
      {{"name": "BBC",     "url": "https://..."}}
    ]
  }}
]

Правила:
- Пиши для КАЖДОЙ из {n} историй — без исключений.
- Используй цифры, цитаты и детали где есть полный текст.
- Если источники расходятся — покажи обе стороны.
- Заголовок и резюме — только на русском. Названия брендов/компаний — в оригинале.
- Сохрани исходную категорию и реальные URL источников.

Истории:
{stories_json}
"""

def analyse_stories(selected: list[dict]) -> list[dict]:
    prompt = ANALYSE_PROMPT.format(
        n=len(selected),
        stories_json=json.dumps(selected, ensure_ascii=False)
    )

    print("[INFO] Проход 2: глубокий анализ …")
    raw = call_llm(prompt, max_tokens=8000)
    raw = raw.lstrip("```json").lstrip("```").rstrip("```").strip()
    stories = json.loads(raw)
    print(f"[INFO] Готово {len(stories)} аналитических историй")
    return stories


# ── HTML-шаблон ───────────────────────────────────────────────────────────────

def render_html(stories: list[dict], generated_at: str) -> str:
    story_cards = ""
    for s in stories:
        sources_html = "".join(
            f'<a href="{src["url"]}" style="display:inline-block;margin:3px 6px 3px 0;'
            f'padding:4px 12px;background:#f0f4ff;border-radius:20px;color:#2563eb;'
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
        <p style="margin:0 0 16px;font-size:15px;color:#334155;line-height:1.75;">
          {s.get('summary','')}
        </p>
        <div>{sources_html}</div>
      </div>"""

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ежедневный дайджест</title>
</head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,
             'Segoe UI',Helvetica,Arial,sans-serif;">

  <div style="background:linear-gradient(135deg,#1e3a8a 0%,#2563eb 100%);padding:40px 32px 32px;">
    <div style="max-width:660px;margin:0 auto;">
      <div style="font-size:11px;letter-spacing:2px;color:#93c5fd;text-transform:uppercase;
                  margin-bottom:8px;">Ежедневный дайджест</div>
      <h1 style="margin:0 0 6px;font-size:28px;font-weight:800;color:#fff;">🌐 Мировые новости</h1>
      <div style="font-size:13px;color:#bfdbfe;">{generated_at} · {len(stories)} историй</div>
    </div>
  </div>

  <div style="max-width:660px;margin:0 auto;padding:28px 16px 48px;">
    {story_cards}
    <div style="text-align:center;padding-top:16px;border-top:1px solid #e2e8f0;">
      <p style="font-size:12px;color:#94a3b8;margin:0;">
        Reuters · AP · BBC · The Economist · FT · Bloomberg · WSJ · MIT Tech Review ·
        Wired · TechCrunch · HBR · Forbes · McKinsey · Adweek · Marketing Week ·
        The Drum · Ad Age · Retail Dive · Food Dive · Grocery Dive и др.<br>
        Автоматически собирается через GitHub Actions + Claude
      </p>
    </div>
  </div>
</body>
</html>"""


# ── Отправка письма ───────────────────────────────────────────────────────────

def send_email(html_body: str, subject: str) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_USER
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    print(f"[INFO] Отправляю на {RECIPIENT_EMAIL} …")
    with smtplib.SMTP_SSL("smtp.yandex.ru", 465) as server:
        server.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        server.sendmail(EMAIL_USER, RECIPIENT_EMAIL, msg.as_string())
    print("[INFO] Письмо отправлено ✓")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    moscow_tz  = timezone(timedelta(hours=3))
    now_moscow = datetime.now(timezone.utc).astimezone(moscow_tz)
    date_str   = now_moscow.strftime("%A, %d %B %Y · %H:%M МСК")
    subject    = f"📰 Дайджест — {now_moscow.strftime('%d %b %Y')}"

    # 1. Сбор RSS
    entries = fetch_rss_entries(HOURS_BACK)
    if not entries:
        print("[WARN] Нет записей — выходим.")
        return

    # 2. Отбор топ-историй
    selected = select_stories(entries)

    # 3. Загрузка полных текстов
    selected = enrich_with_full_text(selected, entries)

    # 4. Глубокий анализ
    stories = analyse_stories(selected)

    # 5. Рендер и отправка
    html = render_html(stories, date_str)
    send_email(html, subject)
    print("[DONE] Дайджест доставлен.")


if __name__ == "__main__":
    main()
