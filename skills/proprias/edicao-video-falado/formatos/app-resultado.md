# App + resultado (demo de ferramenta)

"Mostrar o app e o resultado": simples, dinâmico e estruturado, sem muita animação. Para vídeos de demonstração de app,
script ou ferramenta, gravados com o celular (pessoa falando) e o OBS (tela) ao mesmo tempo.

## Material e montagem

- Celular + gravação de tela sincronizados pela palma (`sync.py`). O som do sistema na gravação de tela (ex.: voz gerada
  pelo app) vira uma fonte própria no `build.py` (`playback.py` acha os trechos).
- O `build.py` gera também `tela.mp4` cortada no mesmo ritmo da fala; trechos de tela podem ser acelerados quando a fala
  foi reordenada (`tela_a`/`tela_b` na EDL).
- A gravação de tela entra como `<video>` dentro de uma janela de painel, com recorte (x, y, largura) por cena.

## Visual

- Kicker mono + janela "localhost:3000" (ou o app) em cima, rosto embaixo (câmera deslocada ~+450 px).
- Tela cheia com punch-in nos momentos de fala.
- Cards de comparação (antes → depois), chip da regra, checklist de andamento.
- Chip de CTA de comentário ("sugere um nome") e "Segue @perfil" no fim.
- Estilo Terminal Noir.

## Cuidados

- Pedaços curtos antes de frases costumam ser palavras repetidas ("WhatsApp… WhatsApp", "essas, essas") que o whisper
  engole: confira cada emenda duvidosa transcrevendo a variante isolada (`wh try`).
- A pessoa fala instruções de edição na gravação ("corta essa parte"): procure e obedeça.

Modelo: `modelos/app-resultado/` (`tpl.html`, `make.py`, `captions.py`).
