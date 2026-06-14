// ===========================================================================
// api/generate/image.js — Vercel serverless function (POST /api/generate/image)
//
// Submits one Kie AI image task and returns its taskId. The key stays
// server-side (KIE_AI_API_KEY env var). Ported from server.js:79-107.
// ===========================================================================

const KIE_BASE = "https://api.kie.ai/api/v1";

function kieHeaders() {
  return {
    Authorization: `Bearer ${process.env.KIE_AI_API_KEY}`,
    "Content-Type": "application/json",
  };
}

function requireKey(res) {
  if (!process.env.KIE_AI_API_KEY || !process.env.KIE_AI_API_KEY.trim()) {
    res.status(503).json({
      error:
        "KIE_AI_API_KEY is not set. Add it in your Vercel project's Environment " +
        "Variables (Settings → Environment Variables) and redeploy.",
    });
    return false;
  }
  return true;
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }
  if (!requireKey(res)) return;

  const {
    model = "google/nano-banana",
    prompt,
    aspect_ratio = "16:9",
    output_format = "png",
  } = req.body ?? {};

  if (!prompt) return res.status(400).json({ error: "prompt is required" });

  const input = { prompt, aspect_ratio, output_format };

  try {
    const response = await fetch(`${KIE_BASE}/jobs/createTask`, {
      method: "POST",
      headers: kieHeaders(),
      body: JSON.stringify({ model, input }),
    });
    const data = await response.json();
    if (data.code !== 200) {
      return res.status(502).json({ error: data.msg ?? "Kie createTask failed", details: data });
    }
    res.json({ taskId: data.data.taskId });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
