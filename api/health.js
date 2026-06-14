// ===========================================================================
// api/health.js — Vercel serverless function (GET /api/health)
//
// Reports whether the Kie key is configured. Note: this route is behind the
// login gate (middleware.js) like the other /api/* tools.
// ===========================================================================

export default function handler(_req, res) {
  res.json({ ok: true, hasKey: Boolean(process.env.KIE_AI_API_KEY?.trim()) });
}
