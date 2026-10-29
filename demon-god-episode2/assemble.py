#!/usr/bin/env python3
"""Verify and assemble real completed video shots. Does not generate AI footage."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

def probe(path):
    p = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration:stream=codec_type,width,height,r_frame_rate","-of","json",str(path)],capture_output=True,text=True,check=True)
    data=json.loads(p.stdout)
    video=next((s for s in data.get("streams",[]) if s.get("codec_type")=="video"),None)
    if not video:
        raise ValueError(f"No video stream: {path}")
    return float(data.get("format",{}).get("duration",0)),video

def assemble(manifest_path,output):
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("Install FFmpeg and ffprobe first")
    root=manifest_path.resolve().parent
    m=json.loads(manifest_path.read_text(encoding="utf-8"))
    clips=[]
    for shot in m["shots"]:
        file=(root/shot["file"]).resolve()
        if root not in file.parents or not file.is_file():
            raise FileNotFoundError(f"Missing or unsafe rendered shot: {shot['file']}")
        duration,stream=probe(file)
        if duration <= 0.1:
            raise ValueError(f"Invalid duration: {file}")
        clips.append(file)
    output=output.resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        listing=Path(tmp)/"concat.txt"
        def esc(path): return str(path).replace("'","'\\''")
        listing.write_text("".join("file '"+esc(p)+"'\n" for p in clips),encoding="utf-8")
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","concat","-safe","0","-i",str(listing),"-c:v","libx264","-pix_fmt","yuv420p","-r",str(m.get("fps",24)),"-vf",f"scale={m.get('width',1080)}:{m.get('height',1920)}:force_original_aspect_ratio=decrease,pad={m.get('width',1080)}:{m.get('height',1920)}:(ow-iw)/2:(oh-ih)/2", "-c:a","aac","-movflags","+faststart",str(output)]
        subprocess.run(cmd,check=True)
    dur,stream=probe(output)
    print(json.dumps({"output":str(output),"status":"VERIFIED_ASSEMBLED","duration_seconds":dur,"width":stream["width"],"height":stream["height"]},indent=2))

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,default=Path(__file__).with_name("shots.json"))
    ap.add_argument("--output",type=Path,default=Path("output/episode2.mp4"))
    args=ap.parse_args()
    assemble(args.manifest,args.output)
