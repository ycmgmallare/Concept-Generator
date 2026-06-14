// ===========================================================================
// middleware.js — Vercel Edge Middleware (login gate for /api/* only)
//
// The three tool PAGES are fully public. Only the data endpoints under /api/
// require a username/password, verified here against the APP_USERNAME /
// APP_PASSWORD environment variables. The /api/img image proxy is excluded so
// thumbnails load without a prompt.
//
// We return a plain 401 JSON (NO WWW-Authenticate header) on purpose: that lets
// the front-end (auth.js) show its own login popup instead of the browser's
// native dialog, which doesn't reliably appear for fetch() calls.
// ===========================================================================

export const config = { matcher: ["/api/((?!img).*)"] };

export default function middleware(req) {
  const auth = req.headers.get("authorization") || "";
  const user = process.env.APP_USERNAME || "";
  const pass = process.env.APP_PASSWORD || "";
  const expected = "Basic " + btoa(`${user}:${pass}`);

  if (auth !== expected) {
    return new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  }
  // Authorized — fall through to the requested function (return nothing).
}
