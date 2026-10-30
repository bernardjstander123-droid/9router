#!/usr/bin/env python3
import argparse
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument("--comfyui",type=Path,required=True);a=p.parse_args()
names={"diffusion_models":"wan2.2_ti2v_5B_fp16.safetensors","text_encoders":"umt5_xxl_fp8_e4m3fn_scaled.safetensors","vae":"wan2.2_vae.safetensors"}
ok=True
for folder,name in names.items():
 path=a.comfyui/"models"/folder/name
 exists=path.is_file() and path.stat().st_size>1024*1024
 print(("OK" if exists else "MISSING"),path, path.stat().st_size if exists else "")
 ok &= exists
raise SystemExit(0 if ok else 1)
