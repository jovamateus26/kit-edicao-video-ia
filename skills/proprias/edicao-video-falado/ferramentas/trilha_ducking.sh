#!/usr/bin/env bash
# Trilha chic house (MusicGen, music/seed1.wav ~39 s) esticada sem mudar o tom (atempo) até a duração do vídeo,
# com auto-ducking de verdade: sidechaincompress com a voz (fala.mp4) como chave.
# Níveis: sob a voz ~20 dB abaixo dela; sem voz (tela final) sobe para ~12 dB abaixo; fade-in curto e fade-out de 1,6 s.
# Uso: ./trilha.sh   (rodar depois do build.py e do make.py)
set -euo pipefail
PYBIN=python3; "$PYBIN" -c "" 2>/dev/null || PYBIN=python   # Git Bash no Windows: lá o python3 da Store é só um atalho
py() { "$PYBIN" -X utf8 -c "$@" | tr -d '\r'; }               # -X utf8 e sem \r: acentos e números certos no Windows
cd "$(dirname "$0")"
export LC_ALL=C
SPEECH=$(py "import json;print(json.load(open('data.json'))['speech'])")
DUR=$(py "import re;print(re.search(r'data-composition-id=\"main\" data-start=\"0\" data-duration=\"([0-9.]+)\"', open('../index.html').read()).group(1))")
SEED=$(ffprobe -v error -show_entries format=duration -of csv=p=0 music/seed1.wav | tr -d '\r')
lufs() { ffmpeg -hide_banner -nostats -i "$1" -vn -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}' | tr -d '\r'; }
VI=$(lufs ../assets/footage/fala.mp4)
# 1) duração: estica a semente (atempo mantém o tom), dynaudnorm tira o crescendo de ~9 dB do fim da semente, nivela em VI-12
TEMPO=$(py "print(round(min(1.0, $SEED / ($DUR + 0.3)), 4))")
ffmpeg -v error -y -i music/seed1.wav -af "atempo=$TEMPO,atrim=0:$DUR,aresample=48000,dynaudnorm=f=400:g=15:m=12:p=0.9" -ac 2 -c:a pcm_f32le music/long.wav
MI=$(lufs music/long.wav)
G=$(py "print(round(($VI - 12) - ($MI), 2))")
# 2) ducking: a voz (mono, com a tela final em silêncio) controla o compressor da trilha
ffmpeg -v error -y -i music/long.wav -i ../assets/footage/fala.mp4 -filter_complex \
  "[0:a]volume=${G}dB[m];[1:a]aresample=48000,apad=whole_dur=$DUR,pan=stereo|c0=c0|c1=c0[k];\
   [m][k]sidechaincompress=threshold=0.05:ratio=2.5:attack=25:release=380:knee=4:makeup=1[d];\
   [d]afade=t=in:d=0.2,afade=t=out:st=$(py "print($DUR - 1.6)"):d=1.6[o]" \
  -map "[o]" -c:a pcm_f32le music/duck.wav
ffmpeg -v error -y -i music/duck.wav -c:a aac -b:a 192k ../assets/music/trilha.m4a
# conferência: nível da trilha sob a voz e na tela final, relativo à voz
SUB=$(ffmpeg -hide_banner -nostats -i music/duck.wav -af "atrim=1:$SPEECH,ebur128" -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}' | tr -d '\r')
FIM=$(ffmpeg -hide_banner -nostats -i music/duck.wav -af "atrim=$SPEECH:$(py "print($DUR - 1.6)"),ebur128" -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}' | tr -d '\r')
echo "voz $VI LUFS | trilha sob a voz $SUB ($(py "print(round($SUB - $VI, 1))") dB) | tela final $FIM ($(py "print(round($FIM - $VI, 1))") dB) | atempo $TEMPO | dur $DUR"
