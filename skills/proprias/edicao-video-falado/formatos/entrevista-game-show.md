# Entrevista game show (perguntas e respostas)

Uma pessoa pergunta (atrás da câmera), outra responde. Tom bem-humorado, animado e interativo, com mecânica de game
show. Funciona para collab entre perfis (o visual mistura os estilos dos dois).

## Mecânica

- Contador `PERGUNTA 0X/05` no card de cada pergunta.
- Ficha `PULO ×1` que fica vermelha `×0` quando a pessoa pula uma pergunta; carimbo "PULOU!" + buzina.
- **Pingue-pongue:** duas opções e a escolhida acende (segure ~0,9 s antes do próximo card).
- Contador "pensando… 00:0X" acelerado quando a pessoa demora.
- Gancho: o momento mais engraçado ("ai ai ai… eu vou pular essa") no início.
- Fim com enquete nos comentários ("qual vai ser a prenda? A ou B").

## Visual

- Cards escuros no topo (y ~300) com kicker mono menta + destaque champanhe.
- Legenda branca Montserrat com rótulo de quem fala: quem pergunta em menta, quem responde em champanhe
  (`@j`/`@m` no `captions.py`).
- Figurinhas creme no peito (y ~1160).
- Todo corte troca o enquadramento: quem pergunta = aberto/médio, quem responde = close/médio.

## Áudio

- A voz de quem está atrás da câmera chega 5–10 dB mais alta: nível automático por item da EDL.
- Ruído de loja/rua oscilando em −28/−35 dB: `THR −30,5` e cortes explícitos nas pausas que ficam acima do limiar.
- Trilha leve com ducking (`trilha.sh` do modelo).

## Duração

Prefira cortar perguntas a passar de ~1:50. Confirme com o usuário nomes de produto que o whisper ouvir com hesitação.

Modelo: `modelos/entrevista-game-show/` (`tpl.html`, `make.py`, `captions.py`, `trilha.sh`).
