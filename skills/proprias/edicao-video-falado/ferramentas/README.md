# Ferramentas (kit de scripts)

Use estas, não copie scripts de episódios antigos. Nos exemplos, `$PIPE` é o caminho absoluto desta pasta.
Quase tudo roda na pasta `.work` do projeto. Requisitos: `ffmpeg`/`ffprobe` com `zscale` (libzimg), `uv`, Python 3.10+;
GPU NVIDIA é opcional (whisper, RVM e composição ficam mais rápidos).

| Ferramenta | Para quê | Comando | Tempo de referência |
|---|---|---|---|
| `errmap.py` | quadros corrompidos na cópia do celular (o dano vai até o próximo quadro-chave) | `python3 -I $PIPE/errmap.py ARQ.MOV` | ~1 min a cada 3 min; segundo plano |
| `sheet.sh` | folha de quadros para olhar o material (só quadros-chave, tonemap em baixa resolução) | `$PIPE/sheet.sh VIDEO saida.jpg [s] [larg] [col]` | ~5 s para 4 min |
| `sync.py` | palma + correlação + drift: `OFF = tB − tA` | `uv run --with numpy python -I $PIPE/sync.py A B` | ~10 s |
| `playback.py` | onde toca o som do sistema na gravação de tela | `uv run --with numpy python -I $PIPE/playback.py MIC TELA OFF` | ~5 s |
| `wh file` | transcrição palavra a palavra | `$PIPE/wh file ARQ [saida.json] [--prompt P]` | ~40 s para 4 min (GPU 2 GB) |
| `wh snip` | janelas curtas com prompt de hesitações (`!` esticada, `?` incerta) | `$PIPE/wh snip ARQ a-b ...` | 2–10 s |
| `wh try` | testa uma emenda antes de mexer na EDL | `$PIPE/wh try ARQ a-b+c-d ...` | ~2 s por variante |
| `wh edit` | transcrição da fala montada + tempo na fonte de cada palavra | `$PIPE/wh edit segs/cat.wav segs.json saida.json` | ~20 s para 80 s |
| `wh status` / `wh stop` | estado do servidor / desligar | | |
| `vad.py` | perfil de 20 ms (V = vozeado, número = −dB): ponto de corte, vogal esticada, respiração | `uv run --with numpy python -I $PIPE/vad.py AUDIO a-b ...` | instantâneo |
| `prof5.py` | perfil de 5 ms com centroide (Hz): fronteira exata entre fonemas | `uv run --with numpy python -I $PIPE/prof5.py AUDIO a-b` | instantâneo |
| `build_template.py` | montagem da fala: copie para `.work/build.py` e preencha o CONFIG | `uv run --with numpy python -I build.py` | 1ª vez ~3 min; depois 6–11 s |
| `edgecheck.py` | varre as emendas atrás de pedaço de palavra vizinha | `uv run --with numpy python -I $PIPE/edgecheck.py [a=tr.json] [-v]` | ~5 s |
| `audit.py` | retranscreve cada trecho em janelas de 2,4 s: REPETE / ESTICADA / FILLER | `python3 -I $PIPE/audit.py a=FONTE.MOV ... > audit.txt` | ~1 min para 80 s |
| `chin.py` | onde termina o rosto em cada quadro → `chin.json` (ou outro nome: `chin.py saida.json`) | `uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/chin.py` | ~1 min para 85 s |
| `matte_rvm.py` | recorte da pessoa (RVM) → `matte/pha.mkv` + `matte/fgr.mp4` | `uv run --with numpy --with onnxruntime python -I $PIPE/matte_rvm.py` | ~12 min para 80 s (CPU) |
| `matte_rvm_gpu.py` | o mesmo na GPU NVIDIA; `--comparar A B` confere dois recortes | `$VENV_TORCH/bin/python -I $PIPE/matte_rvm_gpu.py` | ~33 q/s numa L4 |
| `studio.py` | o estúdio escuro com LED animado; sozinho gera fundos de teste | `uv run --with numpy --with opencv-python-headless python -I $PIPE/studio.py t1,t2` | ~4 s |
| `composite.py` | pessoa com luz de estúdio sobre o `studio.py` → `fala_estudio.mp4`; com tempos, só quadros de teste | `uv run --with numpy --with opencv-python-headless python -I $PIPE/composite.py [t1,t2]` | ~10 min para 80 s (CPU livre) |
| `composite_gpu.py` | o mesmo na GPU (PyTorch); com tempos, compara com a versão CPU | `$VENV_TORCH/bin/python -I $PIPE/composite_gpu.py [t1,t2]` | ~21 q/s numa L4 |
| `reframe.py` | enquadramento de telejornal: plano médio A/B nos cortes, zoom até 2× que segue o rosto, corpo inteiro só nos trechos de `"planos"` do `estudio.json` → `fala_estudio_zoom.mp4` + `chin.json` no quadro novo; com tempos, só quadros de teste em `qc/` | `uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/reframe.py [t1,t2]` | ~5,5 min para 67 s (CPU de 4 núcleos); teste ~1 s por quadro |
| `finalize.sh` | −14 LUFS / −1 dBTP (loudnorm em 2 passes, vídeo copiado) | `$PIPE/finalize.sh entrada.mp4 saida.mp4` | ~15 s |
| `musicgen.py` | trilha instrumental local (MusicGen small, CPU) | ver `../guias/07-audio.md` | ~1–3 min por clipe |
| `trilha_ducking.sh` | trilha esticada + ducking pela voz (modelo da loja/moda) | copie para a `.work` e ajuste | segundos |

## `wh` (whisper com o modelo carregado uma vez)

- O `wh` cria sozinho o ambiente em `~/.cache/whisperd/venv` no primeiro uso (`faster-whisper` + libs CUDA do pip) e sobe o
  `whisperd.py` num socket Unix (no Windows, TCP em `127.0.0.1:47615`). Ele mantém o modelo `medium` na GPU e sai
  depois de 20 min parado. No PowerShell/cmd do Windows use o `wh.cmd`; no Git Bash, o próprio `wh`.
- Sem GPU NVIDIA, cai para o CPU (int8). Falta de memória na placa: refaz o pedido no CPU e reinicia limpo.
- Variáveis: `WHISPERD_MODEL`, `WHISPERD_SOCK` (ex.: túnel para outra máquina), `WHISPERD_PORT` (usa TCP local em
  qualquer sistema), `WHISPERD_IDLE_MIN`.
- O idioma está fixo em português (`language="pt"` no `whisperd.py`) e o prompt de hesitações (`FILLERS` no `wh.py`) é
  em pt-BR. Para outro idioma, troque os dois.

## Arquivos que o `build.py` gera e os outros leem

| Arquivo | Quem gera | Quem lê |
|---|---|---|
| `audio/<fonte>48.wav` | build | edgecheck, vad (fonte) |
| `segs.json` | build | wh edit, edgecheck, audit, matte, composite, captions, make, entrega |
| `segs/cat.wav` | build | wh edit |
| `../assets/footage/fala.mp4` | build | chin, matte, make |
| `chin.json` | chin (com reframe: o reframe, no quadro novo) | make |
| `chin_raw.json` | chin, chamado pelo reframe (quadro original) | reframe |
| `matte/pha.mkv`, `matte/fgr.mp4` | matte_rvm | composite |
| `../assets/footage/fala_estudio.mp4` | composite | make (`FALA=`), reframe |
| `../assets/footage/fala_estudio_zoom.mp4` | reframe | make (`FALA=`) |
