#!/usr/bin/env bash
# Trilha (MusicGen small, music/seed1.wav ~32 s) em loop com crossfade de 1,5 s até a duração do vídeo,
# com auto-ducking de verdade: sidechaincompress com a voz (fala.mp4) como chave.
# Níveis: sob a voz ~20 dB abaixo dela; na tela final (sem voz) +4 dB para não ficar morta; fade-out de 1,6 s.
# Uso: ./trilha.sh   (rodar depois do build.py e do make.py)
set -euo pipefail
cd "$(dirname "$0")"
export LC_ALL=C
SPEECH=$(python3 -c "import json;print(json.load(open('data.json'))['speech'])")
DUR=$(python3 -c "import re;print(re.search(r'data-composition-id=\"main\" data-start=\"0\" data-duration=\"([0-9.]+)\"', open('../index.html').read()).group(1))")
lufs() { ffmpeg -hide_banner -nostats -i "$1" -vn -af ebur128 -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}'; }
VI=$(lufs ../assets/footage/fala.mp4)
# 1) loop: 5 cópias da semente com crossfade (a semente tem 32 s; 5 x 32 - 4 x 1,5 = 154 s), corta na duração
ffmpeg -v error -y -i music/seed1.wav -i music/seed1.wav -i music/seed1.wav -i music/seed1.wav -i music/seed1.wav -filter_complex \
  "[0][1]acrossfade=d=1.5:c1=qsin:c2=qsin[a];[a][2]acrossfade=d=1.5:c1=qsin:c2=qsin[b];[b][3]acrossfade=d=1.5:c1=qsin:c2=qsin[c];\
   [c][4]acrossfade=d=1.5:c1=qsin:c2=qsin,atrim=0:$DUR,aresample=48000,dynaudnorm=f=400:g=15:m=12:p=0.9[o]" \
  -map "[o]" -ac 2 -c:a pcm_f32le music/long.wav
MI=$(lufs music/long.wav)
G=$(python3 -c "print(round(($VI - 12) - ($MI), 2))")
# 2) ducking: a voz (mono, com a tela final em silêncio) controla o compressor da trilha
ffmpeg -v error -y -i music/long.wav -i ../assets/footage/fala.mp4 -filter_complex \
  "[0:a]volume=${G}dB[m];[1:a]aresample=48000,apad=whole_dur=$DUR,pan=stereo|c0=c0|c1=c0[k];\
   [m][k]sidechaincompress=threshold=0.05:ratio=2.5:attack=25:release=380:knee=4:makeup=1[d];\
   [d]volume=1.6:enable='gte(t,$SPEECH)',afade=t=in:d=0.2,afade=t=out:st=$(python3 -c "print($DUR - 1.6)"):d=1.6[o]" \
  -map "[o]" -c:a pcm_f32le music/duck.wav
ffmpeg -v error -y -i music/duck.wav -c:a aac -b:a 192k ../assets/music/trilha.m4a
SUB=$(ffmpeg -hide_banner -nostats -i music/duck.wav -af "atrim=1:$SPEECH,ebur128" -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
FIM=$(ffmpeg -hide_banner -nostats -i music/duck.wav -af "atrim=$SPEECH:$(python3 -c "print($DUR - 1.6)"),ebur128" -f null - 2>&1 | grep -E "^\s+I:" | tail -1 | awk '{print $2}')
echo "voz $VI LUFS | trilha sob a voz $SUB ($(python3 -c "print(round($SUB - $VI, 1))") dB) | tela final $FIM ($(python3 -c "print(round($FIM - $VI, 1))") dB) | dur $DUR"
