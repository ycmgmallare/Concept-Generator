// ===========================================================================
// server.js — local server for the FrontEnd moodboard generator
//
// Responsibilities:
//   1. Serve Frontend.html (and other static files) from this folder.
//   2. Turn the user's 3 inputs into the 6 concepts + prompts (concepts.js).
//   3. Proxy Kie AI image generation so the API key stays server-side and the
//      browser never hits Kie directly (avoids CORS + leaking the key).
//
// Kie REST flow (mirrors the working sibling Aerofy project):
//   • POST https://api.kie.ai/api/v1/jobs/createTask   -> { data: { taskId } }
//   • GET  https://api.kie.ai/api/v1/jobs/recordInfo?taskId=...
//       -> { data: { state, resultJson, failMsg } }; state "success" => parse
//          resultJson.resultUrls
// ===========================================================================

import "dotenv/config";
import express from "express";
import cors from "cors";
import path from "path";
import { fileURLToPath } from "url";
import { buildConcepts } from "./concepts.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));
app.use(express.static(__dirname)); // serves index.html and assets

// Open the app at the root.
app.get("/", (_req, res) => res.sendFile(path.join(__dirname, "index.html")));

const KIE_BASE = "https://api.kie.ai/api/v1";

function kieHeaders() {
  return {
    Authorization: `Bearer ${process.env.KIE_AI_API_KEY}`,
    "Content-Type": "application/json",
  };
}

// Guard: every Kie route fails fast with a clear message if the key is missing.
function requireKey(res) {
  if (!process.env.KIE_AI_API_KEY || !process.env.KIE_AI_API_KEY.trim()) {
    res.status(503).json({
      error:
        "KIE_AI_API_KEY is not set. Open the .env file in this folder, paste your key from " +
        "https://kie.ai/api-keys after 'KIE_AI_API_KEY=', save, and restart the server.",
    });
    return false;
  }
  return true;
}

app.get("/api/health", (_req, res) =>
  res.json({ ok: true, hasKey: Boolean(process.env.KIE_AI_API_KEY?.trim()) })
);

// GET /api/img?url=... — image proxy for the Trend Finder Upgrade thumbnails,
// so all pages run on this single :3000 origin locally (mirrors api/img.js on
// Vercel). Reddit/news images often block hotlinking or lack CORS headers.
app.get("/api/img", async (req, res) => {
  const target = req.query.url;
  if (!target || !/^https?:\/\//i.test(target)) {
    return res.status(400).send("Provide an http(s) image url via ?url=");
  }
  try {
    const upstream = await fetch(target, {
      headers: {
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
    res.send(Buffer.from(await upstream.arrayBuffer()));
  } catch (err) {
    res.status(502).send("Image proxy failed: " + err.message);
  }
});

// POST /api/concepts — body { idea, theme, products }
// Returns the 6 concepts with finished front/back prompts. No Kie call here.
app.post("/api/concepts", (req, res) => {
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
});

// POST /api/generate/image — body { prompt, aspect_ratio?, model? }
// Submits one Kie image task and returns its taskId.
app.post("/api/generate/image", async (req, res) => {
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
});

// GET /api/task/image?taskId=... — poll one image task.
// Returns { state, urls?, failMsg? }. state is "success" | "fail" | (waiting/etc).
app.get("/api/task/image", async (req, res) => {
  if (!requireKey(res)) return;

  const { taskId } = req.query;
  if (!taskId) return res.status(400).json({ error: "taskId is required" });

  try {
    const response = await fetch(`${KIE_BASE}/jobs/recordInfo?taskId=${encodeURIComponent(taskId)}`, {
      headers: kieHeaders(),
    });
    const data = await response.json();
    if (data.code !== 200) return res.status(502).json({ error: data.msg ?? "Kie recordInfo failed" });

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
});

const PORT = process.env.PORT ?? 3000;
app.listen(PORT, () => {
  const keyOk = Boolean(process.env.KIE_AI_API_KEY?.trim());
  console.log(`\n  FrontEnd moodboard generator running at http://localhost:${PORT}\n`);
  if (!keyOk) {
    console.warn(
      "  ⚠  KIE_AI_API_KEY is empty. Generating concepts will work, but images will not.\n" +
        "     Paste your key into .env (KIE_AI_API_KEY=...) and restart.\n"
    );
  }
});
