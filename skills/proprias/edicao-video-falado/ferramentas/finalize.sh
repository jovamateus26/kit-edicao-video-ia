#!/usr/bin/env bash
# Normaliza o áudio do render para -14 LUFS / -1 dBTP (loudnorm em 2 passes), copia o vídeo sem re-encode.
# Uso: finalize.sh <entrada.mp4> <saida.mp4>
set -euo pipefail
PYBIN=python3; "$PYBIN" -c "" 2>/dev/null || PYBIN=python   # Git Bash no Windows: lá o python3 da Store é só um atalho
py() { "$PYBIN" -X utf8 -c "$@" | tr -d '\r'; }               # -X utf8 e sem \r: acentos e números certos no Windows
IN="$1"; OUT="$2"
export LC_ALL=C
STATS=$(ffmpeg -hide_banner -nostats -i "$IN" -vn -af loudnorm=I=-14:TP=-1.0:LRA=11:print_format=json -f null - 2>&1 | sed -n '/^{/,/^}/p')
get() { echo "$STATS" | py "import json,sys; print(json.load(sys.stdin)['$1'])"; }
ffmpeg -hide_banner -v error -y -i "$IN" -map 0:v:0 -map 0:a:0 -c:v copy \
  -af "loudnorm=I=-14:TP=-1.0:LRA=11:measured_I=$(get input_i):measured_TP=$(get input_tp):measured_LRA=$(get input_lra):measured_thresh=$(get input_thresh):offset=$(get target_offset):linear=true:print_format=summary,aresample=48000" \
  -c:a aac -b:a 256k -ar 48000 -movflags +faststart "$OUT"
echo "entrada: I=$(get input_i) LUFS TP=$(get input_tp) dBTP"
ffmpeg -hide_banner -nostats -i "$OUT" -vn -af ebur128=peak=true -f null - 2>&1 | grep -E "^\s+(I|Peak):" | tr -s ' '
