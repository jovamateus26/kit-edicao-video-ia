# Notícia com prova (uma notícia, curta)

Formato curto de alta retenção para uma notícia só: prints reais para dar credibilidade e o rosto do apresentador para
construir autoridade, sem "super produção". Foi o primeiro formato de notícia aprovado; o [giro](giro-noticias.md) herdou
as regras dele e trocou o split por tela cheia. Use o split só se o perfil pedir.

## Estrutura

- **Gancho:** pilha de manchetes reais caindo uma sobre a outra (3 veículos), o 1º quadro já com a frase marcada.
- **Provas (split):** print real em cima com faixa "domínio · data" e marca-texto menta varrendo a frase no instante
  falado; rosto embaixo, com a câmera deslocada para baixo (+460 a +600 px, conforme o enquadramento de cada gravação).
- **Opinião:** tela cheia com punch-in.
- **Card "quem achou a falha"** (ou personagem da notícia).
- **Fim:** "Fontes:" + CTA no topo.

## Detalhes

- Prints: `puppeteer-core` com viewport de iPhone 430×932 @3x, sem aceitar cookies, anúncios escondidos por seletor
  (use o `capture.mjs` do giro, que é a versão mais nova; o `tops.mjs` do modelo recorta manchetes empilhadas).
- Meça as caixas do marca-texto só depois de `document.fonts.ready`.
- Confira os fatos das falas contra as matérias; quando a fala arredonda, o vídeo mostra o número da fonte ("≈70%").
- Estilo Terminal Noir (`estilos-visuais.md`), legenda menta.

Modelo: `modelos/noticia-com-prova/` (`tpl.html`, `make.py`, `captions.py`, `tops.mjs`).
