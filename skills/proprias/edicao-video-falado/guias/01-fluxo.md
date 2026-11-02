# Fluxo de edição, passo a passo

Os comandos assumem `$PIPE` apontando para `ferramentas/` desta skill e o Node 22 no PATH (HyperFrames exige Node ≥ 22).
O python do sistema pode não ter numpy: use `uv run --with numpy python -I script.py`.

## 0. Pasta do episódio

```text
<categoria>/NN - Título/
├── brutos/ (ou iphone/)         .MOV/.mp4 do celular, gravação de tela .mp4 do OBS
├── briefing.md                  (opcional) pauta, fontes, tags, estilo: modelo em modelos/briefing-edicao.modelo.md
├── <projeto>/                   projeto HyperFrames (copiado de modelos/<formato>/)
│   ├── index.html               gerado pelo make.py (não editar à mão)
│   ├── assets/footage|img|music|sfx
│   └── .work/                   scripts e intermediários: build.py, captions.py, make.py, tpl.html, segs/, audio/ ...
└── final/                       só a entrega: 1 .mp4, legendas.srt, palavras.json, publicacao_copy.md, relatorio_cortes.json
```

Crie o projeto copiando o modelo do formato (`modelos/README.md`) e o `ferramentas/build_template.py` para `.work/build.py`.
Para começar um projeto HyperFrames do zero: `npx hyperframes@0.8.185 init` (ver skill `hyperframes-cli`).

## 1. Começo: tudo o que pode rodar junto

| Comando | Para quê | Tempo de referência |
|---|---|---|
| `python3 -I $PIPE/errmap.py BRUTO.MOV` (segundo plano) | quadros corrompidos na cópia do celular | ~1 min a cada 3 min de vídeo |
| `$PIPE/wh file BRUTO.MOV .work/tr_a.json` | transcrição palavra a palavra (GPU se houver) | ~40 s para 4 min numa GPU de 2 GB |
| `$PIPE/sheet.sh BRUTO.MOV .work/sheet_a.jpg 5` | folha de quadros para ver enquadramento, olhar, cortes | ~5 s para 4 min |
| `uv run --with numpy python -I $PIPE/sync.py CEL.MOV TELA.mp4` | sincronia pela palma: `OFF = tTela − tCel` | ~10 s |
| `uv run --with numpy python -I $PIPE/playback.py CEL.MOV TELA.mp4 OFF` | onde o som do sistema toca na gravação de tela | ~5 s |

GPU (whisper) e CPU (errmap, folhas, build) não atrapalham um ao outro: rode juntos.
Leia `03-material-bruto.md` antes: cópia corrompida, HDR, áudio com furos, tela que congela, câmera espelhada.

## 2. Decupagem (montar a EDL)

1. Leia as transcrições inteiras. Marque: tomadas repetidas (fica a melhor, em geral a última inteira), tropeços,
   instruções faladas para a edição, o gancho e o CTA.
2. **Instruções faladas valem como pedido do usuário.** "Corta essa parte", "esquece essa notícia, vou regravar" (só
   entram as tomadas depois disso). O whisper às vezes erra a instrução ("não corta" quando ele disse "corta"): confira com `wh snip`.
3. **Gancho:** frase curta e provocativa repetida em tomadas seguidas (no começo, no fim do arquivo ou num arquivo à
   parte) é a abertura, não o fecho. Entra sem o "E" inicial, com o melhor olhar pra câmera. Outra tomada dela pode
   fechar como pergunta para os comentários. Na dúvida sobre qual frase é o gancho, pergunte.
4. **Notícia:** confira cada frase contra a matéria antes de pôr na EDL (`04-noticias.md`). O que não tem fonte, sai.
5. **Duração:** feche aqui, antes do recorte e da composição (notícia: 60–90 s no total, contando a tela final).
6. Escreva a EDL no `build.py`: `(fonte, a, b, "fala do trecho", "opções")`, tempos no relógio da fonte.
   Opções: `ea`/`eb` borda exata, `nosplit` mantém pausas, `fadeout` no último trecho, `xN` timelapse.
7. Pontos duvidosos, antes de fechar:
   - `$PIPE/wh snip BRUTO.MOV 12.3-15.0 40.1-42.5` janelas curtas com prompt de hesitações (`!` = esticada, `?` = incerta);
   - `uv run --with numpy python -I $PIPE/vad.py BRUTO.MOV 12.3-15.0` perfil de 20 ms (V = vozeado, número = −dB);
   - `$PIPE/wh try BRUTO.MOV 10.0-12.4+13.1-15.0` testa a emenda antes de mexer na EDL;
   - `uv run --with numpy python -I $PIPE/prof5.py BRUTO.MOV 12.30-12.80` perfil de 5 ms com centroide (fronteira de fonema).

## 3. Montagem

```bash
cd <projeto>/.work && uv run --with numpy python -I build.py
```

Saída: `../assets/footage/fala.mp4`, `segs.json` (mapa fonte → saída) e `segs/cat.wav`. A 1ª vez leva alguns minutos
(converte só os quadros usados); depois só os trechos alterados são recodificados (segundos).

## 4. Checagem da fala (obrigatória antes de qualquer render)

```bash
$PIPE/wh edit segs/cat.wav segs.json transcript_edit.json          # procurar !, ? e repetições
uv run --with numpy python -I $PIPE/edgecheck.py a=tr_a.json        # pedaço de palavra vizinha nas bordas
python3 -I $PIPE/audit.py a=../../brutos/A.MOV b=../../brutos/B.MOV > audit.txt   # repetição escondida (janelas de 2,4 s)
```

- Toda borda suspeita se confere **na fonte** (vad/prof5/`wh try`), não na fala montada.
- Zero marca sem explicação no `audit.txt`. Detalhes e critérios em `02-limpeza-da-fala.md`.
- Varra pausas > 0,25 s na fala montada (`cat.wav` abaixo de −38 dB).
- **Revisão visual:** folha de rostos a 5 q/s perto de cada corte. Olhar pra baixo, mão no rosto, se inclinar para sair
  não podem aparecer: corte ou cubra com print grande (`05-layout-e-composicao.md`).

## 5. Legenda

`captions.py` (do modelo): o texto revisado é a fonte da verdade; os tempos vêm do `transcript_edit.json` por alinhamento.
`*palavra` = palavra-chave destacada; `|` = quebra de bloco. Revise nomes próprios, termos técnicos e números.
Se o whisper pular um trecho da fala montada, complete o `transcript_edit.json` com `wh snip`.

## 6. Prints e material de apoio (notícia, demo)

- Notícia: `node capture.mjs jobs.json ../assets/img [id]` tira o print real da matéria com o trecho e os grifos
  (`04-noticias.md`). `probe.mjs`/`para.mjs` acham o texto exato na página antes do print.
- Demo de app: a gravação de tela entra como `tela.mp4` (o `build.py` corta no mesmo ritmo da fala, com `TELA` e `toff`).

## 7. Composição

```bash
uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/chin.py   # formatos sem split: onde termina o rosto
python3 -I make.py                                                                  # tpl.html + dados -> ../index.html
```

O `make.py` imprime o plano (onde entra cada tag/print, quanto a câmera sobe). Fundo de estúdio LED: `06-fundo-estudio-led.md`
(rode o `matte_rvm.py` em segundo plano assim que o `audit.py` fechar a EDL; mexeu na EDL, refaça o recorte). Gravação de
corpo inteiro: depois do `composite`, o `reframe.py` faz o enquadramento de telejornal e o `make.py` usa
`FALA=fala_estudio_zoom.mp4` (mesmo guia, passo 6).

## 8. Trilha e SFX

`./trilha.sh` (trilha ~11 dB abaixo da voz) ou `$PIPE/trilha_ducking.sh` (ducking pela voz). SFX vêm da skill
`media-use` (`audio/assets/sfx/`). Detalhes em `07-audio.md`.

## 9. Conferir sem renderizar

```bash
cd <projeto> && npx hyperframes@0.8.185 check
npx hyperframes@0.8.185 snapshot --at 0.5,8.2,15.0,30.4      # instantes críticos: gancho, cada print, CTA, fim
```

Olhe cada snapshot: legenda legível, nada sobre o rosto, print sem meia linha cortada, grifo no lugar.

## 10. Render (uma vez só) e entrega

```bash
npx hyperframes@0.8.185 render . -o renders/com-legenda.mp4 > .work/render.log 2>&1     # em segundo plano
$PIPE/finalize.sh renders/com-legenda.mp4 ../final/Titulo_DD-MM-AAAA.mp4              # −14 LUFS / −1 dBTP
python3 -I .work/entrega.py                                                          # legendas.srt, palavras.json, relatorio_cortes.json
```

Escreva `final/publicacao_copy.md` (`modelos/giro-noticias/publicacao_copy.modelo.md`). Detalhes em `08-entrega.md`.
