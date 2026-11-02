#!/usr/bin/env bash
# Trilha: loop do clipe MusicGen (music/loop.wav) cortado na duração da composição (fala + 1,2 s do CTA), ~11 dB abaixo da voz, fade-in curto e fade-out de 1,4 s.
# Uso: ./trilha.sh   (rodar depois do build.py)
set -euo pipefail
PYBIN=python3; "$PYBIN" -c "" 2>/dev/null || PYBIN=python   # Git Bash no Windows: lá o python3 da Store é só um atalho
py() { "$PYBIN" -X utf8 -c "$@" | tr -d '\r'; }               # -X utf8 e sem \r: acentos e números certos no Windows
cd "$(dirname "$0")"
export LC_ALL=C
DUR=$(py "import json;print(round(json.load(open('segs.json'))['duration'] + 2.2, 3))")   # + 2,2 s da tela final
lufs() { ffmpeg -hide_banner -nostats -i "$1" -vn -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}' | tr -d '\r'; }
VI=$(lufs ../assets/footage/fala.mp4)
# o clipe tem ~60 s: três voltas emendadas com crossfade de 3 s cobrem até ~174 s (giro de 29/10 tem 145 s)
ffmpeg -v error -y -i music/loop.wav -i music/loop.wav -i music/loop.wav \
  -filter_complex "[0][1]acrossfade=d=3:c1=tri:c2=tri[x];[x][2]acrossfade=d=3:c1=tri:c2=tri,atrim=0:$DUR" -c:a pcm_s16le music/cut.wav
MI=$(lufs music/cut.wav)
GAIN=$(py "print(round(($VI - 11) - ($MI), 2))")
ffmpeg -v error -y -i music/cut.wav -af "volume=${GAIN}dB,afade=t=in:d=0.25,afade=t=out:st=$(py "print($DUR - 1.4)"):d=1.4" \
  -c:a aac -b:a 192k ../assets/music/trilha.m4a
echo "voz $VI LUFS | trilha $(lufs ../assets/music/trilha.m4a) LUFS | dur $DUR"
