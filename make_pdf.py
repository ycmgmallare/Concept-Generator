# Generates ConceptGenerator.pdf — a self-learning write-up of the three tools
# built in this project. Run:  python make_pdf.py
from datetime import date

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable, ListFlowable, ListItem, PageBreak, Paragraph,
    SimpleDocTemplate, Spacer, Table, TableStyle,
)

# ---- palette (echoes the app's warm paper theme) -------------------------
INK = colors.HexColor("#1d1813")
INK_SOFT = colors.HexColor("#6a6055")
ACCENT = colors.HexColor("#d2452a")
GREEN = colors.HexColor("#3f6b59")
LINE = colors.HexColor("#c6b9a0")
PAPER = colors.HexColor("#f4eee1")
PANEL = colors.HexColor("#faf6ec")
WARN = colors.HexColor("#c79a1e")

styles = getSampleStyleSheet()


def S(name, **kw):
    return ParagraphStyle(name, parent=styles["Normal"], **kw)


body = S("body", fontName="Helvetica", fontSize=10, leading=15, textColor=INK,
         spaceAfter=6, alignment=TA_LEFT)
h1 = S("h1", fontName="Helvetica-Bold", fontSize=22, leading=26, textColor=INK, spaceAfter=4)
h2 = S("h2", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=ACCENT,
       spaceBefore=14, spaceAfter=6)
h3 = S("h3", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=GREEN,
       spaceBefore=8, spaceAfter=3)
small = S("small", fontName="Helvetica", fontSize=8.5, leading=12, textColor=INK_SOFT)
mono = S("mono", fontName="Courier", fontSize=8.5, leading=12, textColor=INK,
         backColor=PANEL, borderColor=LINE, borderWidth=0.5, borderPadding=6,
         spaceBefore=2, spaceAfter=8)
quote = S("quote", fontName="Helvetica-Oblique", fontSize=10, leading=15, textColor=INK_SOFT,
          leftIndent=10, borderColor=ACCENT, spaceAfter=8)

story = []


def para(txt, st=body):
    story.append(Paragraph(txt, st))


def bullets(items, st=body):
    story.append(ListFlowable(
        [ListItem(Paragraph(t, st), leftIndent=12, value="•") for t in items],
        bulletType="bullet", start="•", leftIndent=10, bulletColor=ACCENT, spaceAfter=6,
    ))


def rule(color=LINE, w=0.8):
    story.append(HRFlowable(width="100%", thickness=w, color=color,
                            spaceBefore=4, spaceAfter=8))


def gap(h=4):
    story.append(Spacer(1, h))


def tbl(data, col_widths, header=True):
    t = Table(data, colWidths=col_widths, hAlign="LEFT")
    ts = [
        ("FONT", (0, 0), (-1, -1), "Helvetica", 8.5),
        ("TEXTCOLOR", (0, 0), (-1, -1), INK),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, PAPER]),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if header:
        ts += [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5),
               ("BACKGROUND", (0, 0), (-1, 0), INK),
               ("TEXTCOLOR", (0, 0), (-1, 0), PAPER)]
    t.setStyle(TableStyle(ts))
    story.append(t)
    gap(8)


def cell(txt):
    return Paragraph(txt, S("cell", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK))


def cellb(txt):
    return Paragraph(txt, S("cellb", fontName="Helvetica-Bold", fontSize=8.5, leading=11, textColor=PAPER))


# ===========================================================================
# COVER
# ===========================================================================
gap(40)
para("CONCEPT GENERATOR", S("tag", fontName="Courier-Bold", fontSize=11, textColor=ACCENT,
                            leading=14, spaceAfter=6))
para("A Three-Tool Build Journal", h1)
para("Moodboard Studio &bull; eBay Trend Finder &bull; Trend Finder Upgrade", S(
    "sub", fontName="Helvetica", fontSize=12.5, leading=18, textColor=INK_SOFT, spaceAfter=10))
rule(INK, 1.4)
para("A self-learning write-up: how each tool was built, the architecture and "
     "data flow, what worked, what broke (and how it was fixed), and the "
     "transferable lessons for future projects.", body)
gap(8)
para("Project: Front-end design studio + web-scraping/AI research tools<br/>"
     "Stack: HTML/CSS/JS &bull; Node.js (Express) &bull; Python (Flask) &bull; "
     "BeautifulSoup &bull; feedparser &bull; Gemini Flash &bull; Kie AI<br/>"
     "Generated: " + date.today().strftime("%d %B %Y"), small)
gap(16)

# the three tools at a glance
para("The three tools at a glance", h3)
tbl([
    [cellb("Tool"), cellb("What it does"), cellb("Backend"), cellb("Ports")],
    [cell("<b>Moodboard Studio</b>"), cell("Turns one brief (idea/theme/products) into 6 homepage design moodboards as AI images"), cell("Node + Kie AI"), cell("3000 / —")],
    [cell("<b>Trend Finder</b> (eBay)"), cell("Search a topic &rarr; top 5 trending products (name, image, store, buy link) + dated CSV / printable report"), cell("Flask + BeautifulSoup"), cell("3000 / 5000")],
    [cell("<b>Trend Finder Upgrade</b>"), cell("Search trending articles &rarr; Gemini extracts products + ideas (labeled) &rarr; you pick &rarr; dated CSV"), cell("Flask + Gemini, Node proxy"), cell("3002 / 5001")],
], [95, 200, 95, 70])

story.append(PageBreak())

# ===========================================================================
# 1. MOODBOARD STUDIO
# ===========================================================================
para("1 — Moodboard Studio", h2)
para("The original tool. A single-page app that takes a creative brief and "
     "generates six homepage design directions (two Minimalist, two "
     "Contemporary, two Dynamic), each rendered as an image via Kie AI.", body)

para("How it was built", h3)
bullets([
    "<b>Front end</b> (<font face='Courier'>Frontend.html</font>): one self-contained file — inline CSS design system (warm paper palette, Fraunces/Newsreader/JetBrains Mono fonts) and inline JS. State persists in <font face='Courier'>localStorage</font> so edits survive a refresh.",
    "<b>Backend</b> (<font face='Courier'>server.js</font>, Express): serves the page and <i>proxies</i> Kie AI so the API key stays server-side. Flow: POST a prompt &rarr; get a <font face='Courier'>taskId</font> &rarr; poll until the image is ready.",
    "<b>Prompt templates</b> (<font face='Courier'>concepts.js</font>): the six concepts are templates with {idea}/{theme}/{products} placeholders — editable without touching app logic.",
])

para("Key pattern: the async create-then-poll proxy", h3)
para("Image generation is slow, so the API is split into two calls. The browser "
     "never sees the key; the server does the waiting.", body)
story.append(Paragraph(
    "POST /api/generate/image  &rarr; { taskId }<br/>"
    "GET  /api/task/image?taskId=...  &rarr; { state: pending|success|fail, urls[] }",
    mono))

para("What worked", h3)
bullets([
    "A single inline-everything HTML file is fast to iterate on and trivial to share.",
    "Proxying the third-party API through your own server is the clean way to hide keys and dodge browser CORS.",
    "Separating prompt templates from logic made the creative part editable in isolation.",
])
para("What to watch", h3)
bullets([
    "Generated image URLs live on the provider's CDN and expire — export to keep a copy.",
    "Polling needs a timeout/back-off so a stuck task doesn't spin forever.",
])

rule()

# ===========================================================================
# 2. TREND FINDER (eBay)
# ===========================================================================
para("2 — Trend Finder (eBay product scraper)", h2)
para("The first Python tool. A search box returns the top 5 trending products "
     "for any topic — name, image, store/source, and a button to the real "
     "listing — scraped live from eBay. No fake data, no API key.", body)

para("How it was built", h3)
bullets([
    "<b>New page</b> (<font face='Courier'>trend-finder.html</font>) reusing the Moodboard design system, linked from a new nav bar added to both pages.",
    "<b>Flask API</b> (<font face='Courier'>app.py</font>, port 5000): <font face='Courier'>GET /api/trends?q=</font> requests eBay's search page and parses it with BeautifulSoup.",
    "The frontend fetches the API across origins (CORS enabled) and renders result cards.",
])

para("The real lesson: scraping is a moving target", h3)
para("This is where most of the learning happened. Three concrete problems "
     "showed up — each is a transferable lesson:", body)
tbl([
    [cellb("Problem"), cellb("Symptom"), cellb("Fix")],
    [cell("Bot blocking"), cell("Bare request &rarr; HTTP 403"), cell("Send a real browser <font face='Courier'>User-Agent</font>; warm up cookies by hitting the homepage first")],
    [cell("Markup drift"), cell("Old selectors (<font face='Courier'>.s-item</font>) found nothing"), cell("eBay had moved to <font face='Courier'>.s-card</font>; inspect the live DOM, don't trust assumptions")],
    [cell("Intermittent challenge"), cell("'Pardon Our Interruption' page ~30% of calls"), cell("Detect the challenge page and retry 2-3x with a short delay")],
], [90, 175, 195])
para("Defensive parsing throughout: skip the 'Shop on eBay' placeholder, treat "
     "the static placeholder graphic as 'no image', de-dupe by item id, and "
     "return an empty list (never fabricated data) when nothing parses.", body)

para("What worked", h3)
bullets([
    "Isolating all selectors in one function (<font face='Courier'>search_ebay()</font>) made the inevitable markup fix a one-place change.",
    "The retry-on-challenge loop turned a flaky ~70% success rate into reliable results.",
    "Returning a clean empty state kept the honesty rule intact: no sample data, ever.",
])
para("Dated reports (added later)", h3)
bullets([
    "Every result set carries a server-stamped capture date (<font face='Courier'>captured</font> in the API), shown as 'Captured YYYY-MM-DD' — because trends change, a report is only reproducible if it says <i>when</i> it was taken.",
    "Two one-click outputs: a date-stamped <b>CSV</b> (<font face='Courier'>ebay-trends-&lt;topic&gt;-&lt;date&gt;.csv</font>) and a <b>printable report</b> window (Save-as-PDF) — both client-side, no new backend.",
])
para("What didn't", h3)
bullets([
    "First selector set was based on memory of eBay's old HTML — wrong. Always verify against the live page.",
    "A single request with no UA/cookies never works against a big retailer.",
])

story.append(PageBreak())

# ===========================================================================
# 3. TREND FINDER UPGRADE
# ===========================================================================
para("3 — Trend Finder Upgrade (article &rarr; idea research)", h2)
para("The most ambitious tool. Search trending <i>articles</i> across three "
     "sources, use Gemini Flash to read each article and extract its meaningful "
     "content — the <b>products it recommends AND the article's main ideas</b>, each "
     "labeled by type — let the user pick which to keep, and export to a dated CSV. "
     "Gemini is used for text analysis only — never images.", body)

para("Architecture (two servers, by design)", h3)
tbl([
    [cellb("Server"), cellb("Port"), cellb("Responsibilities")],
    [cell("<b>Flask</b> <font face='Courier'>server.py</font>"), cell("5001"), cell("All scraping + AI: <font face='Courier'>/api/trending</font> (Google News RSS + Reddit + Hacker News) and <font face='Courier'>/api/extract</font> (fetch &rarr; clean text &rarr; Gemini &rarr; fallback). Holds the Gemini key.")],
    [cell("<b>Node</b> <font face='Courier'>serve.mjs</font>"), cell("3002"), cell("Serves the page and proxies thumbnail images (<font face='Courier'>/img?url=</font>) to dodge hotlink/CORS blocks.")],
], [110, 40, 300])

para("Data flow", h3)
story.append(Paragraph(
    "search &rarr; GET :5001/api/trending?q=  &rarr; 5 article cards (+ captured date)<br/>"
    "card button &rarr; GET :5001/api/extract?url=  &rarr; { items:[{rank,text,type}], method, captured }<br/>"
    "items &rarr; Idea Panel (checkboxes) &rarr; Preview table &rarr; Export dated CSV (client-side Blob + BOM)",
    mono))

para("Smart bits", h3)
bullets([
    "<b>AI-first extraction, heuristic fallback</b>: Gemini decides what the article's real content is; if the key is missing or the call fails, a BeautifulSoup heuristic (&lt;ol&gt;/&lt;li&gt; or repeated headings) keeps the tool usable.",
    "<b>Products AND ideas, labeled by type</b>: the prompt asks Gemini for both the products/tools the article recommends and its main ideas/takeaways, each tagged <font face='Courier'>product</font> or <font face='Courier'>idea</font> — so it works on essays, not just listicles (the earlier version only scraped raw lists).",
    "<b>Structured AI output</b>: Gemini is asked for JSON (<font face='Courier'>responseMimeType: application/json</font>) so results parse reliably instead of scraping prose.",
    "<b>User selects, not auto-pick</b>: <b>Extract Ideas</b> adds the whole list in one click; <b>Browse &amp; Pick</b> opens a checklist that starts empty so the user ticks exactly what to keep before adding.",
    "<b>Dated, reproducible export</b>: a server-stamped capture date flows into the panel, Preview, and a date-stamped <font face='Courier'>trend-ideas-&lt;date&gt;.csv</font> with a Type column.",
    "<b>Google News workaround</b>: News links are browser-only redirects, so the server flags <font face='Courier'>needs_manual</font> and the UI shows a paste box — open the article, copy the real URL, paste it back.",
])

para("Problems hit & fixed (live debugging)", h3)
tbl([
    [cellb("Problem"), cellb("Root cause"), cellb("Fix")],
    [cell("Reddit returned 403"), cell("<font face='Courier'>.json</font> endpoint now blocks bots"), cell("Switched to Reddit's RSS feed + retry on 429")],
    [cell("Only News results showed"), cell("HN is tech-focused; 0 hits for consumer queries"), cell("Expected — interleave 3 sources, degrade gracefully")],
    [cell("Image proxy '400/404'"), cell("Not a bug — passing through upstream status for bad test URLs"), cell("Confirmed with known-good images (200)")],
    [cell("Gemini 429 on 1st call"), cell("Free tier had <font face='Courier'>limit: 0</font> for gemini-2.0-flash"), cell("Probed models; switched default to <font face='Courier'>gemini-2.5-flash</font>")],
], [120, 175, 155])

para("Biggest lesson here", h3)
para("Read the actual error body. The Gemini failure looked like ordinary rate "
     "limiting, but the JSON said <font face='Courier'>limit: 0</font> for that specific model — a "
     "quota/availability issue, not a throttle. Probing each model against the "
     "key found a working one in seconds.", quote)

story.append(PageBreak())

# ===========================================================================
# CROSS-CUTTING LESSONS
# ===========================================================================
para("What this mini-project teaches", h2)

para("Architecture & integration", h3)
bullets([
    "<b>Proxy third-party APIs through your own backend.</b> It hides keys, fixes CORS, and lets you reshape responses. Used for Kie, Gemini, and images.",
    "<b>Polyglot is fine.</b> Node and Python servers coexisted happily; pick the right tool per job (Node for the existing site + image streaming, Python for scraping/AI) and let CORS bridge them.",
    "<b>Run tools as separate services on separate ports.</b> Each tool stayed independent, so a change in one couldn't break another — lowest-risk way to add features.",
    "<b>Design once, reuse everywhere.</b> A small set of CSS tokens (colors, fonts, card/button styles) copied across pages gave a consistent look with no framework.",
])

para("Working with live web data", h3)
bullets([
    "<b>The web actively resists scraping.</b> Expect 403/429/captcha. Browser headers, cookie warm-ups, and retry loops are the baseline, not extras.",
    "<b>Markup changes — isolate your selectors.</b> Keep parsing in one function so the inevitable fix is contained.",
    "<b>Prefer feeds/APIs over HTML when they exist.</b> RSS (Google News, Reddit) and JSON APIs (HN Algolia) are far more stable than scraping pages.",
    "<b>Degrade gracefully and never fake data.</b> Empty states and honest errors beat fabricated results.",
])

para("Working with AI (LLMs)", h3)
bullets([
    "<b>Let the model do judgement, not plumbing.</b> Gemini decided which text was 'the list' — far better than brittle HTML rules — while code handled fetching and formatting.",
    "<b>Ask for structured output.</b> JSON mode + a clear schema makes results parseable and reliable.",
    "<b>Always keep a non-AI fallback.</b> Keys expire, quotas hit zero, calls fail — the tool should still do something useful.",
    "<b>Model availability is not uniform.</b> Free-tier quota differs per model; make the model configurable and verify before assuming.",
])

para("Debugging mindset", h3)
bullets([
    "<b>Reproduce in isolation.</b> Small standalone scripts (one request, print the status/body) found every root cause faster than guessing in the app.",
    "<b>Read the full error, not just the status code.</b> The 429 'limit: 0' detail and the eBay challenge-page title were the whole story.",
    "<b>Verify end-to-end with the real thing.</b> curl against live endpoints caught the eBay markup change, the Reddit block, and the Gemini quota — none were visible from the code alone.",
])

gap(6)
rule(INK, 1.2)
para("Suggested next steps for self-study", h3)
bullets([
    "Add caching (e.g. 10-minute TTL) to scrape/AI calls to cut repeat latency and respect rate limits.",
    "Add a tiny test that hits each live source and warns when a selector/feed breaks.",
    "Try swapping the eBay scraper for an official API to compare reliability vs. effort.",
    "Add request back-off + a queue so bursts of extractions stay under the free-tier limit automatically.",
])
gap(10)
para("Built iteratively, debugged against the live web and a live LLM. The "
    "recurring theme: external systems are unreliable — design for it, observe "
    "carefully, and always leave an honest fallback.", quote)


# ---- footer with page numbers --------------------------------------------
def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(INK_SOFT)
    canvas.drawString(20 * mm, 12 * mm, "ConceptGenerator — Build Journal")
    canvas.drawRightString(A4[0] - 20 * mm, 12 * mm, "Page %d" % doc.page)
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 15 * mm, A4[0] - 20 * mm, 15 * mm)
    canvas.restoreState()


doc = SimpleDocTemplate(
    "ConceptGenerator.pdf", pagesize=A4,
    leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
    title="ConceptGenerator — Build Journal", author="Concept Generator project",
)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print("Wrote ConceptGenerator.pdf")
