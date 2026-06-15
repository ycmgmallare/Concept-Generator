# ===========================================================================
# server.py — Trend Finder Upgrade backend (Flask, port 5001)
#
# A trend-research API that:
#   1. GET /api/trending?q=  — searches Google News RSS + Reddit + Hacker News
#      and returns the top 5 trending ARTICLES for the query.
#   2. GET /api/extract?url= — fetches one article, pulls clean text, and asks
#      Gemini Flash to return the article's real ranked list of products/ideas
#      (ignoring nav/ads). Falls back to HTML heuristics if Gemini is
#      unavailable or returns nothing.
#   3. GET /api/health
#
# Runs SEPARATELY from the other tools (Node :3000, Flask app.py :5000, Node
# serve.mjs :3002). CORS is enabled so the page on :3002 can call this on :5001.
#
# Gemini is used for TEXT ANALYSIS ONLY — never image generation. The key lives
# in .env (GEMINI_API_KEY) and never reaches the browser.
# ===========================================================================

import json
import os
import re
from datetime import date
from urllib.parse import quote_plus, urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

# A real key is set (not the placeholder shipped in .env.example).
HAS_GEMINI = bool(GEMINI_API_KEY) and GEMINI_API_KEY != "your-gemini-key-here"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
BROWSER_HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
MAX_RESULTS = 5
GOOGLE_HOSTS = ("news.google.com", "consent.google.com")


# ---------------------------------------------------------------------------
# Step 1 — trending article search across three sources
# ---------------------------------------------------------------------------
def search_hacker_news(query):
    url = (
        "https://hn.algolia.com/api/v1/search"
        f"?query={quote_plus(query)}&tags=story&hitsPerPage=5"
    )
    out = []
    try:
        data = requests.get(url, headers={"User-Agent": UA}, timeout=12).json()
        for hit in data.get("hits", []):
            title = hit.get("title") or hit.get("story_title")
            if not title:
                continue
            link = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
            out.append(
                {"title": title, "link": link, "source": "Hacker News", "thumbnail": None}
            )
    except (requests.RequestException, ValueError):
        pass
    return out


def search_reddit(query, attempts=3):
    # Reddit's .json endpoint 403s automated requests, but the RSS feed works
    # (it just rate-limits with 429 under bursts — so we retry briefly, exactly
    # like the eBay scraper). Returns [] if Reddit keeps throttling us.
    url = (
        "https://www.reddit.com/search.rss"
        f"?q={quote_plus(query)}&limit=8&sort=relevance"
    )
    out = []
    feed = None
    for attempt in range(attempts):
        try:
            resp = requests.get(url, headers={"User-Agent": UA}, timeout=12)
        except requests.RequestException:
            return out
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            if feed.entries:
                break
        if attempt < attempts - 1:
            __import__("time").sleep(2)

    if not feed:
        return out

    for entry in feed.entries:
        link = getattr(entry, "link", "") or ""
        title = getattr(entry, "title", None)
        if not title or "/comments/" not in link:  # keep posts, skip subreddits/users
            continue
        sub_match = re.search(r"/r/([^/]+)/", link)
        sub = f"r/{sub_match.group(1)}" if sub_match else "reddit"
        # Reddit embeds a preview thumbnail in the entry's HTML content.
        content = ""
        if getattr(entry, "content", None):
            content = entry.content[0].get("value", "")
        elif getattr(entry, "summary", None):
            content = entry.summary
        thumb = None
        for src in re.findall(r'<img[^>]+src="([^"]+)"', content):
            if "preview.redd" in src or "external-preview" in src or "thumb" in src:
                thumb = src.replace("&amp;", "&")
                break
        out.append(
            {"title": title, "link": link, "source": f"Reddit · {sub}", "thumbnail": thumb}
        )
    return out


def search_google_news(query):
    url = (
        "https://news.google.com/rss/search"
        f"?q={quote_plus(query)}&hl=en-US&gl=US&ceid=US:en"
    )
    out = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:6]:
            title = getattr(entry, "title", None)
            if not title:
                continue
            source = None
            if getattr(entry, "source", None):
                source = entry.source.get("title")
            out.append(
                {
                    "title": title,
                    "link": getattr(entry, "link", None),
                    "source": source or "Google News",
                    "thumbnail": None,
                }
            )
    except Exception:
        pass
    return out


def merge_top(sources, limit=MAX_RESULTS):
    """Round-robin interleave results from each source, dedupe by title."""
    merged, seen = [], set()
    for items in __import__("itertools").zip_longest(*sources):
        for item in items:
            if not item:
                continue
            key = (item.get("title") or "").strip().lower()
            if not key or key in seen or not item.get("link"):
                continue
            seen.add(key)
            merged.append(item)
            if len(merged) >= limit:
                return merged
    return merged


@app.get("/api/trending")
def trending():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify(error="Please provide a search topic via ?q="), 400

    sources = [
        search_google_news(query),
        search_reddit(query),
        search_hacker_news(query),
    ]
    results = merge_top(sources)
    for i, item in enumerate(results, start=1):
        item["rank"] = i
    return jsonify(query=query, results=results, captured=date.today().isoformat())


# ---------------------------------------------------------------------------
# Step 2 + 8 — article fetch, Gemini extraction, heuristic fallback
# ---------------------------------------------------------------------------
def _norm_type(value):
    """Normalise Gemini's type field to exactly 'product' or 'idea'."""
    return "product" if str(value or "").strip().lower().startswith("prod") else "idea"


def extract_with_gemini(title, text):
    """Ask Gemini Flash to read the article and return the meaningful content as
    a labeled list: the products/tools it recommends AND its main ideas. Each
    item is {rank, text, type} with type 'product' or 'idea'. Returns items or
    None (None lets the caller fall back to HTML heuristics)."""
    if not HAS_GEMINI:
        return None
    prompt = (
        "You are reading the text of ONE online article. Extract the meaningful "
        "content a researcher would want, as a single ranked list. Include BOTH:\n"
        "  (a) PRODUCTS — any specific products, tools, services, models, or named "
        "items the article recommends, reviews, or ranks; and\n"
        "  (b) IDEAS — the article's main ideas, key takeaways, themes, or "
        "conclusions (the actual substance of the article, not just a list of names).\n"
        "If the article is a product round-up, list the products in the article's own "
        "order, then add its key ideas. If it is an essay/news piece with no products, "
        "still return its main ideas. ALWAYS return the key ideas even when there are "
        "no products. IGNORE navigation menus, sidebars, ads, cookie/newsletter "
        "prompts, related-article links, and comments.\n\n"
        "Return ONLY a JSON object of the form "
        '{"items":[{"rank":1,"text":"...","type":"product"},'
        '{"rank":2,"text":"...","type":"idea"}, ...]}. '
        "Each 'text' is concise (a name or a one-line takeaway); 'type' is exactly "
        '"product" or "idea". Aim for 5-15 items.\n\n'
        f"ARTICLE TITLE: {title or '(unknown)'}\n\nARTICLE TEXT:\n{text}"
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
    }
    try:
        resp = requests.post(
            GEMINI_URL,
            headers={"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=45,
        )
        if resp.status_code == 429:
            raise _RateLimited()
        resp.raise_for_status()
        data = resp.json()
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw)
        items = parsed.get("items") if isinstance(parsed, dict) else parsed
        cleaned = []
        for it in items or []:
            if isinstance(it, dict):
                txt = (it.get("text") or "").strip()
                typ = _norm_type(it.get("type"))
            else:
                txt, typ = str(it).strip(), "idea"
            if txt:
                cleaned.append({"text": txt, "type": typ})
        # Re-number sequentially for a clean 1..N list.
        for i, it in enumerate(cleaned, start=1):
            it["rank"] = i
        return cleaned or None
    except _RateLimited:
        raise
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


class _RateLimited(Exception):
    pass


def extract_with_html(text, soup_html):
    """Heuristic fallback (Step 8): pull the longest list-like run from HTML."""
    soup = BeautifulSoup(soup_html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    best = []
    # 1) Ordered lists are the strongest signal for a ranked listicle.
    for ol in soup.find_all("ol"):
        items = [li.get_text(" ", strip=True) for li in ol.find_all("li", recursive=False)]
        items = [t for t in items if 3 <= len(t) <= 200]
        if len(items) > len(best):
            best = items
    # 2) Otherwise, repeated H2/H3 headings often label each list entry.
    if len(best) < 3:
        heads = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
        heads = [h for h in heads if 3 <= len(h) <= 120]
        if len(heads) >= 3:
            best = heads

    # Heuristics can't reliably tell a product from a theme, so label everything
    # "idea" honestly rather than guessing.
    return [{"rank": i, "text": t, "type": "idea"} for i, t in enumerate(best[:25], start=1)]


@app.get("/api/extract")
def extract():
    url = (request.args.get("url") or "").strip()
    if not url:
        return jsonify(error="Please provide an article URL via ?url="), 400

    host = urlparse(url).netloc.lower()
    # Step 7 — Google News links can't be followed server-side.
    if any(h in host for h in GOOGLE_HOSTS) or "/url?" in url:
        return jsonify(
            needs_manual=True,
            open_url=url,
            reason="This is a Google News link. Open it in your browser, let it redirect to the "
            "real article, then paste that URL back here.",
        )

    try:
        resp_html = requests.get(url, headers=BROWSER_HEADERS, timeout=15, allow_redirects=True)
        resp_html.raise_for_status()
        final_host = urlparse(resp_html.url).netloc.lower()
        if any(h in final_host for h in GOOGLE_HOSTS):
            return jsonify(needs_manual=True, open_url=url,
                           reason="The link redirected to a Google page. Open it in your browser "
                                  "and paste the final article URL.")
        html = resp_html.text
    except requests.RequestException as exc:
        return jsonify(error=f"Could not fetch the article: {exc}"), 502

    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string.strip() if soup.title and soup.title.string else None)
    og_title = soup.find("meta", property="og:title")
    if og_title and og_title.get("content"):
        title = og_title["content"].strip()
    og = soup.find("meta", property="og:image")
    thumbnail = og["content"].strip() if og and og.get("content") else None

    work = BeautifulSoup(html, "html.parser")
    for tag in work(["script", "style", "nav", "header", "footer", "aside", "noscript", "form"]):
        tag.decompose()
    main = work.find("article") or work.find("main") or work.body or work
    text = re.sub(r"\n{2,}", "\n", main.get_text("\n", strip=True))[:12000]

    method = "fallback"
    items = None
    try:
        items = extract_with_gemini(title, text)
        if items:
            method = "gemini"
    except _RateLimited:
        return jsonify(
            error="Gemini rate limit reached (free tier). Wait a minute and try again.",
        ), 429

    if not items:  # Step 8 — Gemini unavailable/empty → HTML heuristics.
        items = extract_with_html(text, html)
        method = "fallback"

    return jsonify(title=title, url=resp_html.url, items=items, thumbnail=thumbnail,
                   method=method, captured=date.today().isoformat())


@app.get("/api/health")
def health():
    return jsonify(ok=True, gemini=HAS_GEMINI, model=GEMINI_MODEL if HAS_GEMINI else None)


if __name__ == "__main__":
    print("\n  Trend Finder Upgrade API running at http://localhost:5001")
    print(f"  Gemini: {'enabled (' + GEMINI_MODEL + ')' if HAS_GEMINI else 'NOT set — extraction uses HTML fallback'}")
    print("  Try: http://localhost:5001/api/trending?q=best+gadgets\n")
    app.run(port=5001, debug=True)
