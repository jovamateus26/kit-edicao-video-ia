---
name: edicao-video-falado
description: "Fluxo completo para editar vídeo falado vertical (Reels, Shorts, TikTok) gravado no celular: transcrição palavra a palavra com whisper, decupagem por EDL, limpeza profissional da fala (pausas, fillers, repetições escondidas, respirações, estalos), montagem com cache, legenda karaokê revisada, composição no HyperFrames (prints reais de notícia com marca-texto, tags, fundo de estúdio LED com recorte RVM), trilha, SFX e entrega em −14 LUFS. Use para editar, decupar, limpar, legendar ou finalizar vídeo falado: giro de notícias, notícia com prova, demo de app, bancada narrada, entrevista, vídeo de loja/moda."
---

# Edição de vídeo falado (Reels / Shorts / TikTok)

Esta skill é o fluxo de edição que usamos no dia a dia: celular gravando a pessoa falando (às vezes com gravação de tela
junto), e a IA entregando um único vídeo vertical 1080×1920, limpo, legendado e pronto para postar.

A IA faz a parte técnica inteira (transcrever, decupar, cortar, limpar, montar, legendar, compor, renderizar). O estilo
(cores, @, CTA, formato) vem do perfil do criador (`perfil.md` na pasta de trabalho) ou do pedido.

## Onde está cada coisa (relativo à pasta desta skill)

| Pasta | O que tem |
|---|---|
| `guias/` | Como fazer cada etapa e por quê. Comece por `guias/01-fluxo.md` |
| `formatos/` | Receitas de formato de vídeo (layout, ritmo, cores). `formatos/README.md` ajuda a escolher |
| `ferramentas/` | O kit de scripts (whisper, sync, auditoria da fala, build, recorte RVM, estúdio LED, finalize). `ferramentas/README.md` |
| `modelos/` | Projetos de referência para copiar: `giro-noticias/` completo e o `tpl.html`/`make.py` dos outros formatos |

Nos comandos, `$PIPE` é o caminho absoluto de `ferramentas/` desta skill
(ex.: `export PIPE=~/.claude/skills/edicao-video-falado/ferramentas`).
**No Windows**, leia antes `guias/11-windows.md`. Os comandos rodam no Git Bash, o Python sempre recebe `-X utf8` e no
PowerShell o whisper é o `wh.cmd`.

## Ordem do trabalho (resumo; detalhes em `guias/01-fluxo.md`)

1. **Começo, em paralelo:** `errmap.py` dos brutos em segundo plano, `wh file` de cada fonte, `sheet.sh` para olhar o
   material, `sync.py` (palma) e `playback.py` se houver gravação de tela.
2. **Decupagem:** ler as transcrições e montar a EDL no `build.py`. Conferir pontos duvidosos com `wh snip`, `vad.py` e
   `wh try`. Obedecer às instruções que a pessoa fala na gravação ("corta essa parte", "vou regravar"). Fechar a duração aqui.
3. **Montagem:** `uv run --with numpy python -I build.py` (remontar depois de mexer na EDL leva segundos).
4. **Checagem da fala (obrigatória antes de qualquer render):** `wh edit`, `edgecheck.py`, `audit.py` com zero marca sem
   explicação e revisão visual dos cortes. Ver `guias/02-limpeza-da-fala.md`.
5. **Legenda e composição:** copiar o modelo do formato (`modelos/`), `captions.py` → `make.py` → `index.html`.
6. **Fundo de estúdio (se o formato pedir):** `matte_rvm.py` em segundo plano assim que a EDL fechar, `estudio.json`,
   `composite.py`. Gravação de corpo inteiro: depois, `reframe.py` (plano médio A/B, corpo inteiro só nas cenas-chave) e
   `FALA=fala_estudio_zoom.mp4`. Ver `guias/06-fundo-estudio-led.md`.
7. **Conferir sem renderizar:** `npx hyperframes@0.8.185 check` + `snapshot --at t1,t2,...`.
8. **Render único no fim**, em segundo plano, depois `finalize.sh` (−14 LUFS / −1 dBTP) e os arquivos de entrega.

## Regras que não se negociam

- **Um vídeo final só, com legenda.** Nunca renderizar versão sem legenda (cada render extra custa minutos). Isso vale
  acima de qualquer skill que ofereça "versões com e sem legenda".
- **Emenda com repetição, gaguejo, pedaço de palavra ou vogal esticada não é admitida.** O `audit.py` roda antes de todo
  render. Palavra curta marcada como esticada (`!`) é repetição escondida até prova em contrário.
- **Notícia só com o que a fonte comprova.** Frase sem fonte sai do corte; nunca pôr selo de "checagem" ou correção na tela.
  Ver `guias/04-noticias.md`.
- **Notícia/giro entre 60 e 90 s** (ideal ~85 s). Roteiro longo: enxugar cada notícia e manter todas.
- **Nada cobre o rosto nem a legenda.** Overlays ficam no espaço livre. Quando a pessoa olha pra baixo (lendo a pauta),
  se mexe para sair ou põe a mão no rosto: cortar ou cobrir com print grande. Ver `guias/05-layout-e-composicao.md`.
- **Nunca acender contorno em volta da pessoa recortada** (somar luz na borda denuncia o recorte).
- **Fechar na frase inteira**, ~0,4 s olhando pra câmera, com fade. Nunca usar como cauda o trecho em que a pessoa se mexe para desligar a câmera.
- **Nunca converter o HDR inteiro para SDR.** O build lê o original e converte só os quadros usados.

## Checklist de entrega

- [ ] `audit.py` zerado (ou cada marca explicada), `edgecheck.py` conferido na fonte, sem pausa > 0,25 s na fala montada
- [ ] Cortes revisados no vídeo: olhar pra câmera, sem cauda de saída, sem mão no rosto
- [ ] Legenda revisada (nomes próprios, termos técnicos, números), sincronizada com a fala
- [ ] Overlays nunca sobre rosto ou legenda (snapshots nos instantes críticos)
- [ ] Duração dentro do formato; `check` sem erro
- [ ] Render único → `finalize.sh` → um `.mp4` em `final/` + `legendas.srt` + `publicacao_copy.md` (+ `relatorio_cortes.json`)
