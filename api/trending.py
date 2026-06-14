# ===========================================================================
# api/trending.py — Vercel Python serverless function (GET /api/trending?q=)
#
# Searches Google News RSS + Reddit RSS + Hacker News and returns the top 5
# trending ARTICLES for the query. Ported from server.py. Vercel serves the
# WSGI `app` below.
# ===========================================================================

import re
from datetime import date
from urllib.parse import quote_plus

import feedparser
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
MAX_RESULTS = 5


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
    # (it rate-limits with 429 under bursts — so we retry briefly). Returns []
    # if Reddit keeps throttling us.
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
@app.get("/")
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
