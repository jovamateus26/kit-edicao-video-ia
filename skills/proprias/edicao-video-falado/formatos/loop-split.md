# Loop + split (demo-first em loop perfeito)

Formato de retenção para demo: abre na prova e a última frase emenda na primeira ("Loop Perfeito"), então o vídeo recomeça
sem o espectador perceber.

## Estrutura

- **Abre na prova:** o resultado (ex.: a voz de IA gerada pelo app) nos primeiros segundos.
- **Split dinâmico:** painel em cima (player, IDE, fluxo, simulador) + rosto embaixo deslocado (~+600 px).
- **Tela cheia** com punch-in alternado a cada corte para esconder o jump cut.
- **Sem tela final** (quebraria o loop): o CTA "@perfil" vai no meio, junto de um teaser. O último quadro é igual ao primeiro.

## Cuidados

- Gravação em dupla (celular + tela) sincronizada pela palma.
- A gravação de tela do Linux pode congelar o vídeo (o áudio continua e traz o som do sistema limpo): confira com
  `freezedetect` antes de planejar as cenas.
- A legenda da voz gerada pelo app vira karaokê do player, separada da legenda da fala.

Modelo: `modelos/loop-split/` (`tpl.html`, `make.py`, `captions.py`).
