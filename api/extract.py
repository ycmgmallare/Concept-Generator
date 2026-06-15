# ===========================================================================
# api/extract.py — Vercel Python serverless function (GET /api/extract?url=)
#
# Fetches one article, pulls clean text, and asks Gemini Flash to return the
# article's ranked list of products/ideas (ignoring nav/ads). Falls back to HTML
# heuristics if Gemini is unavailable. Uses Vercel's native
# BaseHTTPRequestHandler pattern (NOT Flask) — see api/trends.py for why.
#
# Gemini is used for TEXT ANALYSIS ONLY. The key lives in the GEMINI_API_KEY env
# var (set in Vercel) and never reaches the browser.
# ===========================================================================

import json
import os
import re
from datetime import date
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
GEMINI_MODEL = (os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash").strip()
GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)

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
GOOGLE_HOSTS = ("news.google.com", "consent.google.com")


class _RateLimited(Exception):
    pass


def _norm_type(value):
    """Normalise Gemini's type field to exactly 'product' or 'idea'."""
    return "product" if str(value or "").strip().lower().startswith("prod") else "idea"


def extract_with_gemini(title, text):
    """Ask Gemini Flash to read the article and return its meaningful content as
    a labeled list of {rank, text, type}. Returns items or None (None lets the
    caller fall back to HTML heuristics)."""
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
        for i, it in enumerate(cleaned, start=1):
            it["rank"] = i
        return cleaned or None
    except _RateLimited:
        raise
    except (requests.RequestException, ValueError, KeyError, IndexError):
        return None


def extract_with_html(text, soup_html):
    """Heuristic fallback: pull the longest list-like run from HTML."""
    soup = BeautifulSoup(soup_html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    best = []
    for ol in soup.find_all("ol"):
        items = [li.get_text(" ", strip=True) for li in ol.find_all("li", recursive=False)]
        items = [t for t in items if 3 <= len(t) <= 200]
        if len(items) > len(best):
            best = items
    if len(best) < 3:
        heads = [h.get_text(" ", strip=True) for h in soup.find_all(["h2", "h3"])]
        heads = [h for h in heads if 3 <= len(h) <= 120]
        if len(heads) >= 3:
            best = heads

    return [{"rank": i, "text": t, "type": "idea"} for i, t in enumerate(best[:25], start=1)]


def do_extract(url):
    """Run the full extract pipeline for `url`. Returns (status_code, dict)."""
    host = urlparse(url).netloc.lower()
    if any(h in host for h in GOOGLE_HOSTS) or "/url?" in url:
        return 200, {
            "needs_manual": True,
            "open_url": url,
            "reason": "This is a Google News link. Open it in your browser, let it redirect to the "
            "real article, then paste that URL back here.",
        }

    try:
        resp_html = requests.get(url, headers=BROWSER_HEADERS, timeout=15, allow_redirects=True)
        resp_html.raise_for_status()
        final_host = urlparse(resp_html.url).netloc.lower()
        if any(h in final_host for h in GOOGLE_HOSTS):
            return 200, {
                "needs_manual": True,
                "open_url": url,
                "reason": "The link redirected to a Google page. Open it in your browser "
                "and paste the final article URL.",
            }
        html = resp_html.text
    except requests.RequestException as exc:
        return 502, {"error": f"Could not fetch the article: {exc}"}

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
        return 429, {"error": "Gemini rate limit reached (free tier). Wait a minute and try again."}

    if not items:
        items = extract_with_html(text, html)
        method = "fallback"

    return 200, {
        "title": title,
        "url": resp_html.url,
        "items": items,
        "thumbnail": thumbnail,
        "method": method,
        "captured": date.today().isoformat(),
    }


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        url = (params.get("url", [""])[0] or "").strip()

        if not url:
            return self._json(400, {"error": "Please provide an article URL via ?url="})

        code, payload = do_extract(url)
        self._json(code, payload)

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
