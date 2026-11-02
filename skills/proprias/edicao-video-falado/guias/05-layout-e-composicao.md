# Layout e composição (1080×1920, 30 fps)

## Áreas da tela

| Área | Uso |
|---|---|
| Topo, y 0–220 | livre de texto (barra do app). Selo/kicker pequeno pode ficar a partir de ~y 120 só se não houver nada do app ali |
| Lateral direita, x 960–1080 | livre (botões de curtir, comentar, compartilhar): overlays com `left 60`, largura até 900 |
| Rodapé, y 1580–1920 | livre de texto crítico (legenda do feed, perfil, música) |
| Legenda | faixa fixa logo acima do rodapé (giro: topo em y 1428, 110 px de altura); área nobre entre y 1250 e 1450 |
| @ fixo | pequeno, ~70% de opacidade, **com fundo escuro** (sem fundo o `check` reprova o contraste), abaixo da legenda |

## Padrão atual: sem tela dividida

Desde que o criador pediu "não quero que fique cortando mais a tela", o giro usa só dois modos:

1. **Pessoa em tela cheia** no estúdio, com tag/print flutuando no espaço livre sobre o tronco, entre o queixo e a
   legenda. Nada encosta no rosto nem na faixa da legenda.
2. **Print em tela cheia (cover)**, com o estúdio desfocado e escurecido atrás. Usado quando o print não cabe abaixo do
   queixo ou quando o rosto não pode aparecer.

Implementação (`modelos/giro-noticias/.work/make.py`):
- `chin.py` mede o queixo a 5 q/s (detector de rosto do OpenCV + 12% de margem para barba); o `make.py` usa a mediana de 1 s
  e o pior caso de cada intervalo.
- Plano médio fechado deixa pouco espaço (queixo em y 1000–1450). Por notícia, a câmera **sobe até 340 px** (`DMAX`) para
  abrir espaço, sem o alto da cabeça passar de y 120 (`TOPMIN`); um **piso escuro** acompanha e esconde a borda de baixo do vídeo.
- Print que não couber (< 230 px livres) vai para cover automaticamente. O `make.py` imprime o plano: topo e altura de cada
  print e quanto a câmera sobe. Confira em snapshot que nada encosta no queixo em nenhum quadro (a pessoa se aproxima da câmera).
- Micro-zoom alternado (1.0 ↔ 1.035) a cada corte esconde o jump cut; na troca de notícia a câmera sobe em 0,45 s.
- Gravação de corpo inteiro, longe da câmera: o `reframe.py` faz plano médio A/B nos cortes (até 2×, seguindo o rosto) e deixa
  corpo inteiro só nas cenas-chave. Aí o `make.py` fica com `ZALT = 1.0` e `DMAX = 0` (`06-fundo-estudio-led.md`, passo 6).
- Print entra subindo com perspectiva leve (0,4 s), cresce devagar (1.0 → 1.035) e rola (pan) se for mais alto que o espaço.

Formatos com split (app + resultado, loop + split, notícia com prova antiga) estão em `formatos/`: só use quando o perfil ou
o pedido escolher esse formato.

## Rosto: olhar pra baixo, mão no rosto, saída

Quem grava lendo a pauta no celular olha pra baixo, inclina a cabeça, se aproxima da câmera e põe a mão no rosto,
justamente perto das emendas e no fim. O corte por áudio não enxerga isso.

- Depois do build, revise a fala montada quadro a quadro perto de cada corte (folha de rostos ampliados a 5 q/s; medidas
  automáticas de pose ficaram ruidosas).
- Onde a fala não dá para cortar: **print grande** (cover) por cima do trecho inteiro, com fundo escuro, print crescendo
  1,06×, transição de 0,2–0,3 s e whoosh suave; a legenda continua visível.
- Avanço rápido pra lente no meio da frase: print grande cobrindo o trecho.
- No fim: escureça a imagem antes de a pessoa baixar o olhar, ou corte a cauda.
- Piscadas curtas não precisam de nada.

## Tela final

Escura (fade a ~90% no fim da fala), com a tag da pergunta, o chip "Segue @perfil pra não perder" e a linha de FONTES,
por pelo menos 2 s para dar tempo de ler (`HOLD = 2.2`). Formatos em loop não têm tela final (o último quadro emenda no primeiro).

## Legenda karaokê

- Texto revisado à mão é a fonte da verdade; os tempos vêm do whisper por alinhamento (`captions.py`).
- 2–3 palavras por bloco (até ~15–18 caracteres), quebra em pontuação ou pausa > 0,6 s.
- Palavra entra no instante falado; palavra-chave com destaque de cor e um "pop".
- Montserrat 800, caixa alta, branco com contorno/sombra preta; cor de destaque vem do estilo (amarelo `#FFE500` no giro,
  menta `#5EEAD4` no Terminal Noir, champanhe `#EDD3A0` no Clean Luxury).
- Legenda é overlay por cima do vídeo: nunca empurre o conteúdo para "reservar" uma faixa (skill `captions-overlay`).

## Conferência

`npx hyperframes@0.8.185 check` (lint, contraste, mídia) e `snapshot --at` em: gancho, cada tag, cada print (entrada e
meio do pan), cada cover, CTA e último quadro. Olhe as imagens: o `check` não vê rosto coberto.
