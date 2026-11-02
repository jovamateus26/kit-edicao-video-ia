# Giro de notícias (padrão atual para notícia)

Resumo de várias notícias do dia num vídeo de 60 a 90 s (ideal ~85 s), com o apresentador em tela cheia num estúdio
escuro de LED e a prova de cada notícia (print real da matéria com grifo) flutuando entre o queixo e a legenda.

## Estrutura

| Bloco | O que entra |
|---|---|
| Gancho (0–3 s) | frase mais provocativa (tomada repetida = gancho) ou a 1ª frase da 1ª notícia; sub-bass + whoosh no 0:00 |
| Cada notícia | tag de abertura `[ TÍTULO CURTO ]` + sub-lettering + número `1/5`; prints reais com grifo sincronizado; clima de cor próprio no estúdio |
| Fecho | pergunta para os comentários (tag CTA) |
| Tela final (2,2 s) | escurece; tag da pergunta, "FONTES: …" e chip "Segue @perfil pra não perder" |

Sem gancho gravado à parte e sem CTA: abra com a 1ª frase e feche com a notícia que termina em pergunta (ela puxa os
comentários). Ordem das notícias: a mais forte no começo, a que termina em pergunta no fim.

## Visual

- **Sem split.** Pessoa sempre em tela cheia; tags e prints no espaço livre sobre o tronco; print que não cabe vai para
  tela cheia (cover) com o estúdio desfocado atrás. A câmera sobe até 340 px por notícia para abrir espaço.
- Fundo de estúdio LED com cor por notícia (`../guias/06-fundo-estudio-led.md`).
- Legenda: Montserrat 800, caixa alta, branca com contorno preto, palavra-chave amarela `#FFE500`, 2–3 palavras por bloco,
  faixa fixa em y 1428.
- Tags: fundo amarelo `#FFE500`, texto `#0B0D10` 900, ícone SVG (sem emoji), sub-lettering em caixa escura com borda na
  cor da notícia, entrada "slam" + slide.
- Prints: cartão branco com faixa superior escura (chip do assunto, ícone, `domínio`, data em amarelo), borda e brilho na
  cor da notícia, marca-texto amarelo em multiply varrendo o trecho no instante falado, zoom lento 1.0 → 1.035.
- `@` fixo pequeno, ~70% de opacidade, com fundo escuro, até o CTA.
- Micro-zoom alternado nos cortes (1.0/1.035) para esconder o jump cut.
- Gravado de corpo inteiro, longe da câmera: **enquadramento de telejornal** com o `reframe.py`. O plano médio fechado
  alterna A/B a cada corte, e o corpo inteiro fica só na abertura das notícias 2 em diante e no fim. Nesse caso, sem
  micro-zoom e sem a câmera subir (`ZALT = 1.0`, `DMAX = 0`). Ver `../guias/06-fundo-estudio-led.md`, passo 6.

## Áudio

Trilha instrumental ~11 dB abaixo da voz (`trilha.sh`), sub-bass no 0:00, whoosh por tag, whoosh curto por print, clique
suave no instante de cada grifo, pop no chip de seguir. Final −14 LUFS.

## Arquivos do modelo (`modelos/giro-noticias/.work/`)

| Arquivo | Papel |
|---|---|
| `build.py` | copie de `ferramentas/build_template.py` e preencha SRC/EDL |
| `captions.py` | texto revisado (`*` destaque, `|` quebra) + tempos do `transcript_edit.json` → `data.json`, `palavras.json` |
| `jobs.exemplo.json` → `jobs.json` | os prints de cada matéria (`capture.mjs`) |
| `capture.mjs`, `probe.mjs`, `para.mjs`, `juntar_prints.py` | prints reais e `prints.json` |
| `estudio.json` | clima de cor por notícia |
| `make.py` + `tpl.html` | monta o `../index.html`: blocos, tags, prints, câmera, legenda, SFX (seções "POR EPISÓDIO") |
| `trilha.sh` | trilha cortada e nivelada |
| `entrega.py` | `legendas.srt`, `palavras.json`, `relatorio_cortes.json` em `final/` |

No `make.py`, os blocos se acham pelas palavras faladas (`at("palavra")`, `seg_of(...)`): mexeu na EDL, rode
`build.py` → `wh edit` → `captions.py` → `make.py` e tudo continua sincronizado.

## Briefing

Se o criador manda um briefing (pauta com fontes, tags, safe areas, copy), siga-o: modelo em
`modelos/briefing-edicao.modelo.md`. As regras de credibilidade (`../guias/04-noticias.md`) valem acima do briefing:
tag que exagera o fato é ajustada ao que a fonte diz.
