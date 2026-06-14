// ===========================================================================
// api/concepts.js — Vercel serverless function (POST /api/concepts)
//
// Turns the user's 3 inputs into the 6 concepts + prompts (concepts.js).
// No external API call here. Ported from server.js:62-75.
// ===========================================================================

import { buildConcepts } from "../concepts.js";

export default function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  const idea = (req.body?.idea ?? "").toString().trim();
  const theme = (req.body?.theme ?? "").toString().trim();
  const products = (req.body?.products ?? "").toString().trim();

  if (!idea || !theme || !products) {
    return res
      .status(400)
      .json({ error: "Please fill in all three fields: Idea, Theme, and Products." });
  }

  const concepts = buildConcepts({ idea, theme, products });
  res.json({ concepts });
}
