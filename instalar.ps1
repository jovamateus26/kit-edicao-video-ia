<#
.SYNOPSIS
  Instala o kit no Windows: liga as skills na pasta da IA, baixa as do HyperFrames do repositório original e confere
  as dependências. Rode pelo instalar.cmd (dois cliques ou no terminal), que não mexe na política de execução.

.EXAMPLE
  .\instalar.cmd                                   skills em %USERPROFILE%\.claude\skills (Claude Code) + conferência
  .\instalar.cmd -Dependencias                     instala pelo winget o que faltar (ffmpeg, uv, Node, Python, Git, Chrome)
  .\instalar.cmd -Destino "%USERPROFILE%\.agents\skills;%USERPROFILE%\.gemini\skills"    outras pastas de skills
  .\instalar.cmd -Copiar                           copia em vez de criar junção (para mover o kit depois)
  .\instalar.cmd -Forcar                           substitui junções que já existam (nunca apaga pasta de verdade)
  .\instalar.cmd -SoProprias                       só as skills nossas (sem baixar as do HyperFrames)
  .\instalar.cmd -Verificar                        só confere as dependências
#>
[CmdletBinding()]
param(
  [string[]]$Destino,
  [switch]$Dependencias,
  [switch]$Copiar,
  [switch]$Forcar,
  [switch]$SoProprias,
  [switch]$Verificar
)

$ErrorActionPreference = 'Continue'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$Pipe = Join-Path $Kit 'skills\proprias\edicao-video-falado\ferramentas'
# pelo .cmd as listas chegam como um texto só: aceita "a;b" e "a,b"
$Destinos = @($Destino | ForEach-Object { $_ -split '[;,]' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($Destinos.Count -eq 0) { $Destinos = @(Join-Path $env:USERPROFILE '.claude\skills') }

# HyperFrames (HeyGen, Apache-2.0): não vem no kit, é baixado do GitHub; a lista é a mesma do instalar.sh
$HfRepo = 'https://github.com/heygen-com/hyperframes.git'
$HfCache = Join-Path $env:LOCALAPPDATA 'kit-edicao-video-ia\hf'   # curto: o Windows limita caminhos a 260 caracteres

function Ok($t)    { Write-Host '  ok    ' -ForegroundColor Green -NoNewline; Write-Host $t }
function Falta($t) { Write-Host '  falta ' -ForegroundColor Red -NoNewline; Write-Host $t }
function Aviso($t) { Write-Host '  aviso ' -ForegroundColor Yellow -NoNewline; Write-Host $t }

function Tem($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

function Atualizar-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}

# python de verdade (o "python" da pasta WindowsApps é só um atalho para a Microsoft Store)
function Achar-Python {
  if (Tem 'py') { return 'py' }
  $p = Get-Command python -ErrorAction SilentlyContinue
  if ($p -and $p.Source -notmatch 'WindowsApps') { return 'python' }
  return $null
}

function Achar-Chrome {
  $c = @($env:CHROME,
         "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
         "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
         "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe",
         "$env:ProgramFiles\Chromium\Application\chrome.exe",
         "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
         "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe")
  foreach ($x in $c) { if ($x -and (Test-Path -LiteralPath $x)) { return $x } }
  return $null
}

function Achar-GitBash {
  $c = @("$env:ProgramFiles\Git\bin\bash.exe", "${env:ProgramFiles(x86)}\Git\bin\bash.exe", "$env:LOCALAPPDATA\Programs\Git\bin\bash.exe")
  foreach ($x in $c) { if ($x -and (Test-Path -LiteralPath $x)) { return $x } }
  return $null
}

function Instalar-Dependencias {
  Write-Host 'Dependências pelo winget (o winget pode pedir para você aceitar os termos de cada pacote):'
  if (-not (Tem 'winget')) { Falta 'winget (App Installer da Microsoft Store): instale as dependências à mão, veja o README'; return }
  $pacotes = @(
    @{ cmd = 'ffmpeg'; id = 'Gyan.FFmpeg';        nome = 'ffmpeg (build completo, com zscale)' },
    @{ cmd = 'uv';     id = 'astral-sh.uv';       nome = 'uv' },
    @{ cmd = 'node';   id = 'OpenJS.NodeJS.LTS';  nome = 'Node.js LTS' },
    @{ cmd = 'git';    id = 'Git.Git';            nome = 'Git (traz o Git Bash)' }
  )
  foreach ($p in $pacotes) {
    if (Tem $p.cmd) { Ok "$($p.nome) já instalado"; continue }
    winget install --id $p.id -e --source winget
    if ($LASTEXITCODE -eq 0) { Ok $p.nome } else { Falta "$($p.nome): o winget falhou (código $LASTEXITCODE)" }
    Atualizar-Path
  }
  if (-not (Achar-Python)) {
    winget install --id Python.Python.3.12 -e --source winget
    if ($LASTEXITCODE -eq 0) { Ok 'Python 3.12' } else { Falta "Python: o winget falhou (código $LASTEXITCODE)" }
    Atualizar-Path
  } else { Ok 'Python já instalado' }
  if (-not (Achar-Chrome)) {
    winget install --id Google.Chrome -e --source winget
    if ($LASTEXITCODE -eq 0) { Ok 'Google Chrome' } else { Aviso 'Chrome: o winget falhou; o Edge também serve para os prints' }
  } else { Ok 'Chrome/Edge já instalado' }
  Write-Host ''
}

function Verificar-Dependencias {
  Write-Host 'Dependências:'
  if ((Tem 'ffmpeg') -and (Tem 'ffprobe')) {
    $f = (& ffmpeg -hide_banner -filters 2>$null) -join "`n"
    if ($f -match ' zscale ') { Ok 'ffmpeg/ffprobe com zscale' }
    else { Aviso 'ffmpeg sem o filtro zscale: o tonemap do HDR do iPhone não funciona (use o build completo do gyan.dev: winget install Gyan.FFmpeg)' }
  } else { Falta 'ffmpeg e ffprobe (winget install Gyan.FFmpeg, ou rode com -Dependencias)' }
  $py = Achar-Python
  if ($py) { Ok ("python " + ((& $py -c "import sys;print('.'.join(map(str,sys.version_info[:2])))") -join '')) }
  else { Falta 'Python 3.10+ (winget install Python.Python.3.12); o "python" da Microsoft Store não serve' }
  if (Tem 'uv') { Ok 'uv' } else { Falta 'uv (winget install astral-sh.uv): roda os scripts com numpy/opencv/onnxruntime sem sujar o sistema' }
  if (Tem 'node') {
    $v = [int]((& node -p "process.versions.node.split('.')[0]") -join '')
    if ($v -ge 22) { Ok "node $(& node -v)" } else { Falta "node >= 22 para o HyperFrames (agora: $(& node -v); winget install OpenJS.NodeJS.LTS)" }
  } else { Falta 'node >= 22 para o HyperFrames (winget install OpenJS.NodeJS.LTS)' }
  if (Tem 'git') { Ok 'git' } else { Falta 'git (winget install Git.Git): baixa as skills do HyperFrames e traz o Git Bash' }
  $gb = Achar-GitBash
  if ($gb) { Ok "Git Bash: $gb (o Claude Code usa ele; as ferramentas .sh do kit rodam nele)" }
  else { Aviso 'Git Bash não achado: o Claude Code no Windows precisa dele e as ferramentas .sh do kit rodam nele' }
  $ch = Achar-Chrome
  if ($ch) { Ok "navegador para os prints: $ch" } else { Aviso 'Chrome/Edge não achado: os prints de notícia (capture.mjs) precisam de um (defina CHROME=caminho)' }
  if ((Tem 'nvidia-smi') -and ((& nvidia-smi -L 2>$null) -join '')) { Ok ("GPU NVIDIA: " + ((& nvidia-smi -L) | Select-Object -First 1)) }
  else { Aviso 'sem GPU NVIDIA: o whisper roda no CPU (mais devagar) e o RVM/composição usam as versões CPU' }
}

function E-Link($p) {
  $i = Get-Item -LiteralPath $p -Force -ErrorAction SilentlyContinue
  return ($i -and ($i.Attributes -band [IO.FileAttributes]::ReparsePoint))
}

# liga (junção, não precisa de administrador) ou copia a pasta de uma skill em cada destino
function Ligar($src) {
  $nome = Split-Path -Leaf $src
  foreach ($dest in $Destinos) {
    $t = Join-Path $dest $nome
    if (E-Link $t) {
      # Directory.Delete sem recursão tira só a junção, nunca o conteúdo da pasta de origem
      if ($Forcar) { [IO.Directory]::Delete($t) } else { Aviso "$nome já existe (junção) em ${dest}: mantida; use -Forcar para trocar"; continue }
    } elseif (Test-Path -LiteralPath $t) {
      Aviso "$nome já existe como pasta em ${dest}: mantida (apague ou renomeie você mesmo se quiser a versão do kit)"; continue
    }
    if ($Copiar) { Copy-Item -LiteralPath $src -Destination $t -Recurse }
    else { New-Item -ItemType Junction -Path $t -Target $src | Out-Null }
    if (Test-Path -LiteralPath $t) { Ok "$nome -> $dest" } else { Falta "${nome}: não consegui criar em $dest" }
  }
}

# baixa só uma pasta de um commit/tag do HyperFrames (clone raso e esparso, ~10 MB, com o LICENSE)
function Baixar-Hf($ref, $pasta) {
  $d = Join-Path $HfCache ($ref.Substring(0, [Math]::Min(12, $ref.Length)) + '-' + ($pasta -replace '[\\/]', '-'))
  if (Test-Path -LiteralPath (Join-Path $d '.completo')) { return $d }
  if (Test-Path -LiteralPath $d) { Remove-Item -LiteralPath $d -Recurse -Force }
  New-Item -ItemType Directory -Path $d -Force | Out-Null
  $passos = @(
    @('init', '-q'),
    @('config', 'core.autocrlf', 'false'),
    @('config', 'core.longpaths', 'true'),
    @('remote', 'add', 'origin', $HfRepo),
    @('sparse-checkout', 'set', $pasta),
    @('fetch', '-q', '--depth', '1', '--filter=blob:none', 'origin', $ref),
    @('-c', 'advice.detachedHead=false', 'checkout', '-q', 'FETCH_HEAD')
  )
  foreach ($a in $passos) {
    & git -C $d @a | Out-Null
    if ($LASTEXITCODE -ne 0) { Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction SilentlyContinue; return $null }
  }
  New-Item -ItemType File -Path (Join-Path $d '.completo') | Out-Null
  return $d
}

function Instalar-Hf {
  Write-Host 'HyperFrames (baixado do repositório original, licença Apache-2.0):'
  if (-not (Tem 'git')) { Aviso 'sem git: pulei as skills do HyperFrames (instale o git e rode de novo)'; return }
  foreach ($linha in Get-Content -LiteralPath (Join-Path $Kit 'skills\hyperframes.lista') -Encoding UTF8) {
    $linha = $linha.Trim()
    if (-not $linha -or $linha.StartsWith('#')) { continue }
    $campos = $linha -split '\s+'
    $ref, $pasta, $skills = $campos[0], $campos[1], $campos[2..($campos.Count - 1)]
    $d = Baixar-Hf $ref $pasta
    if (-not $d) { Aviso "não consegui baixar $pasta de $HfRepo em $ref (sem internet?): rode de novo depois"; continue }
    foreach ($s in $skills) {
      $src = Join-Path $d (Join-Path $pasta $s)
      if (Test-Path -LiteralPath $src) { Ligar $src } else { Aviso "$s não está em $pasta no $ref" }
    }
  }
}

if ($Dependencias) { Instalar-Dependencias }
if (-not $Verificar) {
  foreach ($dest in $Destinos) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
  Write-Host 'Skills do kit:'
  Get-ChildItem -LiteralPath (Join-Path $Kit 'skills\proprias') -Directory | ForEach-Object { Ligar $_.FullName }
  if (-not $SoProprias) { Instalar-Hf }
  # PIPE (pasta das ferramentas) fica salvo para o usuário; vale nos terminais abertos depois daqui
  [Environment]::SetEnvironmentVariable('PIPE', $Pipe, 'User')
  $env:PIPE = $Pipe
}
Verificar-Dependencias
Write-Host ''
Write-Host 'Ferramentas do fluxo ($PIPE):'
Write-Host "  PowerShell: `$env:PIPE = `"$Pipe`"   (já salvo para o seu usuário pelo instalador)"
$bashPipe = $Pipe -replace '\\', '/'
if ($bashPipe -match '^([A-Za-z]):(.*)$') { $bashPipe = '/' + $Matches[1].ToLower() + $Matches[2] }
Write-Host "  Git Bash:   export PIPE=`"$bashPipe`""
Write-Host '  Nos comandos Python, use sempre -X utf8 (ex.: uv run --with numpy python -X utf8 -I script.py): sem ele o'
Write-Host '  Python do Windows lê e grava os acentos errado.'
if (-not (Test-Path -LiteralPath (Join-Path $Kit 'perfil.md'))) {
  Write-Host "Próximo passo: copie perfil.exemplo.md para perfil.md e preencha (ou peça para a IA preencher com você)."
}
