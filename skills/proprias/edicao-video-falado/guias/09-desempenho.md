# Desempenho: o que roda onde

Referência medida num notebook comum (CPU de 4 núcleos/8 threads, 16–18 GB, GPU NVIDIA de 2 GB sem NVENC, GPU Intel
integrada). Ajuste para a sua máquina, mas a lógica vale.

| Recurso | Uso |
|---|---|
| GPU NVIDIA (CUDA) | whisper, sempre pelo `wh` (servidor que mantém o modelo carregado). 3–4× mais rápido que o CPU, mesma qualidade |
| GPU integrada | o render do HyperFrames já usa sozinho (Chrome/ANGLE, workers automáticos). Não mexer, não passar `--gpu` |
| CPU | decodificação HEVC, tonemap HDR→SDR e x264 (o ffmpeg estático não tem hwaccel): build, folhas, errmap, render |
| GPU NVIDIA maior (opcional, outra máquina) | whisper por túnel SSH, recorte RVM e composição do estúdio na placa |

Nuvem tipo Colab foi avaliada e **não compensa** para Reels: upload e setup custam mais do que a GPU ganha.

## Regras de eficiência (aprendidas na prática)

- Nunca converter o HDR inteiro para SDR. O build lê o original e converte só os quadros usados. Para olhar, `sheet.sh`.
- Nunca carregar `WhisperModel` em script avulso: cada carga custa tempo e disputa o CPU. Use `wh`.
- Rode GPU (`wh`) junto com CPU (`errmap`, build, folhas): um não atrapalha o outro.
- Para esperar algo em segundo plano, use a notificação do processo, espere pelo arquivo de saída ou `wait PID`.
  **Nunca** `until ! pgrep -f "padrão"`: o próprio comando de espera casa com o padrão e trava até o timeout.
- Intermediários (fala.mp4, tela.mp4) em x264 `veryfast`: o render do HyperFrames recodifica tudo depois.
- O build guarda cache por segmento: mexer na EDL e remontar leva segundos.
- Feche a duração antes do recorte RVM e da composição: mudar a EDL depois obriga a refazer os dois.
- Render completo só uma vez, no fim. Para conferir, `check` + `snapshot`.

## Tempos de referência

| Etapa | CPU/notebook | GPU NVIDIA |
|---|---|---|
| Transcrição de 4 min | ~2 min (CPU) | ~40 s (2 GB) |
| Recorte RVM de 80 s | ~12 min | ~1 min (L4) |
| Composição do estúdio de 80 s | ~10 min (CPU livre) | ~2 min (L4) |
| Build (1ª vez / remontagem) | ~3 min / 6–11 s | — |
| Render de 80 s | ~4,5 min (GPU integrada) | — |

## `wh`: o servidor de transcrição

- Sobe sozinho um `whisperd.py` com o modelo `medium` carregado e o mantém entre as chamadas; sai depois de 20 min parado.
  Se a placa ficar sem memória, refaz o pedido no CPU e reinicia limpo. `wh status` mostra o estado, `wh stop` desliga.
- Ambiente em `~/.cache/whisperd/venv` (faster-whisper + cuBLAS/cuDNN do pip), criado no primeiro uso com o `uv`.
- Variáveis: `WHISPERD_MODEL` (padrão `medium`), `WHISPERD_SOCK`, `WHISPERD_PORT` (TCP local; padrão no Windows,
  porta 47615), `WHISPERD_IDLE_MIN`.
- Sem GPU NVIDIA funciona no CPU (int8), só mais devagar.

## GPU em outra máquina (opcional)

Se você tem acesso SSH a uma máquina com GPU NVIDIA maior:

- **Mesmos caminhos dos dois lados** (um link simbólico na máquina remota para a mesma pasta de vídeos) e `rsync` de
  `audio/<fonte>48.wav` e `segs/cat.wav` antes de chamar: o `wh` local manda o caminho e a máquina remota acha o arquivo.
- Whisper remoto: suba o `whisperd.py` lá com `setsid nohup ... &` num socket (ex.: `/tmp/whisperd-gpu.sock`) e faça o
  túnel de socket: `ssh -N -L /run/user/$UID/whgpu.sock:/tmp/whisperd-gpu.sock usuario@host` em segundo plano, depois
  `WHISPERD_SOCK=/run/user/$UID/whgpu.sock $PIPE/wh ...`. Caminho de socket com mais de 108 caracteres falha.
- Nunca `pgrep -f` com o padrão na mesma linha do `ssh` (casa consigo mesmo).
- RVM e composição: `matte_rvm_gpu.py` e `composite_gpu.py` num venv com `torch==2.6.0+cu124` e `onnxruntime-gpu==1.22.0`
  (`$VENV_TORCH`). Não mexa em serviços de produção que dividam a placa.
