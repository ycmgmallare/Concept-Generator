# FrontEnd — Website Design Moodboard Generator

Turn one brief (**Idea · Theme · Products**) into **six homepage design moodboards** —
two Minimalist, two Contemporary, two Dynamic — each with a rendered front (homepage layout)
and back (inner sections) image, editable prompts, and one-click HTML export. Images are
generated with **Kie AI** (Nano Banana).

> These are *visual design directions* for the same website before development, not working sites.

## What's here

| File | Purpose |
|------|---------|
| `Frontend.html` | The UI — brief inputs, six design cards, editable prompts, export buttons. |
| `server.js` | Local server: serves the page + proxies Kie AI so your key stays server-side. |
| `concepts.js` | **The 6 editable prompt templates.** Tweak concept names / prompts here. |
| `.env` | Holds your `KIE_AI_API_KEY` (you fill this in). |
| `package.json` | Dependencies (`express`, `cors`, `dotenv`). |

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

## Cost

Each full run renders 12 images at ~$0.02 each ≈ **$0.24 per generation**.

## Notes

- Concepts generate even without a key; **images need a valid `KIE_AI_API_KEY`** (the server
  returns a clear error otherwise).
- Kie image URLs are temporary on Kie's CDN — export to `.html` to keep a copy of a direction.
