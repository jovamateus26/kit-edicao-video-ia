# Material bruto: problemas que já apareceram

Confira estes pontos antes de decupar. Todos já custaram um vídeo devolvido ou horas de retrabalho.

## Cópia do iPhone pelo cabo USB corrompe o arquivo

- Sintoma: quadros borrados com blocos coloridos e furos no áudio, em instantes soltos do vídeo postado.
- Causa: bytes estragados na cópia pelo gerenciador de arquivos (gvfs/AFC) com o iPhone no cabo. Não é codec faltando:
  o ffmpeg decodifica HEVC do iPhone normalmente.
- O dano vai até o próximo quadro-chave (~1 s no iPhone).
- O que fazer: `errmap.py` em todo `.MOV` antes de editar. Não use os trechos com erro (ou cubra com print/congele um
  quadro bom). Recomende transferir por outro meio (AirDrop/LocalSend em qualidade original, download do Google Fotos) e
  conferir a cópia. Arquivos baixados do Google Fotos em `.zip` vieram limpos.

## HDR do iPhone (HLG/PQ)

- Detecção: `ffprobe -v error -select_streams v:0 -show_entries stream=color_transfer -of default=nw=1:nk=1 ARQ`.
  Use `-of default=nw=1:nk=1`: com `csv=p=0` sai `arib-std-b67,` (com vírgula), a comparação falha e a imagem sai lavada.
- Tonemap usado (zscale + hable): `zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`.
- Nunca converta o arquivo inteiro: o `build.py` lê o original e converte só os quadros usados. Para olhar, `sheet.sh`.
- Uma LUT 3D no lugar do tonemap foi testada e errou a cor (PSNR 32 dB) para ganhar só 20%: descartada.

## Áudio do iPhone com furos

Extraia sempre com `aresample=async=1:first_pts=0` (o `build.py` e as ferramentas já fazem). Sem isso, um furo de 0,5 s
dessincroniza tudo o que vem depois.

## Gravação de tela (OBS) junto com o celular

- Sincronize pela palma (`sync.py`): bata uma palma no começo das duas gravações. Ele mede o drift ao longo do arquivo.
- A gravação de tela do Linux pode **congelar o vídeo** e continuar o áudio. Confira com `freezedetect` antes de planejar.
- O áudio da gravação de tela traz o som do sistema limpo (ex.: voz gerada pelo app): `playback.py` acha onde ele toca.
  Esse áudio pode virar uma fonte própria no `build.py`.

## Câmera e enquadramento

- **Câmera frontal espelhada** (texto/logo ao contrário): `hflip` no build.
- **Vídeo de app de teleprompter / Blackmagic Cam:** pode vir SDR bt709, girado 90°, com taxa variável (VFR). O build
  normaliza para 30 fps.
- **720×1280 full range (yuvj):** escale com lanczos para 1080 e um `eq`/`unsharp` leve.
- **Enquadramento varia entre dias e entre arquivos** (até ~100 px): meça em cada fonte (snapshot ou `chin.py`) em vez de
  reaproveitar números de outro episódio. Em projetos com split, o deslocamento vira um dict por fonte.

## Microfone e níveis

- Pessoa atrás da câmera (entrevistador) chega 5–10 dB mais alta que quem está na frente: nível automático por item da EDL
  (`gain` por fonte ou ganho por item).
- Ruído de sala alto (loja, rua): suba o `THR` e, se precisar, `afftdn` leve.

## Material de terceiros

- "Prints" gerados por IA (artes com texto inventado, rodapé de agência) **nunca** são prova. Print de notícia é sempre o
  print real da matéria (`capture.mjs`).
- Pautas e roteiros gerados por IA erram fatos, números e datas, e trazem notícia velha como se fosse de hoje. Confira tudo
  na matéria original (`04-noticias.md`).
- Quem aparece no quadro: confirme antes de chamar alguém de "terceiro" (pode ser o próprio criador com a câmera no tripé).
