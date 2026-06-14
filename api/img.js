// ===========================================================================
// api/img.js — Vercel serverless function (GET /api/img?url=<encoded>)
//
// Image proxy: fetches a remote thumbnail server-side and streams it back.
// Reddit/news images often block hotlinking or lack CORS headers, so proxying
// them lets the browser <img> tags load. Ported from serve.mjs:30-57.
// This endpoint is intentionally NOT gated (see middleware.js) so thumbnails
// load without a login prompt.
// ===========================================================================

export default async function handler(req, res) {
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

    const buf = Buffer.from(await upstream.arrayBuffer());
    res.setHeader("Content-Type", type);
    res.setHeader("Cache-Control", "public, max-age=86400");
    res.status(200).end(buf);
  } catch (err) {
    res.status(502).send("Image proxy failed: " + err.message);
  }
}
