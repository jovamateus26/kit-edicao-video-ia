# Inventário de ferramentas

Tudo o que a skill sabe usar. É um **inventário**: descreve o que cada item faz e o que ele exige da cena, sem dizer qual é "melhor" para um assunto. A escolha vem do estilo ([estilo.md](estilo.md)).

Atualize o registry com `python3 scripts/atualizar_catalogo.py`; o inventário completo (447 itens) fica em [catalogo_hyperframes.md](catalogo_hyperframes.md).

---

## 1. Pipeline técnico (scripts da skill)

| Ferramenta | Faz | Comando |
|---|---|---|
| `scripts/corte_alta_retencao.py` | Transcreve (faster-whisper), remove silêncio, filler words e repetições, renderiza com micro-crossfade de áudio, gera `palavras.json`/`srt`/`ass`, legenda (se houver estilo), relatório e base de copy | `uv run scripts/corte_alta_retencao.py PASTA [--estilo estilo.json]` |
| `scripts/color_engine.py` | Presets de cor ffmpeg ou LUT `.cube` | `--color` / `estilo.cor` |
| `scripts/broll_engine.py` | Imagem → clipe (zoom opcional), sobreposição com dissolvência, geração via gflow | `estilo.broll` |
| `scripts/semantic_curator.py` | Curadoria de trechos (plano editorial) | `plano_editorial.json` |
| `scripts/overlay_safe_zones.py` | `grid`: quadros com grade + rostos; `place`: posições livres de rosto, keepouts e legenda | §Overlay na SKILL.md |
| `badges/badge_kit.py` | Monta badges + legenda HyperFrames num projeto a partir de um spec | `init / build / measure / place / auto / gallery / models / captions-models / hf-models / hf-install` |
| `badges/captions.py` | Adapta qualquer `caption-*` às palavras reais (troca texto, grupos, duração, largura, vars) | bloco `captions` do spec |
| `scripts/atualizar_catalogo.py` | Regenera o inventário do registry | — |

Flags do corte: `--formato vertical|horizontal`, `--min-silence 0.35`, `--model tiny|base|small|medium`, `--device auto|cpu|cuda`, `--crf 18–23`, `--plan`, `--keep-cache`, `--legenda hyperframes|ass|none`, `--legenda-modelo`, `--color`, `--lut`, `--broll`, `--estilo`.

### Presets de cor (`cor.preset`)

| Preset | Filtro |
|---|---|
| `none` | nenhum (imagem original) |
| `studio` | contraste +6%, saturação +6%, unsharp leve |
| `vibrant` | contraste +8%, saturação +12%, unsharp |
| `cinematic` | contraste +10%, saturação −2%, curva S, unsharp |
| `warm` | contraste +5%, saturação +8%, balanço quente |
| LUT | qualquer `.cube` em `cor.lut` |

### B-roll

- `manual`: usa imagens/clipes da pasta do projeto.
- `auto`: local + geração via `gflow` (`gflow image t2i "<prompt>" -o arq.png --aspect 9:16 --model nano2`, `gflow video t2v "<prompt>" -o arq.mp4 --aspect 9:16 --duration 4`; MCP `gflow_generate_image`, `gflow_generate_video`, `gflow_get_credits`, `gflow_auth_status`). Auth: `gflow auth login`, `gflow auth status`, `gflow credits user`. O sufixo estético do prompt vem de `broll.prompt_sufixo`.
- Parâmetros: `duracao`, `zoom_max`, `dissolve`. O áudio original segue intacto por baixo.

---

## 2. Legendas

### 2.1 Modelos `caption-*` do registry (trilha contínua)

Montados pelo `captions.py`. Constantes ajustáveis via `legenda.vars` (abra o HTML do modelo em `~/Projetos/hyperframes-showcase/components/NOME/` para ver as disponíveis).

| Modelo | Mecânica | Exige da cena |
|---|---|---|
| `caption-pill-karaoke` | pílula + cor por palavra ativa | — |
| `caption-highlight` | fundo varre a palavra ativa | — |
| `caption-clip-wipe` | wipe L→R por palavra | — |
| `caption-particle-burst` | palavras-chave viram partículas | — |
| `caption-neon-glow` | texto com glow, keywords destacadas | contraste cai em fundo claro |
| `caption-gradient-fill` | gradiente + entrada elástica | — |
| `caption-matrix-decode` | letras embaralham antes de revelar | — |
| `caption-neon-accent` | acentos luminosos multicor | contraste cai em fundo claro |
| `caption-emoji-pop` | contorno + entrada espremida, emoji opcional | — |
| `caption-weight-shift` | transição de peso da fonte | fonte variável |
| `caption-glitch-rgb` | aberração RGB + scanlines | — |
| `caption-blend-difference` | inverte cor por pixel (mix-blend difference) | não adaptado pelo `captions.py` ainda: testar antes |
| `inline-highlight` | marca-texto animado atrás do texto | não adaptado ainda |

### 2.2 Modelos de destaque (frase única, não trilha)

`caption-kinetic-slam` (palavra única em tela cheia), `caption-texture` (texto grande com textura: lava, mármore, metal, madeira, concreto, pedra), `caption-camera-follow` (frase num "mundo" maior que a tela), `caption-editorial-emphasis` (duas fontes, contraste de tamanho), `caption-parallax-layers` (texto 3D atrás do assunto, exige recorte), `mk-callout-highlight` (block 16:9, ênfase guiada por escalar). Entram como overlay, seguindo as zonas proibidas.

### 2.3 `/embedded-captions`: 35 identidades

Só para vídeo de **uma tomada, um assunto, sem cortes** (recusa vídeos com cortes ou sem pessoa). Faz recorte do assunto e põe texto em profundidade. Catálogo completo: `~/.claude/skills/embedded-captions/CATALOG.md`.

| Superfície | Identidades |
|---|---|
| Texto embutido na cena (coluna) | `cream` (cena escura/média quente), `ink` (cena clara), `editorial`, `keynote`, `documentary`, `neon` (cena escura), `glitch`, `chrome`, `velocity` |
| Embutido com corpo na frente | `loud` |
| Trilha verbatim + clímax | `anchor`, `ordnance`, `terminal`, `neonsign`, `scoreboard`, `transit`, `vhs`, `arcade`, `dossier`, `laser`, `thunder`, `hologram`, `biolume`, `aurora`, `spectrum`, `papercut`, `popup`, `chalkboard`, `graffiti`, `brush` (faixa média/clara), `inkwater` (faixa média/clara), `ransom`, `lastpage` |
| Outras superfícies | `stardust` (poema acumulado, exige uma lateral livre), `stomp` (cards de tela cheia) |

### 2.4 Fallback ASS (ffmpeg)

`--legenda ass` ou quando o render HyperFrames falha. Visual em `legenda.ass` (fonte, cores ASS `&HAABBGGRR`, contorno, sombra, caixa, palavra ativa).

---

## 3. Badges e overlays

### 3.1 Kit da skill (13 modelos, `badges/models.py`)

Visual-base tokenizado em `badges.css`; tudo é sobrescrito por `estilo.badges` / `estilo.motion`. Prévia: `badges/preview/galeria.png`. Campos e deixas: `python3 badges/badge_kit.py models`.

| Modelo | Função | Altura aprox. / onde cabe |
|---|---|---|
| `pill-banner` | 1 linha: chip + título | ~70px, faixa acima da cabeça |
| `title-chips` | título + chips (specs, números, tags) | ~180px |
| `swap` | antes → depois (risca o antigo) | ~200px |
| `keycaps-led` | teclas combinadas + LED de status | ~380px, área livre grande |
| `terminal-typing` | digita comando + saída | ~220px |
| `ok-pill` | selo de confirmação de 1 linha | ~86px |
| `ab-slots` | opções lado a lado, uma selecionada | ~200px |
| `progress-pill` | barra 0→100% + concluído | ~90px |
| `stamp` | kicker + carimbo de 1 linha | ~180px |
| `checklist-row` | até 3 itens marcados na deixa | ~160px |
| `vertical-win` | selo vertical estreito | 250px de largura, lateral |
| `side-status` | painel lateral: kicker + título + chip | 440px de largura |
| `final-cta` | status + próximo passo + botão | ~280px, acima da legenda |

Animações por deixa disponíveis: `in`, `stagger`, `pop`, `strike`, `led`, `type`, `select`, `progress`, `fldone`, `check`, `stamp`.

### 3.2 Modelos HyperFrames já baixados (24, `~/Projetos/hyperframes-showcase`)

`python3 badges/badge_kit.py hf-models [--funcao F] [--query txt]` · `hf-install NOME --project DIR`. Funções: `codigo / terminal`, `dados / graficos / mapas`, `ui / chat / cursor`, `social / notificacao / cta`, `overlay / anotacao`, `lower-third / identificacao`, `produto / showcase / galeria`, `camera / 3d / video`, `primitiva de movimento`, `legenda`.

### 3.3 Registry completo (447 itens)

Por função ([catalogo_hyperframes.md](catalogo_hyperframes.md)): legenda 19 · transição 73 · lower-third 13 · título/tipografia 68 · dados/gráficos/mapas 20 · código/terminal 12 · UI/chat/cursor 39 · social/notificação/CTA 12 · overlay/anotação 9 · produto/showcase/galeria 45 · logo/marca 5 · fundo/textura/shader 59 · câmera/3D/vídeo 16 · primitivas de movimento 30 · outros 27.

```bash
npx hyperframes catalog --query "<efeito em inglês>"      # busca por significado
npx hyperframes catalog --tag transition --json            # por tag
npx hyperframes add NOME --dir <projeto>/public             # instala (precisa de internet)
npx hyperframes feedback --search-miss "<busca>" --wanted "<efeito>" --tier words   # registra lacuna
```

Blocks 16:9 (1920×1080) entram em 9:16 num wrapper com `scale` (~0,56) ou com layout adaptado; blocks `vertical` já são 1080×1920. Components são colados na composição conforme o comentário do topo do arquivo.

---

## 4. Skills HyperFrames (roteamento por tarefa)

| Skill | Quando |
|---|---|
| `/hyperframes` | entrada obrigatória para criar/editar qualquer composição |
| `/hyperframes-core` | contrato da composição, `data-*`, tracks, sub-composições |
| `/hyperframes-cli` | init, lint, check, snapshot, preview, render, transcribe, tts, remove-background, beats, keyframes |
| `/hyperframes-registry` | buscar/instalar/ligar blocks e components |
| `/hyperframes-animation` | regras de movimento, blueprints, 24 efeitos de texto, adapters (GSAP, Lottie, Three.js, Anime.js, CSS, WAAPI, TypeGPU) |
| `/hyperframes-keyframes` | punch-in, zoom, reframe, Ken Burns, câmera, masks, SVG |
| `/hyperframes-audio` | fades, ducking, EQ, compressor, automação, buses |
| `/hyperframes-creative` | design spec, paleta, tipografia, beats (aplica o estilo dado, não inventa) |
| `/hyperframes-studio` | trabalho no Studio, timeline, safe zones |
| `/media-use` | BGM, SFX, imagem, ícone, logo, voz, LUT, transcrição, remoção de fundo |
| `/embedded-captions`, `/captions-overlay` | legenda em profundidade / doutrina de overlay de legenda |
| `/talking-head-recut` | cards gráficos sincronizados sobre talking-head |
| `/motion-graphics`, `/general-video`, `/faceless-explainer`, `/music-to-video`, `/pr-to-video`, `/product-launch-video`, `/slideshow`, `/figma`, `/remotion-to-hyperframes` | formatos específicos |
| `/motion-doctrine`, `/cut-the-curve`, `/seam-craft`, `/oversized-cursor` | técnica de transição/continuidade (aplicar só se o estilo pedir esse tipo de movimento) |

Requisito: Node 22+ (`export PATH=~/.nvm/versions/node/v22*/bin:$PATH`).
