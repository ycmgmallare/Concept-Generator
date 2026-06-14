// ===========================================================================
// serve.mjs — front-end server for the Trend Finder Upgrade (Node, port 3002)
//
// Responsibilities:
//   1. Serve trend-finder-upgrade.html (and other static files) from this folder.
//   2. Image proxy: GET /img?url=<encoded> fetches a remote thumbnail server-side
//      and streams it back. Reddit/news images often block hotlinking or lack
//      CORS headers, so proxying them lets the browser <img> tags load.
//
// All scraping + Gemini extraction lives in the Python Flask server (server.py,
// port 5001). This server never touches the Gemini key.
// ===========================================================================

import express from "express";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const app = express();
const PORT = process.env.RESEARCH_PORT ?? 3002;

app.use(express.static(__dirname));

// Open the upgrade tool at the root for convenience.
app.get("/", (_req, res) =>
  res.sendFile(path.join(__dirname, "trend-finder-upgrade.html"))
);

// GET /img?url=... — stream a remote image back to the browser.
app.get("/img", async (req, res) => {
  const target = req.query.url;
  if (!target || !/^https?:\/\//i.test(target)) {
    return res.status(400).send("Provide an http(s) image url via ?url=");
  }
  try {
    const upstream = await fetch(target, {
      headers: {
        // A plain browser UA with no referer dodges most hotlink protection.
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        Accept: "image/avif,image/webp,image/*,*/*;q=0.8",
      },
    });
    if (!upstream.ok) return res.status(upstream.status).end();

    const type = upstream.headers.get("content-type") || "image/jpeg";
    if (!type.startsWith("image/")) return res.status(415).end();

    res.set("Content-Type", type);
    res.set("Cache-Control", "public, max-age=86400");
    const buf = Buffer.from(await upstream.arrayBuffer());
    res.send(buf);
  } catch (err) {
    res.status(502).send("Image proxy failed: " + err.message);
  }
});

app.listen(PORT, () => {
  console.log(`\n  Trend Finder Upgrade UI running at http://localhost:${PORT}`);
  console.log("  (Make sure server.py is running on :5001 for data.)\n");
});
