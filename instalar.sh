#!/usr/bin/env bash
# Instala as skills do kit (link simbólico por padrão), baixa as do HyperFrames do repositório original e confere as
# dependências. Linux, macOS e WSL. No Windows, use o instalar.cmd (ou o instalar.ps1).
#
#   ./instalar.sh                      skills em ~/.claude/skills (Claude Code) + conferência
#   ./instalar.sh --destino ~/.agents/skills --destino ~/.gemini/skills    outras pastas de skills (repetível)
#   ./instalar.sh --copiar             copia em vez de criar link (para mover o kit depois)
#   ./instalar.sh --forcar             substitui links que já existam (nunca apaga pasta de verdade)
#   ./instalar.sh --so-proprias        só as skills nossas (sem baixar as do HyperFrames)
#   ./instalar.sh --verificar          só confere as dependências
set -euo pipefail

KIT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESTS=() COPIAR=0 FORCAR=0 PROPRIAS=0 VERIFICAR=0
while [ $# -gt 0 ]; do
  case "$1" in
    --destino) DESTS+=("$2"); shift 2 ;;
    --copiar) COPIAR=1; shift ;;
    --forcar) FORCAR=1; shift ;;
    --so-proprias) PROPRIAS=1; shift ;;
    --verificar) VERIFICAR=1; shift ;;
    -h|--help) sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "opção desconhecida: $1" >&2; exit 1 ;;
  esac
done
[ ${#DESTS[@]} -eq 0 ] && DESTS=("$HOME/.claude/skills")

# HyperFrames (HeyGen, Apache-2.0): não vem no kit, é baixado do GitHub na versão do CLI que os modelos usam.
# A lista mora em skills/hyperframes.lista (a mesma para o instalar.ps1).
HF_REPO="https://github.com/heygen-com/hyperframes.git"
HF_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/kit-edicao-video-ia/hyperframes"

ok() { printf '  \033[32mok\033[0m   %s\n' "$*"; }
falta() { printf '  \033[31mfalta\033[0m %s\n' "$*"; }
aviso() { printf '  \033[33maviso\033[0m %s\n' "$*"; }

verificar() {
  echo "Dependências:"
  if command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null; then
    if ffmpeg -hide_banner -filters 2>/dev/null | grep -q " zscale "; then ok "ffmpeg/ffprobe com zscale"
    else aviso "ffmpeg sem o filtro zscale: o tonemap do HDR do iPhone não funciona (use um ffmpeg estático, ex.: johnvansickle.com)"; fi
  else falta "ffmpeg e ffprobe"; fi
  command -v python3 >/dev/null && ok "python3 $(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:2])))')" || falta "python3"
  command -v uv >/dev/null && ok "uv" || falta "uv (https://docs.astral.sh/uv/): roda os scripts com numpy/opencv/onnxruntime sem sujar o sistema"
  if command -v node >/dev/null; then
    v=$(node -p 'process.versions.node.split(".")[0]')
    [ "$v" -ge 22 ] && ok "node $(node -v)" || falta "node >= 22 para o HyperFrames (agora: $(node -v); com nvm: nvm install 22)"
  else falta "node >= 22 (HyperFrames)"; fi
  command -v git >/dev/null && ok "git" || falta "git (baixa as skills do HyperFrames)"
  chrome=""
  for c in "${CHROME:-}" /usr/bin/google-chrome /usr/bin/google-chrome-stable /usr/bin/chromium /usr/bin/chromium-browser \
           "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"; do
    [ -n "$c" ] && [ -x "$c" ] && { chrome="$c"; break; }
  done
  [ -n "$chrome" ] && ok "Chrome para os prints: $chrome" \
                   || aviso "Chrome/Chromium não achado: os prints de notícia (capture.mjs) precisam dele (ou exporte CHROME=caminho)"
  if command -v nvidia-smi >/dev/null && nvidia-smi -L >/dev/null 2>&1; then ok "GPU NVIDIA: $(nvidia-smi -L | head -1)"
  else aviso "sem GPU NVIDIA: o whisper roda no CPU (mais devagar) e o RVM/composição usam as versões CPU"; fi
}

# liga (ou copia) a pasta de uma skill em cada destino
ligar() {
  local s="${1%/}" name dest t
  name="$(basename "$s")"
  for dest in "${DESTS[@]}"; do
    t="$dest/$name"
    if [ -L "$t" ]; then
      if [ "$FORCAR" -eq 1 ]; then rm "$t"; else aviso "$name já existe (link) em $dest: mantido; use --forcar para trocar"; continue; fi
    elif [ -e "$t" ]; then
      aviso "$name já existe como pasta em $dest: mantida (apague ou renomeie você mesmo se quiser a versão do kit)"; continue
    fi
    if [ "$COPIAR" -eq 1 ]; then cp -r "$s" "$t"; else ln -s "$s" "$t"; fi
    ok "$name → $dest"
  done
}

# baixa só uma pasta de um commit/tag do HyperFrames (clone raso e esparso, ~10 MB, com o LICENSE) e imprime onde ficou
baixar_hf() {
  local ref="$1" pasta="$2" d="$HF_CACHE/${1:0:12}-${2//\//-}"
  if [ ! -f "$d/.completo" ]; then
    rm -rf "$d" && mkdir -p "$d"
    { git -C "$d" init -q &&
      git -C "$d" remote add origin "$HF_REPO" &&
      git -C "$d" sparse-checkout set "$pasta" &&
      git -C "$d" fetch -q --depth 1 --filter=blob:none origin "$ref" &&
      git -C "$d" -c advice.detachedHead=false checkout -q FETCH_HEAD; } >&2 </dev/null || { rm -rf "$d"; return 1; }
    touch "$d/.completo"
  fi
  echo "$d"
}

instalar_hf() {
  echo "HyperFrames (baixado do repositório original, licença Apache-2.0):"
  command -v git >/dev/null || { aviso "sem git: pulei as skills do HyperFrames (instale o git e rode de novo)"; return; }
  local ref pasta skills d s
  while read -r ref pasta skills <&3; do
    case "$ref" in ''|'#'*) continue ;; esac
    if ! d="$(baixar_hf "$ref" "$pasta")"; then
      aviso "não consegui baixar $pasta de $HF_REPO em $ref (sem internet?): rode de novo depois"; continue
    fi
    for s in $skills; do
      if [ -d "$d/$pasta/$s" ]; then ligar "$d/$pasta/$s"; else aviso "$s não está em $pasta no $ref"; fi
    done
  done 3< "$KIT/skills/hyperframes.lista"
}

instalar() {
  for dest in "${DESTS[@]}"; do mkdir -p "$dest"; done
  echo "Skills do kit:"
  for s in "$KIT"/skills/proprias/*/; do ligar "$s"; done
  [ "$PROPRIAS" -eq 0 ] && instalar_hf
  chmod +x "$KIT"/skills/proprias/edicao-video-falado/ferramentas/{wh,sheet.sh,finalize.sh,trilha_ducking.sh} \
           "$KIT"/skills/proprias/edicao-video-falado/modelos/giro-noticias/.work/trilha.sh 2>/dev/null || true
}

[ "$VERIFICAR" -eq 0 ] && instalar
verificar
echo
echo "Ferramentas do fluxo (use nos comandos como \$PIPE):"
echo "  export PIPE=\"$KIT/skills/proprias/edicao-video-falado/ferramentas\""
[ -f "$KIT/perfil.md" ] || echo "Próximo passo: cp \"$KIT/perfil.exemplo.md\" \"$KIT/perfil.md\" e preencha (ou peça para a IA preencher com você)."
