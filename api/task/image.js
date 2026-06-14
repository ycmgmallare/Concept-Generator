// ===========================================================================
// api/task/image.js — Vercel serverless function (GET /api/task/image?taskId=)
//
// Polls one Kie AI image task. Returns { state, urls?, failMsg? }. The browser
// calls this repeatedly until state === "success". Ported from server.js:111-139.
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
  if (!requireKey(res)) return;

  const { taskId } = req.query;
  if (!taskId) return res.status(400).json({ error: "taskId is required" });

  try {
    const response = await fetch(
      `${KIE_BASE}/jobs/recordInfo?taskId=${encodeURIComponent(taskId)}`,
      { headers: kieHeaders() }
    );
    const data = await response.json();
    if (data.code !== 200) {
      return res.status(502).json({ error: data.msg ?? "Kie recordInfo failed" });
    }

    const task = data.data;
    const result = { taskId: task.taskId, state: task.state };

    if (task.state === "success" && task.resultJson) {
      const parsed = JSON.parse(task.resultJson);
      result.urls = parsed.resultUrls ?? [];
    }
    if (task.state === "fail") {
      result.failMsg = task.failMsg ?? "Generation failed.";
    }

    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
}
