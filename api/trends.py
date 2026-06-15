# ===========================================================================
# api/trends.py — Vercel Python serverless function (GET /api/trends?q=<topic>)
#
# Returns the Top 5 eBay products for a topic via eBay's official Browse API.
# Uses Vercel's native BaseHTTPRequestHandler pattern (NOT Flask).
#
# Why the API and not HTML scraping: eBay blocks datacenter IPs (Vercel) at the
# edge (503 / anti-bot), so server-side scraping is unreliable in production. The
# Browse API works from any IP and returns clean structured data.
#
# Auth: OAuth 2.0 client-credentials grant. Set EBAY_CLIENT_ID (App ID) and
# EBAY_CLIENT_SECRET (Cert ID) — from https://developer.ebay.com — as env vars.
# No fake/sample data is ever returned: if eBay yields nothing, results is [].
# ===========================================================================

import base64
import json
import os
import time
from datetime import date
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote_plus, urlparse, parse_qs

import requests

EBAY_CLIENT_ID = (os.environ.get("EBAY_CLIENT_ID") or "").strip()
EBAY_CLIENT_SECRET = (os.environ.get("EBAY_CLIENT_SECRET") or "").strip()

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
MARKETPLACE = "EBAY_US"
MAX_RESULTS = 5

# Cache the application token across warm invocations (it lasts ~2 hours).
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
    # Refresh 60s before the real expiry to avoid edge-of-expiry failures.
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


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        query = (params.get("q", [""])[0] or "").strip()

        if not query:
            return self._json(400, {"error": "Please provide a search topic via ?q="})

        if not has_keys():
            return self._json(503, {
                "error": "eBay API keys are not set. Add EBAY_CLIENT_ID and "
                         "EBAY_CLIENT_SECRET (from developer.ebay.com) to the "
                         "environment variables and redeploy.",
            })

        try:
            results = search_ebay(query)
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 502
            detail = ""
            try:
                detail = exc.response.json().get("errors", [{}])[0].get("message", "")
            except Exception:
                detail = exc.response.text[:200] if exc.response is not None else ""
            return self._json(502, {"error": f"eBay API error ({status}): {detail or exc}"})
        except requests.RequestException as exc:
            return self._json(502, {"error": f"Could not reach eBay API: {exc}"})

        self._json(200, {"query": query, "results": results, "captured": date.today().isoformat()})

    def _json(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
