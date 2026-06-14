# ===========================================================================
# api/trends.py — Vercel Python serverless function (GET /api/trends?q=<topic>)
#
# Scrapes eBay's live search results for a topic and returns the Top 5 products.
# Ported from app.py. Vercel serves the WSGI `app` below.
#
# NOTE: eBay blocks datacenter IPs (Vercel) more aggressively than home IPs, so
# this may hit the "Pardon Our Interruption" challenge more often in production.
# No fake/sample data is ever returned: if eBay yields nothing, results is [].
# ===========================================================================

import time
from datetime import date
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request

app = Flask(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

MAX_RESULTS = 5


def _first_attr(tag, *attrs):
    """Return the first non-empty attribute value among *attrs on tag."""
    if not tag:
        return None
    for attr in attrs:
        value = tag.get(attr)
        if value and value.strip():
            return value.strip()
    return None


def _itm_id(link):
    """Extract the eBay item id from a listing URL (for de-duping carousels)."""
    if not link:
        return None
    marker = "/itm/"
    if marker not in link:
        return None
    tail = link.split(marker, 1)[1]
    digits = ""
    for ch in tail:
        if ch.isdigit():
            digits += ch
        else:
            break
    return digits or None


def _clean_title(text):
    """Drop eBay's appended accessibility label from a card title."""
    suffix = "Opens in a new window or tab"
    if text.endswith(suffix):
        text = text[: -len(suffix)].strip()
    return text


def _fetch_results_html(query, attempts=3):
    """Fetch the eBay results page, retrying past the 'Pardon Our Interruption'
    anti-bot challenge that eBay serves intermittently."""
    search_url = (
        "https://www.ebay.com/sch/i.html"
        f"?_nkw={quote_plus(query)}&_sop=12"  # _sop=12 = Best Match (trending-ish)
    )

    session = requests.Session()
    session.headers.update(HEADERS)
    # Warm up: collect anti-bot cookies from the homepage, else search 403s.
    session.get("https://www.ebay.com/", timeout=15)

    for attempt in range(attempts):
        resp = session.get(search_url, timeout=15)
        resp.raise_for_status()
        if "Pardon Our Interruption" not in resp.text:
            return resp.text
        if attempt < attempts - 1:
            time.sleep(2)

    raise requests.RequestException(
        "eBay is temporarily blocking automated requests (anti-bot challenge). "
        "Please try again in a moment."
    )


def search_ebay(query):
    """Scrape eBay's search results for `query` and return up to 5 products.
    Each item is {name, image, source, link}. Returns [] when nothing usable is
    found — never fabricated data."""
    html = _fetch_results_html(query)

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    for card in soup.select(".s-card"):
        title_el = card.select_one(".s-card__title")
        name = _clean_title(title_el.get_text(" ", strip=True)) if title_el else None

        link_el = card.select_one("a[href*='/itm/']")
        link = link_el.get("href") if link_el else None

        if not name or not link or name.lower() == "shop on ebay":
            continue

        item_id = _itm_id(link)
        dedupe_key = item_id or link
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        img_el = card.select_one("img")
        image = _first_attr(img_el, "src", "data-src")
        if image and "ebaystatic.com" in image:
            image = None

        results.append(
            {"name": name, "image": image, "source": "eBay", "link": link}
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


@app.get("/api/trends")
@app.get("/")
def trends():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify(error="Please provide a search topic via ?q="), 400

    try:
        results = search_ebay(query)
    except requests.RequestException as exc:
        return jsonify(error=f"Could not reach eBay: {exc}"), 502

    return jsonify(query=query, results=results, captured=date.today().isoformat())
