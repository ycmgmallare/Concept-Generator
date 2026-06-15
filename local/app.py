# ===========================================================================
# local/app.py — Trend Finder backend (Flask, local dev only — port 5000)
#
# Returns the Top 5 eBay products for a topic via eBay's official Browse API.
# The DEPLOYED copy is api/trends.py (Vercel native handler); this Flask version
# mirrors it for local development so behavior matches production.
#
# Auth: OAuth 2.0 client-credentials. Set EBAY_CLIENT_ID (App ID) and
# EBAY_CLIENT_SECRET (Cert ID) in .env — get them at https://developer.ebay.com.
# No fake/sample data: if eBay yields nothing, results is an empty list.
# ===========================================================================

import base64
import os
import time
from datetime import date
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

app = Flask(__name__)
CORS(app)  # allow the page served from http://localhost:3000 to call this API

EBAY_CLIENT_ID = (os.environ.get("EBAY_CLIENT_ID") or "").strip()
EBAY_CLIENT_SECRET = (os.environ.get("EBAY_CLIENT_SECRET") or "").strip()

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
MARKETPLACE = "EBAY_US"
MAX_RESULTS = 5

_token_cache = {"value": None, "expires_at": 0.0}


def has_keys():
    return bool(EBAY_CLIENT_ID) and bool(EBAY_CLIENT_SECRET)


def get_token():
    """Return a cached or fresh eBay application access token (client credentials)."""
    now = time.time()
    if _token_cache["value"] and now < _token_cache["expires_at"]:
        return _token_cache["value"]

    basic = base64.b64encode(
        f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}".encode("utf-8")
    ).decode("ascii")
    resp = requests.post(
        TOKEN_URL,
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    token = data["access_token"]
    _token_cache["value"] = token
    _token_cache["expires_at"] = now + int(data.get("expires_in", 7200)) - 60
    return token


def search_ebay(query):
    """Search eBay's Browse API for `query` and return up to 5 products as
    {name, image, source, link}. Returns [] when nothing is found."""
    token = get_token()
    resp = requests.get(
        f"{SEARCH_URL}?q={quote_plus(query)}&limit={MAX_RESULTS}",
        headers={
            "Authorization": f"Bearer {token}",
            "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE,
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in (data.get("itemSummaries") or [])[:MAX_RESULTS]:
        name = item.get("title")
        link = item.get("itemWebUrl")
        if not name or not link:
            continue
        image = (item.get("image") or {}).get("imageUrl")
        if not image:
            thumbs = item.get("thumbnailImages") or []
            if thumbs:
                image = thumbs[0].get("imageUrl")
        results.append({"name": name, "image": image, "source": "eBay", "link": link})

    return results


@app.get("/api/health")
def health():
    return jsonify(ok=True, ebay=has_keys())


@app.get("/api/trends")
def trends():
    query = (request.args.get("q") or "").strip()
    if not query:
        return jsonify(error="Please provide a search topic via ?q="), 400

    if not has_keys():
        return jsonify(
            error="eBay API keys are not set. Add EBAY_CLIENT_ID and "
                  "EBAY_CLIENT_SECRET (from developer.ebay.com) to .env and restart."
        ), 503

    try:
        results = search_ebay(query)
    except requests.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        detail = ""
        try:
            detail = exc.response.json().get("errors", [{}])[0].get("message", "")
        except Exception:
            detail = exc.response.text[:200] if exc.response is not None else ""
        return jsonify(error=f"eBay API error ({status}): {detail or exc}"), 502
    except requests.RequestException as exc:
        return jsonify(error=f"Could not reach eBay API: {exc}"), 502

    return jsonify(query=query, results=results, captured=date.today().isoformat())


if __name__ == "__main__":
    print("\n  Trend Finder API running at http://localhost:5000")
    print(f"  eBay API keys: {'set' if has_keys() else 'NOT set — add them to .env'}")
    print("  Try: http://localhost:5000/api/trends?q=mechanical+keyboard\n")
    app.run(port=5000, debug=True)
