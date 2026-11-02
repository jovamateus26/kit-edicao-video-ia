# Windows

O kit nasceu no Linux, mas roda no Windows de dois jeitos. Escolha um.

## Jeito 1: Windows normal (Claude Code + Git Bash)

1. **Dependências:** na pasta do kit, rode `instalar.cmd -Dependencias`. Ele instala pelo `winget` o que faltar:
   - ffmpeg build completo do gyan.dev, que já vem com `zscale` para o HDR do iPhone;
   - uv, Node.js LTS, Python 3.12, Git (traz o Git Bash) e Chrome.

   Feche e abra o terminal depois, para o PATH novo valer.
2. **Skills:** `instalar.cmd`, com dois cliques ou no terminal.
   - Liga as skills em `%USERPROFILE%\.claude\skills` por junção, que não precisa de administrador.
   - Baixa as do HyperFrames.
   - Salva a variável `PIPE` para o seu usuário.
   - Outras pastas de skills: `instalar.cmd -Destino "%USERPROFILE%\.agents\skills;%USERPROFILE%\.gemini\skills"`.
3. **Claude Code:** ele roda os comandos no **Git Bash** (é por isso que pede o Git for Windows). Os comandos dos guias
   funcionam como estão, com as trocas da tabela abaixo. No Codex, Gemini CLI e outras IAs que usam o PowerShell, siga a
   coluna do PowerShell.

| Nos guias (Linux/Mac) | Git Bash (Claude Code) | PowerShell |
|---|---|---|
| `python3 -I script.py` | `python -X utf8 -I script.py` | `python -X utf8 -I script.py` |
| `uv run --with numpy python -I script.py` | `uv run --with numpy python -X utf8 -I script.py` | igual ao Git Bash |
| `$PIPE/wh file ARQ` | `$PIPE/wh file ARQ` | `& "$env:PIPE\wh.cmd" file ARQ` |
| `$PIPE/sheet.sh`, `$PIPE/finalize.sh`, `./trilha.sh` | iguais | rode pelo Git Bash: `& "$env:ProgramFiles\Git\bin\bash.exe" "$env:PIPE/finalize.sh" entrada.mp4 saida.mp4` |
| `$VENV_TORCH/bin/python` | `$VENV_TORCH/Scripts/python.exe` | `& "$env:VENV_TORCH\Scripts\python.exe"` |
| `export CHROME=...` | não precisa: os scripts acham o Chrome ou o Edge sozinhos | não precisa |

### Por que o `-X utf8`

Sem ele, o Python do Windows lê e grava texto em cp1252. Com acento na legenda ou no roteiro, o resultado é:

- palavras como "ÁUDIO" fazem a leitura do arquivo falhar;
- "→" e "✓" quebram a gravação.

O `-I` dos comandos ignora a variável `PYTHONUTF8`, então o `-X utf8` tem que estar no próprio comando. O `wh` e os
scripts `.sh` do kit já passam o `-X utf8` sozinhos.

### GPU NVIDIA

- **Whisper:** o `wh` instala o cuBLAS e o cuDNN pelo pip no primeiro uso, e o `whisperd.py` acha as DLLs sozinho. Basta
  o driver NVIDIA atualizado.
  - No Windows, o servidor escuta em `127.0.0.1:47615` (TCP local, só a própria máquina); troque com `WHISPERD_PORT`.
  - Whisper em outra máquina: `ssh -N -L 47615:127.0.0.1:47615 usuario@host`, com o `whisperd.py` rodando lá com
    `WHISPERD_PORT=47615`.
- **Recorte e composição na GPU:** crie um ambiente com PyTorch CUDA e aponte o `VENV_TORCH` para ele:

  ```bash
  uv venv --python 3.12 "$HOME/venv-torch"
  VIRTUAL_ENV="$HOME/venv-torch" uv pip install torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
  VIRTUAL_ENV="$HOME/venv-torch" uv pip install onnxruntime-gpu==1.22.0 numpy opencv-python-headless
  export VENV_TORCH="$HOME/venv-torch"
  ```

- **Sem GPU NVIDIA:** tudo roda nas versões CPU (`matte_rvm.py`, `composite.py`), só mais devagar.

### Cuidados

- **Brutos fora do OneDrive:** a sincronização trava e deixa lento ler e gravar arquivos grandes. Use uma pasta local,
  ex.: `C:\Videos`.
- **Caminhos longos:** o Windows limita caminhos a 260 caracteres.
  - O instalador guarda o HyperFrames num caminho curto (`%LOCALAPPDATA%\kit-edicao-video-ia\hf`).
  - Mantenha a pasta do kit e a dos vídeos perto da raiz do disco.
- **Firewall:** o servidor do whisper só escuta na própria máquina. Se o Windows perguntar, permita só em rede privada.
- **Fim de linha:** clone o kit com o Git normal. O `.gitattributes` mantém os `.sh` e `.py` com LF, senão o Git Bash
  quebra com `$'\r': command not found`.

## Jeito 2: WSL2 (Ubuntu dentro do Windows)

Tudo roda como no Linux, inclusive a GPU NVIDIA (o driver do Windows já atende o WSL2).

1. `wsl --install -d Ubuntu`, abra o Ubuntu e instale `ffmpeg` (estático, com `zscale`), `uv`, Node 22 (nvm), `git` e
   Chrome ou Chromium.
2. Ponha o kit e os vídeos **dentro do WSL** (ex.: `~/videos`), não em `/mnt/c/...`: ler arquivo do disco do Windows
   pelo WSL é várias vezes mais lento.
3. `./instalar.sh` e o Claude Code (ou outra IA) rodando no próprio Ubuntu.

Para levar os brutos do Windows: `cp /mnt/c/Users/<você>/Videos/*.MOV ~/videos/projetos/...`. No Explorer, a pasta
`\\wsl$\Ubuntu\home\<você>` também aparece.
