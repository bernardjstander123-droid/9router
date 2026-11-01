# Episode 2: prepare the 3Min BTU Cinema render queue

This bridge converts the existing 12-shot `shots.json` into the **existing** 3Min BTU Cinema Render Jobs sandbox record schema. It is an offline planning tool by default. It does not render, install Wan 2.2, register a worker, or make an episode available on Android.

## Plan without sending any records

```bash
cd demon-god-episode2
python queue_manifest.py
# output/episode2-queue-jobs.json: 12 records, total 90 seconds
python -m unittest discover -p 'test_*.py' -v
```

The planner checks shot IDs and paths, durations, dimensions, FPS, the 90-second manifest total, eight-wing continuity and the original `local://` character-reference identifier. It assigns a reference to every queued shot because the current ComfyUI worker requires one even for environment shots. The reference image must actually condition the deployed workflow. A string identifier alone does not preserve a face.

## Submit only from a configured sandbox worker host

1. Install ComfyUI, compatible Wan 2.2 I2V checkpoints, a working API-exported workflow, FFmpeg and an actual GPU.
2. Place the **original approved** image at `$BTU_ASSET_ROOT/projects/character_reference.png`. Never substitute a generic portrait.
3. Set `BTU_3MIN_API_KEY` to the sandbox key in the host environment (do not commit it).
4. Run:

```bash
python queue_manifest.py --submit --reference-root "$BTU_ASSET_ROOT"
python comfyui_queue_worker.py --workflow /path/to/wan22_api.json \
  --prompt-node 6 --image-node 10 --reference-root "$BTU_ASSET_ROOT" \
  --output-root "$PWD/renders" --since 2026-10-29 --loop
```

Replace node IDs with those of the actual workflow. Submission requires the original image to exist and rejects non-sandbox keys. The script stores accepted record IDs in `.btu-submission-receipts.json` and skips unchanged scenes on reruns. **Back up this private receipt file:** a crash between HTTP acceptance and writing the receipt can still produce a duplicate on retry. Queue writes consume sandbox API calls; they do not generate videos by themselves.

Only after all 12 actual rendered clips exist and pass verification, run:

```bash
python assemble.py --manifest shots.json \
  --render-root "renders/the-demon-god-s-awakening-episode-2" \
  --output output/episode2.mp4
```

The worker writes clips under `renders/<project_id>/shot_XX.mp4`, whereas the manifest uses `renders/shot_XX.mp4`; `--render-root` resolves that difference without moving or overwriting originals. The assembly command refuses missing or too-short clips and validates the finished MP4. Inspect character identity and wing count visually before any delivery; metadata checks cannot prove identity. Do not describe the offline job plan, queued records or individual shots as a completed episode.
