# ===========================================================================
# app.py — Trend Finder backend (Flask)
#
# Responsibilities:
#   1. Expose GET /api/trends?q=<topic> which scrapes eBay's live search
#      results for that topic and returns the Top 5 products.
#   2. Each product carries: name, image (if available), source/store, and a
#      link to the original listing.
#
# This runs SEPARATELY from the Node site (server.js, port 3000). The two HTML
# pages are still served by Node; this Flask app only serves trend data on
# port 5000 and enables CORS so the browser page can fetch across origins.
#
# No API key required — it scrapes the public eBay search results page with
# requests + BeautifulSoup. No fake/sample data is ever returned: if eBay
# yields nothing, the response is an empty results list.
# ===========================================================================

import time
from datetime import date
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # allow the page served from http://localhost:3000 to call this API

# eBay blocks bare requests (returns 403); it needs a full browser-like header
# set AND session cookies from a prior page view. We grab cookies by visiting
# the homepage once, then hit the search page (see search_ebay()).
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
    """Fetch the eBay results page, retrying past the 'Pardon Our
    Interruption' anti-bot challenge that eBay serves intermittently.

    Returns the HTML of a real results page. Raises requests.RequestException
    if eBay keeps challenging us after `attempts` tries.
    """
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
        # The challenge page is small and titled "Pardon Our Interruption".
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

    Each item is a dict: {name, image, source, link}. Selectors are isolated
    here so they're easy to update if eBay changes its markup. Returns [] when
    nothing usable is found — never fabricated data.

    eBay's current results use `.s-card` items (title `.s-card__title`, a real
    listing link containing `/itm/<id>`, image from i.ebayimg.com). The first
    "Shop on eBay" card and any placeholder image (ir.ebaystatic.com) are
    skipped.
    """
    html = _fetch_results_html(query)

    soup = BeautifulSoup(html, "html.parser")
    results = []
    seen = set()

    for card in soup.select(".s-card"):
        title_el = card.select_one(".s-card__title")
        name = _clean_title(title_el.get_text(" ", strip=True)) if title_el else None

        link_el = card.select_one("a[href*='/itm/']")
        link = link_el.get("href") if link_el else None

        # Skip the leading "Shop on eBay" placeholder and any broken row.
        if not name or not link or name.lower() == "shop on ebay":
            continue

        item_id = _itm_id(link)
        dedupe_key = item_id or link
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        img_el = card.select_one("img")
        image = _first_attr(img_el, "src", "data-src")
        # eBay uses a static placeholder graphic for lazy/empty images.
        if image and "ebaystatic.com" in image:
            image = None

        results.append(
            {"name": name, "image": image, "source": "eBay", "link": link}
        )

        if len(results) >= MAX_RESULTS:
            break

    return results


@app.get("/api/health")
def health():
    return jsonify(ok=True)


@app.get("/api/trends")
def trends():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify(error="Please provide a search topic via ?q="), 400

    try:
        results = search_ebay(query)
    except requests.RequestException as exc:
        # Network / HTTP failure talking to eBay — surface honestly.
        return jsonify(error=f"Could not reach eBay: {exc}"), 502

    return jsonify(query=query, results=results, captured=date.today().isoformat())


if __name__ == "__main__":
    print("\n  Trend Finder API running at http://localhost:5000")
    print("  Try: http://localhost:5000/api/trends?q=mechanical+keyboard\n")
    app.run(port=5000, debug=True)
