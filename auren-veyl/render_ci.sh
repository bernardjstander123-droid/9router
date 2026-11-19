#!/usr/bin/env bash
set -euo pipefail
mkdir -p renders
ffmpeg -hide_banner -loglevel error -y \
  -f lavfi -i "color=c=0x051122:s=1280x720:r=24:d=18" \
  -loop 1 -framerate 24 -i assets/auren_original.webp \
  -filter_complex "[1:v]format=rgba,scale=710:710:flags=lanczos[actor];[0:v][actor]overlay=x='570-1.4*t':y='-14-0.6*t':shortest=1:format=auto,drawbox=x=0:y=0:w=1280:h=720:c=0x003a40@0.13:t=fill:enable='between(t,6,10)',drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='THE OMNI AWAKENING':fontcolor=0x7cf4df:fontsize=29:x=76:y=126,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='AUREN VEYL':fontcolor=white:fontsize=82:x=74:y=185,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='THE SO-CALLED HONOURED ONE':fontcolor=0x9df9ed:fontsize=26:x=78:y=306,drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='ETERNAL STILLNESS':fontcolor=0x83ffe9:fontsize=34:x=78:y=575:enable='between(t,6,11)',drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:text='OMNI VERDICT':fontcolor=0x83ffe9:fontsize=34:x=78:y=575:enable='between(t,11,17)',fade=t=in:st=0:d=1,fade=t=out:st=17:d=1,format=yuv420p[v]" \
  -map '[v]' -t 18 -an -c:v libx264 -preset veryfast -crf 22 -movflags +faststart renders/Auren_Veyl_Opening.mp4
ffprobe -v error -show_entries stream=codec_name,width,height:format=duration -of default=noprint_wrappers=1 renders/Auren_Veyl_Opening.mp4
