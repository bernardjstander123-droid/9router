# Auren Veyl original-face animated preview

This folder contains a deterministic, no-AI-recasting 18-second MP4 renderer for **The So-Called Honoured One**, using the publicly shared original Tripo portrait as the image input.

## Run

On a Linux host with FFmpeg and FFprobe:

```bash
mkdir -p assets
curl -fL 'https://tripo-public.tripo3d.ai/studio/project/be64fa7b-4c9f-461c-949e-a5371f4abcfc/white-haired-anime-male-character-with-sunglasses-teal-eyes-and-blac.webp' -o assets/auren_original.webp
bash auren-veyl/render_ci.sh
```

The workflow under `.github/workflows/auren-veyl-preview.yml` runs the same process on GitHub Actions and uploads the output MP4 plus ffprobe verification as an artifact.

**Actual AI video inference remains unimplemented** in this fallback. Real ComfyUI Wan 2.2/LTX requires the separate compatible NVIDIA GPU host, model weights, and workflow; GitHub-hosted CPU runners are not a GPU solution. The renderer moves/scales the original portrait and overlays titles/lighting only; it does not animate facial muscles or invent replacement facial features.

The render script itself was smoke tested with a synthetic stand-in image, not with the original face. The workflow must be inspected for a passing Actions run and downloaded artifact before anyone claims an Auren-specific MP4 exists.
