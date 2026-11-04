# RealmForge Local Video: no Runway / no third-party queue

A Python standard-library HTTP job queue + worker for **real ComfyUI-generated MP4** videos. It does not call Runway, and it does not use the 3Min queue or any credit ledger. It does **not** include ComfyUI, model weights, a GPU, or an artificial claim that AI inference has occurred.

The interface accepts a prompt and an optional **original local reference image** for the existing Demon God / eight-wing continuity workflow. The configured, real ComfyUI workflow must actually connect its LoadImage input to the video generation pipeline: a disconnected reference node is not identity preservation.

## Host requirements

- A trusted computer / GPU host running Python 3.10+, `ffprobe`, and [ComfyUI](https://github.com/Comfy-Org/ComfyUI) listening on `127.0.0.1:8188` (or a trusted loopback SSH tunnel).
- Proper **video-generation checkpoints and API-format** workflow exported from your installed ComfyUI. See [official Wan 2.2 instructions](https://docs.comfy.org/tutorials/video/wan/wan2_2) for 5B and 14B workflow and model choices. **8 GB phone RAM is not 8 GB dedicated GPU VRAM.** Wan models may require significant GPU memory and disk space. Never assume that an Android A07 alone can run them.
- An original character image under `runtime/assets/character.png`. No copyrighted/private character images or secrets are stored in Git.
- LAN/mobile access requires a trusted TLS reverse proxy and authentication. The Python server intentionally binds to **loopback only**. Do not forward `8188` or `5678` to the public internet.

## Configure on a host with ComfyUI

From `realmforge/local-video`:

```bash
python3 -m venv .venv
# Activate the virtual environment if desired; no pip requirements for this backend.
mkdir -p runtime/assets
cp bindings.example.json runtime/bindings.json
# Export your own workflow via ComfyUI > Save (API Format) as runtime/workflow_api.json.
# Update node IDs in runtime/bindings.json from that API export.
# Put your real original image at runtime/assets/character.png.
export RF_LOCAL_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export RF_LOCAL_ROOT="$PWD/runtime"
python3 local_video.py check
```

`RF_LOCAL_TOKEN` must be the **same secret in both processes**. Store it in a secure host environment or secret manager, not in your repo or commands that persist into history. It is used only for your local backend; it does not authorize Runway access.

Start in two separate host sessions (same environment variables):

```bash
python3 local_video.py serve
python3 local_video.py worker
```

Submit your own image-to-video job from the same host (substitute your actual token in the environment, not in the command line):

```bash
curl -sS -X POST http://127.0.0.1:5678/v1/jobs \
  -H "Authorization: Bearer $RF_LOCAL_TOKEN" -H 'Content-Type: application/json' \
  -d '{"prompt":"An original eight-wing Demon God awakens under storm clouds, cinematic sweeping camera and realistic motion","reference_image":"character.png"}'
```

Poll `GET /v1/jobs/{id}` with the same bearer token. If `status` is `completed`, fetch `GET /v1/jobs/{id}/video` with the token for the validated MP4. The public unauthenticated `GET /health` only reports that the process is online. Authenticated `GET /ready` reports workflow, FFprobe, server connectivity and token setup, **not inference readiness**.

For text-to-video workflows, omit `reference_image` and remove the `reference_image` mapping from bindings, using a corresponding text-to-video API graph. Frame count, FPS, resolution, and model configuration come **from that exported graph**, not the request, to prevent false precision. MP4 metadata is read back using actual FFprobe output.

## State, safety, and failures

- SQLite queue states: `queued → running → completed / failed`. A single worker is recommended. A worker crash leaves a `running` job needing manual inspection/re-enqueue; this prevents blindly resubmitting potentially in-flight GPU work.
- **No synthetic or placeholder video** is ever returned as an AI generation. The test suite deliberately uses synthetic FFmpeg content to exercise transfer and verification only.
- Max JSON request 16 KiB, local reference 32 MiB, MP4 1 GiB. The reference image must resolve beneath `runtime/assets`; no URLs or arbitrary file paths. Only `http://localhost` / other loopback ComfyUI endpoints are accepted. Use a trusted SSH tunnel for a separate GPU host.
- A saved MP4 must appear in ComfyUI history. The worker downloads it, FFprobes its stream/duration/dimensions, then sets `completed`. Rejected or broken MP4s are never advertised as completed.
- This is a **new standalone backend**. It does not change the existing 3Min pipeline, Android APK, or provide a live external server.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

The tests validate authentication, path controls, queue behavior, binding mapping, and MP4 transfer using a **mock ComfyUI server** and FFmpeg fixture. Passing them does not confirm actual Wan inference, GPU driver compatibility, external Android connectivity or APK installation. Verify those separately on the target GPU computer and Samsung Galaxy A07.
