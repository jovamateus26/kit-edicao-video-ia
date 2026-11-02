# Biblioteca de Badges + Modelos HyperFrames

Badges animados (HyperFrames + GSAP) para 9:16, extraídos do Reel 3 (17/10/2026) e transformados em modelos reutilizáveis. Prévia: [`preview/galeria.png`](preview/galeria.png).

O kit é **estilo-neutro**: o visual de `badges.css` é só uma base tokenizada. Cores, fontes, véu de legibilidade, movimento de entrada/saída e a legenda inteira vêm do bloco `estilo` / `captions` do spec, que por sua vez vem do prompt ou do `estilo.json` (ver `../referencias/estilo.md`).

Todos seguem as zonas proibidas da skill (§3): nada sobre rosto, informação em cena ou legenda. A posição é calculada pelo `../scripts/overlay_safe_zones.py`.

## Estrutura

```text
badges/
├── badge_kit.py              # CLI: init, build, measure, place, auto, gallery, models, hf-models, hf-install
├── models.py                 # os 13 modelos (HTML + animação por deixas)
├── badges.css                # visual-base tokenizado (--glass, --ink, --font-sans...), sobrescrito por estilo.badges
├── captions.py               # adapta qualquer caption-* às palavras reais (sem cor/fonte/caixa impostas)
├── hyperframes_models.json   # os 24 modelos HyperFrames BAIXADOS, por função
├── assets/fonts (licenças em assets/fonts/LICENCAS.md; o GSAP vem da CDN)
├── examples/reel3_sailfish.json + reel3_keepout.json   # reproduz o Reel 3 v3 (com o estilo dele explícito no spec)
└── preview/galeria.png | galeria.html
```

## Os 13 modelos da skill

| Modelo | Para quê | Onde costuma caber |
|---|---|---|
| `pill-banner` | Gancho de 1 linha (chip + título) | Close de rosto: faixa acima do cabelo (~70px) |
| `title-chips` | Título + chips (specs, números) | Topo acima da cabeça / base livre |
| `swap` | Antes → depois (risca o antigo) | Topo/base livre |
| `keycaps-led` | Combinação de teclas + LED que muda de cor | Espaço livre grande (parede, janela) |
| `terminal-typing` | Digita o comando citado + saída | Abaixo da tela real, sobre o teclado |
| `ok-pill` | Selo "✓ DETECTADO / PRONTO" | Faixa estreita (borda da tela, mesa) |
| `ab-slots` | Opções lado a lado; uma é selecionada | Abaixo da tela real |
| `progress-pill` | Barra 0→100% + "✓ concluído" | Topo, sobre conteúdo antigo |
| `stamp` | Carimbo grande de 1 linha (tensão) | Acima do aparelho |
| `checklist-row` | Até 3 itens marcados no momento citado | Acima do aparelho |
| `vertical-win` | Comemoração vertical estreita (250px) | Lateral ao lado do celular |
| `side-status` | Painel lateral (kicker + título + chip) | Lateral livre |
| `final-cta` | Status + próximo passo + "Comenta X" | Base livre acima da legenda |

Campos e deixas de cada um: `python3 badge_kit.py models`. Em textos, `**trecho**` vira destaque.

## Passo a passo (vídeo novo)

```bash
KIT=~/.claude/skills/editor-video-alta-retencao/badges
SZ=~/.claude/skills/editor-video-alta-retencao/scripts/overlay_safe_zones.py

# 1. Projeto + vídeo (converte HDR do iPhone para SDR e deixa keyframes densos)
python3 $KIT/badge_kit.py init --project projeto_hf --video final/final_sem_legenda.mp4

# 2. Enxergar a cena: quadros com grade e rostos detectados -> escrever keepout.json
uv run $SZ grid projeto_hf/public/input-video.mp4 --at 1,5,12,24,40 --out .cache/grid

# 3. Escrever o spec (copie examples/reel3_sailfish.json e troque textos, tempos e deixas)

# 4. Montar, medir, posicionar sem cobrir nada e gerar a composição final
python3 $KIT/badge_kit.py auto spec.json --project projeto_hf --keepout keepout.json

# 5. Conferir e renderizar: badges + legenda HyperFrames saem juntos no mesmo render
npx hyperframes lint projeto_hf/public && npx hyperframes snapshot projeto_hf/public --at 5,20,40
npx hyperframes render projeto_hf/public -o final/final_com_legenda.mp4 --fps 30
```

A legenda vem do bloco `captions` do spec (modelo definido pelo estilo). Não queime `.ass` por cima.

O HyperFrames exige Node 22 ou superior: `export PATH=~/.nvm/versions/node/v22*/bin:$PATH`.

## Legendas (`captions`)

```bash
python3 $KIT/badge_kit.py captions-models     # trilha contínua + destaque; nenhum é padrão
```

```json
"captions": {"model": "<do estilo>", "words": "palavras.json", "keywords": [],
             "vars": {}, "case": "original", "group": {"max_words": 3, "max_chars": 20, "pause": 0.35},
             "scale": 0.75, "baseline_y": 1640, "css": ""}
```
O `captions.py` copia o modelo, troca o texto de exemplo pelas palavras reais com tempo, recalcula os grupos, ajusta duração e largura para 9:16 e monta como sub-composição. `vars` sobrescreve as constantes do modelo; sem `vars`, o modelo roda com os valores originais. Sem `model`, nenhuma legenda é montada.

## Estilo dos badges (`estilo`)

```json
"estilo": {"badges": {"vars": {"--glass": "rgba(255,255,255,.9)", "--ink": "#111", "--font-sans": "Inter, sans-serif"},
                      "css": "", "legibility": false},
           "motion": {"in": {"x": 0, "y": 40, "blur": 0, "duration": 0.4, "ease": "power2.out"},
                      "out": {"x": 0, "y": 20, "blur": 0, "duration": 0.25, "ease": "power2.in"}}}
```

## Modelos HyperFrames baixados (24)

Ficam em `~/Projetos/hyperframes-showcase` (abra o `index.html` de lá para ver as demos). Inventário completo do registry: `../referencias/catalogo_hyperframes.md`.

```bash
python3 $KIT/badge_kit.py hf-models                         # todos
python3 $KIT/badge_kit.py hf-models --funcao dados          # filtra por função
python3 $KIT/badge_kit.py hf-models --query terminal
python3 $KIT/badge_kit.py hf-install badge-pop --project projeto_hf
```

A maioria dos **blocks** é 16:9 (1920×1080). Em 9:16, monte num wrapper com `scale` (cerca de 0,56) ou adapte o layout, e posicione sempre pelo `overlay_safe_zones.py`. **Components** são colados direto na composição; instruções e variáveis no comentário do topo de cada arquivo.

## Criando um modelo novo

1. Adicione em `models.py` com `@model(...)`: campos, `html(f)` e `beats(f, cue, start, end)`. Os tipos de animação disponíveis são `in`, `stagger`, `pop`, `strike`, `led`, `type`, `select`, `progress`, `fldone`, `check` e `stamp`.
2. Coloque o CSS em `badges.css` com classes próprias.
3. Rode `python3 badge_kit.py gallery` e confira a `preview/galeria.png`.
