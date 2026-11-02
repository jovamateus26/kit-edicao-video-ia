# Bancada narrada (mão na massa)

O celular filma a bancada (tela de computador, peça, instalação) com a voz de quem faz narrando, e fecha com uma selfie
(cliffhanger ou conclusão). Não é talking head nem gravação de tela.

## Montagem

- Vários clipes curtos: todas as fontes têm fala, então `REFINE = tuple(SRC)` no `build.py` (refino, aparo e ripple em todas).
- Timelapse: opção `xN` na EDL (vídeo N× mais rápido, áudio em silêncio), ex.: o boot de 20 s em 4 s.
- Cauda do fim em item próprio com `ea eb nosplit fadeout` (o fade é limitado à duração do trecho).
- Fala lenta, com vogal esticada e repetição escondida: rode `wh snip` em todos os trechos antes de fechar a EDL.
- Procure áudio de terceiros ao fundo (música com letra) e deixe fora.

## Visual

- **Selo de etapa** mono no topo (01 HD → 02 BIOS → … → 08 instalando), troca seca no corte.
- Cards no topo: specs da máquina, opção riscada → escolhida, hostname, tela de erro em vermelho com flash.
- Gancho em card embaixo da tela de erro; "PARTE 2 EM BREVE" no selo e "Segue @perfil" no fim.
- Sem trilha, só SFX (glitch no erro, whoosh no timelapse, pop no seguir). Estilo Terminal Noir.

Modelo: `modelos/bancada-narrada/` (`tpl.html`, `make.py`, `captions.py`). O plano de edição em tabela
(`modelos/plano-edicao.modelo.md`) ajuda muito quando há muitos clipes.
