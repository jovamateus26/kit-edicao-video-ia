# Áudio: voz, trilha e efeitos

## Voz

Limpeza no `build.py` (`02-limpeza-da-fala.md`): highpass 70 Hz, adeclick, debreath −14 dB, micro-fades seno de 20–25 ms,
compressor 3:1 e limiter. O nível final vem do `finalize.sh`: **−14 LUFS integrado / −1 dBTP**, loudnorm em 2 passes,
vídeo copiado sem recodificar, AAC 256 kbps 48 kHz.

## Trilha

- **Notícia/giro:** instrumental minimalista (cyber tech, lo-fi acelerado) ~11 dB abaixo da voz (≈ −24 a −26 dB),
  fade-in curto e fade-out de 1,4 s (`modelos/giro-noticias/.work/trilha.sh`). O mesmo loop pode servir para todos os
  episódios de uma série; para vídeos longos, emende voltas com `acrossfade` de 3 s.
- **Loja/moda:** chic house, pop acústico ou lo-fi chic ~20 dB abaixo da voz, com ducking de verdade: a voz controla um
  `sidechaincompress` na trilha; sem voz (tela final) a trilha sobe para ~12 dB abaixo (`ferramentas/trilha_ducking.sh`).
- **Série técnica "Terminal Noir" e bancada narrada:** sem trilha, só SFX.

### Gerar trilha local com MusicGen (sem serviço pago)

```bash
cd .work && mkdir -p music && cp $PIPE/musicgen.py music/gen.py
TOK=2000 uv run --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
  --with torch --with transformers --with soundfile --with numpy python -I music/gen.py \
  "minimal cyber tech lo-fi instrumental, steady beat, no vocals" loop 7
```

- MusicGen small no CPU; 50 tokens por segundo de áudio; **máximo ~2000 tokens (40 s)**: 2200 dá `IndexError`.
- O 3º argumento é a semente (mude para outra variação). Ouça antes de usar: descarte clipe com crescendo forte ou vocal.
- O `trilha.sh` do giro espera `music/loop.wav`; o `trilha_ducking.sh` espera `music/seed1.wav` e estica com `atempo`
  (mantém o tom) + `dynaudnorm` para tirar o crescendo do fim.
- Verifique a licença dos pesos do modelo para o seu uso. Alternativa: trilhas livres de direitos (ver skill `media-use`).

## Efeitos sonoros (SFX)

Os SFX ficam na skill `media-use` (`audio/assets/sfx/`, licença Pixabay: uso comercial sem atribuição; `CREDITS.md` e
`manifest.json` com duração e uso). Copie os que usar para `assets/sfx/` do projeto.

| Momento | SFX | Volume |
|---|---|---|
| 0:00 do gancho | `impact-bass-2` (sub-bass) + `whoosh-short` | 0,55 / 0,26 |
| Entrada de cada tag (troca de notícia) | `whoosh` | 0,4 |
| Entrada de print | `whoosh-short` (se não houver outro SFX a < 0,15 s) | 0,18 |
| Instante do grifo (marca-texto) | `click-soft` | 0,26 |
| Chip "Segue @perfil" | `pop` | 0,26 |
| Erro/tela de falha (bancada) | `glitch-1` | conforme o caso |
| Print grande por cima do rosto | whoosh suave | baixo |

O `make.py` do giro distribui os SFX em trilhas (`data-track-index` 11–29) sem sobrepor e corta cada um no fim da composição.
Mixagem fina (fades, ducking, EQ) dentro do HyperFrames: skill `hyperframes-audio`.
