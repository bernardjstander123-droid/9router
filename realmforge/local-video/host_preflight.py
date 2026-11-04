#!/usr/bin/env python3
"""Read-only checks for a local RealmForge Wan2.2 5B ComfyUI GPU host.

This does not install packages, download models, run inference or expose services.
All external HTTP checks are restricted to the loopback interface.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request

MODELS = {
    "diffusion_model": ("diffusion_models", "wan2.2_ti2v_5B_fp16.safetensors"),
    "text_encoder": ("text_encoders", "umt5_xxl_fp8_e4m3fn_scaled.safetensors"),
    "vae": ("vae", "wan2.2_vae.safetensors"),
}


def model_file_status(path: Path) -> dict:
    """Presence and basic integrity only, not a cryptographic model verification."""
    if not path.is_file():
        return {"ok": False, "reason": "missing", "filename": path.name}
    try:
        size = path.stat().st_size
        with path.open("rb") as stream:
            prefix = stream.read(80)
    except OSError:
        return {"ok": False, "reason": "unreadable", "filename": path.name}
    if prefix.startswith(b"version https://git-lfs.github.com/spec/v1"):
        return {"ok": False, "reason": "git-lfs pointer, not model weights", "filename": path.name}
    if size < 1024 * 1024:
        return {"ok": False, "reason": "too small to be a complete model", "filename": path.name}
    return {"ok": True, "reason": "present (model loading unverified)", "filename": path.name, "bytes": size}


def gpu_status() -> dict:
    """Require positive CUDA evidence; never infer a functional GPU from an APK or RAM."""
    try:
        if importlib.util.find_spec("torch") is None:
            return {"ok": False, "reason": "PyTorch missing: CUDA not verified"}
        import torch  # type: ignore[import-not-found]
        if not torch.cuda.is_available():
            return {"ok": False, "reason": "PyTorch CUDA not available"}
        return {
            "ok": True,
            "reason": "PyTorch detects CUDA (Wan inference still unverified)",
            "devices": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "vram_gib": [round(torch.cuda.get_device_properties(i).total_memory / (1024**3), 1)
                         for i in range(torch.cuda.device_count())],
        }
    except (Exception, RuntimeError) as error:
        return {"ok": False, "reason": "CUDA check failed: " + type(error).__name__}


def comfy_status(url: str) -> dict:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost", "::1") or parts.username or parts.password or parts.query or parts.fragment or parts.path not in ("", "/"):
        return {"ok": False, "reason": "Only a loopback HTTP ComfyUI URL is permitted"}
    try:
        with urllib.request.urlopen(url.rstrip("/") + "/system_stats", timeout=4) as response:
            data = json.load(response)
        if not isinstance(data, dict) or "system" not in data:
            return {"ok": False, "reason": "ComfyUI endpoint returned unexpected JSON"}
        return {"ok": True, "reason": "ComfyUI responds on loopback (workflow unverified)"}
    except (OSError, ValueError, urllib.error.URLError, TimeoutError):
        return {"ok": False, "reason": "ComfyUI is not responding on loopback"}


def workflow_status(runtime: Path) -> dict:
    workflow, bindings = runtime / "workflow_api.json", runtime / "bindings.json"
    if not workflow.is_file() or not bindings.is_file():
        return {"ok": False, "reason": "Export workflow_api.json and configure bindings.json"}
    try:
        graph = json.loads(workflow.read_text(encoding="utf-8"))
        mapping = json.loads(bindings.read_text(encoding="utf-8"))
        if not isinstance(graph, dict) or not isinstance(mapping, dict):
            return {"ok": False, "reason": "Workflow or bindings must be JSON objects"}
        for label in ("positive_prompt",):
            entry = mapping.get(label)
            if not isinstance(entry, dict) or not isinstance(entry.get("node"), str) or not isinstance(entry.get("input"), str):
                return {"ok": False, "reason": "Missing binding: " + label}
            node = graph.get(entry["node"])
            if not isinstance(node, dict) or entry["input"] not in node.get("inputs", {}):
                return {"ok": False, "reason": "Binding does not match workflow: " + label}
        if "reference_image" in mapping:
            entry = mapping["reference_image"]
            if not isinstance(entry, dict) or not isinstance(entry.get("node"), str) or not isinstance(entry.get("input"), str):
                return {"ok": False, "reason": "Invalid reference_image binding"}
            node = graph.get(entry["node"])
            if not isinstance(node, dict) or entry["input"] not in node.get("inputs", {}):
                return {"ok": False, "reason": "reference_image node missing or input incorrect"}
        return {"ok": True, "reason": "Mappings present (model nodes and graph connectivity unverified)"}
    except (OSError, UnicodeError, ValueError, TypeError):
        return {"ok": False, "reason": "Workflow or bindings is unreadable/invalid JSON"}


def check(comfy_root: Path, runtime: Path, url: str) -> dict:
    root = comfy_root.expanduser().resolve()
    local_runtime = runtime.expanduser().resolve()
    checks = {
        "cuda": gpu_status(),
        "ffprobe": {"ok": shutil.which("ffprobe") is not None,
                    "reason": "FFprobe installed" if shutil.which("ffprobe") else "FFprobe missing"},
        "comfyui": comfy_status(url),
        "workflow": workflow_status(local_runtime),
    }
    for label, (subdir, name) in MODELS.items():
        checks[label] = model_file_status(root / "models" / subdir / name)
    ready = all(entry["ok"] for entry in checks.values())
    return {
        "preflight_passed": ready,
        "inference_verified": False,
        "checks": checks,
        "next_step": ("Run one real ComfyUI job and FFprobe the generated MP4"
                      if ready else "Fix failed checks, then rerun preflight"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--comfy-root", type=Path, required=True, help="ComfyUI installation directory")
    ap.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parent / "runtime")
    ap.add_argument("--comfy-url", default="http://127.0.0.1:8188")
    args = ap.parse_args()
    report = check(args.comfy_root, args.runtime_root, args.comfy_url)
    print(json.dumps(report, indent=2))
    return 0 if report["preflight_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
