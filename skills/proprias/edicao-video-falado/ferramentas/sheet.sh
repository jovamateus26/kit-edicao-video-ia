#!/usr/bin/env bash
# Folha de quadros para olhar o material rápido: sheet.sh VIDEO SAIDA.jpg [intervalo_s=5] [largura=270] [colunas=6]
# Lê só quadros-chave (-skip_frame nokey) e reduz ANTES do tonemap do HDR: segundos mesmo em arquivo longo.
set -euo pipefail
PYBIN=python3; "$PYBIN" -c "" 2>/dev/null || PYBIN=python   # Git Bash no Windows: lá o python3 da Store é só um atalho
py() { "$PYBIN" -X utf8 -c "$@" | tr -d '\r'; }               # -X utf8 e sem \r: acentos e números certos no Windows
IN="$1"; OUT="$2"; EVERY="${3:-5}"; WID="${4:-270}"; COLS="${5:-6}"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$IN" | tr -d '\r')
N=$(py "import math; print(max(1, math.ceil($DUR / $EVERY)))")
ROWS=$(( (N + COLS - 1) / COLS ))
TRC=$(ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of default=nw=1:nk=1 "$IN" | tr -d '\r')
VF="fps=1/$EVERY,scale=$WID:-2"
if [ "$TRC" = "arib-std-b67" ] || [ "$TRC" = "smpte2084" ]; then
  VF="fps=1/$EVERY,zscale=w=$WID:h=-2:tin=$TRC:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
fi
ffmpeg -v error -y -skip_frame nokey -i "$IN" -vf "$VF,tile=${COLS}x${ROWS}:padding=4" -frames:v 1 "$OUT"
echo "$OUT: $N quadros a cada $EVERY s (${COLS}x${ROWS})"
