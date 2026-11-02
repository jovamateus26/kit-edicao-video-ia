# Entrega

## Um vídeo só

- Um único render, **com legenda**, no fim, depois de `check` e snapshots. Nada de versão sem legenda: cada render extra
  custa vários minutos (num notebook com GPU integrada, ~4,5 s de render por segundo de vídeo).
- Rode o render em segundo plano e espere pela notificação ou pelo arquivo de saída.
- Depois: `finalize.sh` (−14 LUFS / −1 dBTP). Confira no fim da saída do `finalize.sh` o `I` e o `Peak` medidos.

## Pasta `final/`

| Arquivo | O que é |
|---|---|
| `Titulo_DD-MM-AAAA_com_legenda.mp4` | o vídeo, já normalizado |
| `legendas.srt` | a legenda (para plataformas que aceitam arquivo) |
| `palavras.json` | palavras com tempo (`transcript.json` do HyperFrames) |
| `relatorio_cortes.json` | fonte, duração bruta/final, ordem, layout, o que saiu e por quê, revisão visual, tratamento de áudio, trechos mantidos |
| `publicacao_copy.md` | legenda do post, título do Shorts, comentário fixado, hashtags, fontes com link, conferência fala × fonte |

`entrega.py` (modelo do giro) gera `legendas.srt`, `palavras.json` e `relatorio_cortes.json` a partir de `data.json` e
`segs.json`; o texto do relatório é preenchido por episódio.

## Resumo para o usuário

Ao entregar, diga em poucas linhas: duração final, o que saiu (sem fonte, tomadas repetidas, tropeços), o que a auditoria
achou e como foi resolvido, e qualquer coisa que ficou e merece atenção (ex.: um toque rápido da mão no queixo olhando
pra câmera). Se algo não foi verificado, diga.

## Depois da aprovação

Se o usuário usa um quadro de tarefas/pauta (issue, card), registre ali o que foi feito só quando ele pedir: comentar pode
acionar agentes ou notificar pessoas.
