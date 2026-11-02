# Modelos

Projetos de referência tirados de vídeos publicados, com nomes, @ e falas trocados por marcadores. Copie o do formato
escolhido para a pasta do episódio e adapte.

| Pasta | O que tem | Estado |
|---|---|---|
| `giro-noticias/` | projeto completo: `package.json`, `hyperframes.json` e a `.work` com `captions.py`, `make.py`, `tpl.html`, `capture.mjs`, `probe.mjs`, `para.mjs`, `juntar_prints.py`, `jobs.exemplo.json`, `estudio.json`, `trilha.sh`, `entrega.py` | o mais novo; ponto de partida padrão |
| `noticia-com-prova/` | `tpl.html`, `make.py`, `captions.py`, `tops.mjs` | referência de layout com split |
| `app-resultado/` | `tpl.html`, `make.py`, `captions.py` | referência (painel do app + rosto) |
| `loop-split/` | `tpl.html`, `make.py`, `captions.py` | referência (loop perfeito, player com karaokê da voz de IA) |
| `bancada-narrada/` | `tpl.html`, `make.py`, `captions.py` | referência (selo de etapa, cards, timelapse) |
| `entrevista-game-show/` | `tpl.html`, `make.py`, `captions.py`, `trilha.sh` | referência (quem fala na legenda, contadores, pulo) |
| `moda-clean-luxury/` | `tpl.html`, `make.py`, `captions.py`, `trilha.sh` | referência (punch-ins, tela final clara, ducking) |
| `briefing-edicao.modelo.md` | briefing de pauta/estilo que o criador pode mandar junto com o vídeo | |
| `plano-edicao.modelo.md` | plano de edição em tabela (útil com muitos clipes) | |
| `giro-noticias/publicacao_copy.modelo.md` | texto de publicação + conferência das falas | |

## Como começar um episódio a partir do giro

```bash
EP="Noticias/2026-10-30"                                   # pasta do episódio, com os brutos dentro
cp -r $PIPE/../modelos/giro-noticias "$EP/giro"            # projeto HyperFrames
cp $PIPE/build_template.py "$EP/giro/.work/build.py"
cp "$EP/giro/.work/jobs.exemplo.json" "$EP/giro/.work/jobs.json"
mkdir -p "$EP/giro/assets/"{footage,img,music,sfx} "$EP/final"
cp <skills>/media-use/audio/assets/sfx/{whoosh,whoosh-short,click-soft,pop,impact-bass-2}.mp3 "$EP/giro/assets/sfx/"
cd "$EP/giro/.work" && npm i puppeteer-core               # para o capture.mjs
```

Depois siga `../guias/01-fluxo.md`. No `make.py`, troque só o que está nas seções "POR EPISÓDIO"; os valores que estão
lá são do exemplo (um giro de 5 notícias).

## Os modelos de referência (outros formatos)

São de episódios mais antigos. O que mudou desde então e vale para eles também:

- Transcrição da fala montada: `wh edit` (os docstrings citam `mapwords.py`, `fillers.py`, `transcribe_edit.py`, que
  foram substituídos por ele).
- Montagem: sempre o `ferramentas/build_template.py` (tem REFINE por fonte, `xN` e cauda com fade).
- Legenda: o `captions.py` de cada formato produz o `data.json` que o `make.py` daquele formato espera (com quem fala,
  títulos, karaokê do player). Mantenha o par `captions.py` + `make.py` + `tpl.html` do mesmo formato.
- Nos `captions.py` com `FIX`/`INS`/`SHIFT` (correções por índice de palavra), prefira o estilo do giro: texto revisado
  em `TEXT` alinhado por `difflib`, que não quebra quando a EDL muda.
