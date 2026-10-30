#!/usr/bin/env python3
"""Download official ComfyUI Wan2.2 5B model assets into an existing ComfyUI checkout."""
import argparse
from pathlib import Path
from huggingface_hub import hf_hub_download
REPO = "Comfy-Org/Wan-2.2"
FILES = (
 ("split_files/diffusion_models/wan2.2_ti2v_5B_fp16.safetensors", "diffusion_models"),
 ("split_files/text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors", "text_encoders"),
 ("split_files/vae/wan2.2_vae.safetensors", "vae"),
)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--comfyui",type=Path,required=True)
 a=p.parse_args()
 base=a.comfyui.expanduser().resolve()
 if not (base/"main.py").is_file(): raise SystemExit("ComfyUI main.py not found; pass the ComfyUI checkout directory")
 for source,folder in FILES:
  destination=base/"models"/folder
  destination.mkdir(parents=True,exist_ok=True)
  name=Path(source).name
  print("Downloading",name,flush=True)
  path=hf_hub_download(repo_id=REPO,filename=source,local_dir=base/"models"/"_realmforge_download_cache")
  target=destination/name
  if target.exists() and target.stat().st_size==Path(path).stat().st_size:
   print("Already installed:",target)
   continue
  import shutil
  shutil.copy2(path,target)
  print("Installed:",target,target.stat().st_size,"bytes")
 print("Wan2.2 5B model assets installed. Restart ComfyUI and load its 5B workflow.")
if __name__=="__main__": main()
