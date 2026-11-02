# Loja / moda "Clean Luxury"

Para perfis de loja, moda e beleza: imagem clara e fiel às cores das roupas, legenda elegante, ritmo de punch-ins e CTA
de venda no fim.

## Diretrizes

- 9:16 1080×1920; texto e rosto na área central 1080×1350, 250 px livres embaixo e 120 px à direita.
- Cor "Clean Luxury": clara, nítida, fiel às cores das roupas. Nada vintage, escuro ou saturado.
- Gancho em 2,5 s, sem hesitação. Jump cuts limpos.
- Alternar aberto e punch-in 1,25–1,35× a cada 1,5–2,5 s, com a origem do zoom no rosto (1.0 / 1.12 / 1.28).
- Legenda: no máximo 2 linhas, 3–5 palavras por linha, Montserrat Bold branca com sombra suave, destaque champanhe
  `#EDD3A0`; frases-chave em caixa alta como título (`#` no `captions.py`).
- Trilha chic house / pop acústico / lo-fi chic ~20 dB abaixo da voz, com ducking (`ferramentas/trilha_ducking.sh`);
  SFX sutis (whoosh, pop).
- Últimos 3 s: CTA na tela e na fala ("Peça pelo Direct", "Link na bio", "Comente LOOK").
- Tela final clara: último quadro desfocado + véu creme, com o CTA, o @ da loja e "conforme disponibilidade".

## Cuidados técnicos

- Câmera frontal costuma vir **espelhada** (logo ao contrário): `hflip` no build.
- 720×1280 SDR full range (yuvj): `lanczos` para 1080 + `eq`/`unsharp` leves.
- Ruído de sala ~−35 dB: `THR −31` (−37 não acha pausa) + `afftdn` leve.
- Marca diferente do criador principal: use o @, as cores e o CTA **da marca** (perfil próprio).

Modelo: `modelos/moda-clean-luxury/` (`tpl.html`, `make.py`, `captions.py`, `trilha.sh`).
