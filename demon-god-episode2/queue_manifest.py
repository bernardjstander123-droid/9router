#!/usr/bin/env python3
"""Turn Episode 2's shot manifest into BTU Cinema sandbox queue records.

Default mode is offline and does not submit, render, or spend credits.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import urllib.request

DEFAULT_API = "https://api.3minapi.com/api/v1/data/o8mxl7uhc7371qouz39de"


def safe_reference(root, uri):
    if not isinstance(uri, str) or not uri.startswith("local://"):
        raise ValueError("Original reference must use local://")
    relative = uri[len("local://"):]
    if not relative or relative.startswith("/") or "\\" in relative or any(
        p in ("", ".", "..") for p in relative.split("/")
    ):
        raise ValueError("Unsafe original reference path")
    root = root.resolve()
    path = (root / relative).resolve()
    if root not in path.parents or not path.is_file():
        raise FileNotFoundError("Original character reference missing or outside root")
    if path.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
        raise ValueError("Original reference must be an image")
    return path


def make_jobs(manifest):
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be an object")
    width, height, fps = (manifest.get(k) for k in ("width", "height", "fps"))
    if any(type(n) is not int for n in (width, height, fps)) or not (
        64 <= width <= 3840 and 64 <= height <= 3840 and
        width % 2 == 0 and height % 2 == 0 and 1 <= fps <= 120
    ):
        raise ValueError("Invalid even video dimensions or fps")
    if manifest.get("protagonist_wings") != 8:
        raise ValueError("Eight-wing protagonist continuity gate failed")
    reference = manifest.get("original_character_reference")
    if not isinstance(reference, str) or not reference.startswith("local://"):
        raise ValueError("Original character reference missing")
    shots = manifest.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ValueError("No shots in manifest")
    project = re.sub(r"[^a-z0-9]+", "-", str(manifest.get("project", "episode")).lower()).strip("-")[:60]
    if not project:
        raise ValueError("Invalid project name")
    jobs, ids, total = [], set(), 0.0
    for shot in shots:
        if not isinstance(shot, dict):
            raise ValueError("Shot must be an object")
        number = shot.get("id")
        if type(number) is not int or not 1 <= number <= 999 or number in ids:
            raise ValueError("Shot IDs must be unique positive integers")
        ids.add(number)
        expected_file = f"renders/shot_{number:02d}.mp4"
        if shot.get("file") != expected_file:
            raise ValueError(f"Unexpected shot path: {shot.get('file')}")
        duration = shot.get("duration_seconds")
        if type(duration) not in (int, float) or not 0.2 <= duration <= 30:
            raise ValueError(f"Invalid shot duration: {number}")
        prompt = shot.get("prompt")
        if not isinstance(prompt, str) or len(prompt.strip()) < 10:
            raise ValueError(f"Missing usable prompt for shot {number}")
        if shot.get("wings", 8) != 8 or shot.get("character_reference", reference) != reference:
            raise ValueError(f"Original character continuity mismatch in shot {number}")
        total += duration
        jobs.append({
            "project_id": project, "scene_id": f"shot_{number:02d}",
            "prompt": prompt.strip(), "character_reference": reference,
            "wings": 8, "width": width, "height": height,
            "fps": fps, "duration_seconds": duration,
            "render_status": "queued", "output_uri": ""
        })
    if sorted(ids) != list(range(1, len(shots) + 1)):
        raise ValueError("Shot numbering must be contiguous from 1")
    estimated = manifest.get("estimated_duration_seconds")
    if type(estimated) not in (int, float) or abs(total - estimated) > 0.001:
        raise ValueError(f"Manifest duration mismatch: shots={total}, estimate={estimated}")
    return jobs


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                 prefix=".btu-", suffix=".tmp", delete=False) as f:
        tmp = Path(f.name)
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")
    try:
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def submit_jobs(jobs, *, api, token, receipt_file):
    if api.rstrip("/") != DEFAULT_API:
        raise ValueError("Only the existing BTU Cinema sandbox queue is supported")
    if not token.startswith("tm_test_"):
        raise ValueError("Sandbox key required; production keys refused")
    receipts = json.loads(receipt_file.read_text()) if receipt_file.exists() else {}
    if not isinstance(receipts, dict):
        raise ValueError("Invalid receipt file")
    for job in jobs:
        scene = job["scene_id"]
        digest = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()
        if scene in receipts:
            if receipts[scene].get("digest") != digest:
                raise ValueError(f"Scene {scene} changed since previous submission")
            continue
        req = urllib.request.Request(api, method="POST", data=json.dumps(job).encode(),
                                     headers={"Authorization": "Bearer " + token,
                                              "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode("utf-8"))
            if response.status != 202 or not body.get("data", {}).get("id"):
                raise RuntimeError(f"Queue did not confirm acceptance for {scene}")
            record_id = body["data"]["id"]
        receipts[scene] = {"digest": digest, "record_id": record_id}
        atomic_json(receipt_file, receipts)
    return receipts


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, default=Path(__file__).with_name("shots.json"))
    ap.add_argument("--output", type=Path, default=Path("output/episode2-queue-jobs.json"))
    ap.add_argument("--reference-root", type=Path)
    ap.add_argument("--receipt-file", type=Path, default=Path(".btu-submission-receipts.json"))
    ap.add_argument("--submit", action="store_true", help="Submit sandbox jobs (default: offline plan only)")
    args = ap.parse_args()
    jobs = make_jobs(json.loads(args.manifest.read_text(encoding="utf-8")))
    atomic_json(args.output, jobs)
    if args.submit:
        if args.reference_root is None:
            ap.error("--reference-root required for submission")
        safe_reference(args.reference_root, jobs[0]["character_reference"])
        token = os.environ.get("BTU_3MIN_API_KEY", "")
        receipts = submit_jobs(jobs, api=DEFAULT_API, token=token, receipt_file=args.receipt_file)
        print(json.dumps({"status": "sandbox_records_accepted", "count": len(receipts)}))
    else:
        print(json.dumps({"status": "offline_plan_only", "shots": len(jobs),
                          "duration_seconds": sum(j["duration_seconds"] for j in jobs),
                          "output": str(args.output)}))


if __name__ == "__main__":
    main()
