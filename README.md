# FrontEnd — Website Design Moodboard Generator

Turn one brief (**Idea · Theme · Products**) into **six homepage design moodboards** —
two Minimalist, two Contemporary, two Dynamic — each with a rendered front (homepage layout)
and back (inner sections) image, editable prompts, and one-click HTML export. Images are
generated with **Kie AI** (Nano Banana).

> These are *visual design directions* for the same website before development, not working sites.

## What's here

| File | Purpose |
|------|---------|
| `Frontend.html` | The Moodboard UI — brief inputs, six design cards, editable prompts, export buttons. |
| `server.js` | Local server: serves the pages + proxies Kie AI so your key stays server-side. |
| `concepts.js` | **The 6 editable prompt templates.** Tweak concept names / prompts here. |
| `.env` | Holds your `KIE_AI_API_KEY` (you fill this in). |
| `package.json` | Node dependencies (`express`, `cors`, `dotenv`). |
| `trend-finder.html` | The **Trend Finder** UI — search a topic, see the top 5 trending products. |
| `local/app.py` | **Python/Flask** backend for Trend Finder (local dev): scrapes live eBay results. Deployed copy lives in `api/trends.py`. |
| `trend-finder-upgrade.html` | The **Trend Finder Upgrade** UI — article research, idea picking, CSV export. |
| `local/server.py` | **Python/Flask** backend (local dev, port 5001): article search + Gemini idea extraction. Deployed copy lives in `api/trending.py` + `api/extract.py`. |
| `serve.mjs` | **Node** front-end server (port 3002): serves the upgrade page + proxies images. |
| `requirements.txt` | Python deps for the **deployed** Vercel functions (`requests`, `beautifulsoup4`, `feedparser` — no Flask). |
| `local/requirements-dev.txt` | Python deps for **local dev** (adds `flask`, `flask-cors` for `local/app.py` + `local/server.py`). |

## Setup

1. **Add your Kie key.** Open `.env` and paste your key from <https://kie.ai/api-keys>:
   ```
   KIE_AI_API_KEY=sk-your-real-key
   ```
2. **Install + run** (needs Node 18+):
   ```bash
   npm install
   npm start
   ```
3. Open <http://localhost:3000>.

## Using it

1. Fill in **Idea**, **Theme**, and **Products**.
2. Click **Generate Now** — six concepts appear instantly, then 12 images (front + back × 6)
   render via Kie AI over the next minute or two.
3. Edit any description or prompt inline — edits **save automatically** and survive a refresh.
4. Click **↻ Render** on a panel (or **↻ Regenerate** on a card) to re-render with the current prompt.
5. **Save .html** on a card, or **Export all**, to download a standalone moodboard page.

Everything (brief, prompts, edits, image URLs) is stored in your browser via `localStorage`,
so it all persists across refreshes.

## Customising the designs

Edit **`concepts.js`** — each of the six concepts has a `frontPromptTemplate` and
`backPromptTemplate` using `{idea}`, `{theme}`, `{products}` placeholders, plus shared
`SHARED_FRONT` / `SHARED_BACK` scaffolding you can change to affect all six at once.
Default image aspect ratio is `16:9` (set via `DEFAULT_ASPECT_RATIO`).

## Trend Finder

A second feature, reachable from the **Trend Finder** tab in the top navigation. Type any
topic and it pulls the **top 5 trending products** for it — name, image, source/store, and a
button straight to the listing — live from **eBay's official Browse API**. No fake/sample
data: if nothing is found, you get a clean "no results" state.

> Uses the eBay Browse API (not HTML scraping) so it works from cloud hosts like Vercel,
> which eBay blocks for scraping. Create a free Production keyset at
> <https://developer.ebay.com> and set `EBAY_CLIENT_ID` (App ID) and `EBAY_CLIENT_SECRET`
> (Cert ID) — in `.env` for local dev, and in the Vercel project's Environment Variables for
> the live site.

Locally it runs as a **separate Python/Flask API** (port 5000) alongside the Node site
(port 3000). The pages are still served by Node; Flask only serves the trend data.

**Setup (needs Python 3.8+):**
```bash
pip install -r local/requirements-dev.txt
python local/app.py
```
Then keep the Node site running too (`npm start`), open <http://localhost:3000>, and click
the **Trend Finder** tab. Both servers must be running for the feature to work.

**Dated reports.** Every result set shows the capture date ("Captured YYYY-MM-DD"), and two
buttons let you save a dated report for reproducibility: **Export CSV** (a date-stamped
`ebay-trends-<topic>-<date>.csv` with rank, product, source, image, listing URL, topic, and
capture date) and **Print report** (a clean dated report page you can print or Save-as-PDF).

**API:** `GET http://localhost:5000/api/trends?q=<topic>` →
```json
{ "query": "mechanical keyboard", "captured": "2026-06-15",
  "results": [ { "rank": 1, "name": "...", "image": "https://...", "source": "eBay", "link": "https://..." } ] }
```
`GET /api/health` → `{ "ok": true, "ebay": true }`. The eBay Browse API call lives in
`search_ebay()` in `local/app.py` (and the deployed copy `api/trends.py`).

## Trend Finder Upgrade

A research tool reachable from the **Trend Finder Upgrade** tab. Search a topic to get the
**top 5 trending articles** (from Google News, Reddit, and Hacker News), then use **Gemini
Flash** to read each article and pull out its real ranked list of products/ideas — ignoring
nav menus, ads, and sidebars. Pick the ideas you want and **export them to CSV** for research.

> Gemini is used here for **text analysis only** — reading and summarising article text. It is
> never used for image generation. Your key stays server-side (in Flask) and never reaches the browser.

Locally it's backed by **Flask** `local/server.py` on **:5001** (article search +
Gemini extraction). The page itself is served by `server.js` on **:3000** (which
also proxies thumbnails at `/api/img`), so everything runs on one origin.

**Setup (Python 3.8+ and Node 18+):**
```bash
pip install -r local/requirements-dev.txt
```
Add your free Gemini key (from <https://aistudio.google.com/apikey>) to `.env`:
```
GEMINI_API_KEY=your-real-key
# GEMINI_MODEL=gemini-2.5-flash   # optional override (default)
```
Run the servers (separate terminals):
```bash
npm start               # site + image proxy on :3000
python local/server.py  # article/Gemini API on :5001
```
Open <http://localhost:3000> and click **Trend Finder Upgrade**. (The pages
auto-detect localhost and call the Flask servers; on Vercel they use the relative
`/api/*` functions. `serve.mjs` on :3002 still works but is no longer required.)

**Using it**
1. Search a topic → up to 5 article cards (rank, title, source, thumbnail).
2. **Extract Ideas** adds the article's content to the right-hand Idea Panel; **Browse &
   Pick** opens a checklist so you choose which items to keep first.
3. Tick/untick items in the panel, then **Preview** (table) or **Export CSV**.
4. **Google News links** can't be followed by a server — the card shows a yellow box: click
   **Open article ↗**, let it redirect, copy the real URL, paste it in the box, press Enter.

**What it extracts.** Gemini reads each article and returns its meaningful content — *both* the
**products/tools** it recommends *and* the article's **main ideas/takeaways** — with each item
**labeled by type** (green `Product` / accent `Idea` badge). It works on essays too, not just
listicles. The HTML fallback labels everything `Idea` (heuristics can't classify reliably).

**Dated CSV.** Export downloads `trend-ideas-<date>.csv` with columns
`Rank, Type, Idea/Product, Article Title, Source, URL, Date Captured` (UTF-8 BOM → opens cleanly
in Excel/Sheets). The capture date is shown in the panel, Browse & Pick, and Preview.

**Endpoints:** `GET /api/trending?q=<topic>` → `{captured,results:[{rank,title,link,source,thumbnail}]}` ·
`GET /api/extract?url=<article>` → `{title,url,captured,items:[{rank,text,type}],method}` (or
`{needs_manual:true,open_url}`) · `GET /api/health`. Without a Gemini key, extraction falls
back to HTML heuristics (`method:"fallback"`) instead of failing.

## Cost

Each full run renders 12 images at ~$0.02 each ≈ **$0.24 per generation**.

## Notes

- Concepts generate even without a key; **images need a valid `KIE_AI_API_KEY`** (the server
  returns a clear error otherwise).
- Kie image URLs are temporary on Kie's CDN — export to `.html` to keep a copy of a direction.
