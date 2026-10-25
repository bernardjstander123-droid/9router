# Agent 01 — Personal AI API
OpenAI-compatible chat completions with a self-hosted Qwen2.5 0.5B ONNX model. This is **not** OpenAI's model API and does not provide GPT-6 or other commercial models.

- Production: https://agent01-own-api.vercel.app
- POST /v1/chat/completions (Bearer auth)
- GET /v1/models (Bearer auth)
- GET /health (public)
- Model ID: `agent01-local`
- CPU inference is on demand, not persistent; free Vercel quotas still apply.
- Streaming/tool calls are not supported. No API key is committed to source.
- Key is stored as the encrypted Vercel environment variable `AGENT01_API_KEY`.
- To rotate: change `AGENT01_API_KEY` in Vercel, redeploy, invalidate the old key.
- Same-origin browser demo holds the entered token in memory only, not localStorage.
- Programmatic access: use OpenAI-compatible client with base URL `https://agent01-own-api.vercel.app/v1` and your key.
- Tests: `node scripts/smoke.mjs` runs validation and local inference; `node scripts/remote-smoke.mjs` tests a deployed instance with `AGENT01_API_KEY` from env.
- Security note: serverless doesn't give guaranteed per-user throttling, global spend caps, uptime or 24/7 workers. Rotate tokens if exposed and monitor usage.

Model alias `agent01-local` can retain compatibility when upgrading the underlying free CPU model. The 1.5B model was too large for Vercel serverless temporary storage, so 0.5B is used.
