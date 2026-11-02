@echo off
rem wh no Windows (PowerShell/cmd): transcricao na GPU NVIDIA (ou no CPU) com o modelo carregado uma vez so.
rem Uso: wh file|snip|try|edit|status|stop ...   (wh --help). No Git Bash, use o wh (sem .cmd).
rem Ambiente fixo em %USERPROFILE%\.cache\whisperd\venv, criado sozinho no primeiro uso.
setlocal
set "D=%~dp0"
if defined XDG_CACHE_HOME (set "V=%XDG_CACHE_HOME%\whisperd\venv") else (set "V=%USERPROFILE%\.cache\whisperd\venv")
set "PY=%V%\Scripts\python.exe"
if exist "%PY%" (
  "%PY%" -I -c "import faster_whisper, nvidia.cublas, nvidia.cudnn" 2>nul && goto :rodar
)
echo [wh] criando ambiente do whisper em %V% - uma vez so... 1>&2
if not exist "%PY%" (
  uv venv -q --python 3.12 "%V%" || exit /b 1
)
set "VIRTUAL_ENV=%V%"
uv pip install -q faster-whisper numpy nvidia-cublas-cu12 "nvidia-cudnn-cu12==9.*" || exit /b 1
:rodar
"%PY%" -X utf8 -I "%D%wh.py" %*
