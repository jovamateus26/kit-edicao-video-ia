# Skills

Uma skill é uma pasta com um `SKILL.md` (instruções que a IA carrega quando a tarefa pede) e, às vezes, scripts e
referências. O `instalar.sh` liga estas pastas em `~/.claude/skills/` (Claude Code); use `--destino` para outras
ferramentas (ex.: `~/.agents/skills`, `~/.gemini/skills`). No Windows, o `instalar.cmd` faz o mesmo com junções em
`%USERPROFILE%\.claude\skills` (`-Destino` para outras pastas). Sem instalar, a IA também pode ler os `SKILL.md`
das nossas direto daqui.

## Nossas (`proprias/`)

| Skill | Quando usar |
|---|---|
| `edicao-video-falado` | **o fluxo principal**: vídeo falado gravado no celular → vídeo vertical limpo, legendado, composto e normalizado. Guias, formatos, ferramentas e modelos |
| `editor-video-alta-retencao` | editor estilo-neutro e mais automático: corte de silêncio/fillers/repetições com crossfade, transcrição, kit de badges e legendas, zonas seguras para overlays (`overlay_safe_zones.py`), catálogo de 447 itens do registry por função. Bom para cortes rápidos e para posicionar overlays sem cobrir rosto/informação. A regra "um vídeo só, com legenda" do `AGENTS.md` vale acima da entrega "com e sem legenda" dela |

## HyperFrames (de terceiros, baixadas pelo instalador)

HyperFrames é o motor de composição: o vídeo é uma página HTML com linha do tempo GSAP, renderizada quadro a quadro.

- **Origem:** projeto da HeyGen, licença Apache-2.0.
- **Download:** as skills não vêm no kit. O `instalar.sh`/`instalar.ps1` baixa cada uma do repositório original
  (github.com/heygen-com/hyperframes), na versão listada em `hyperframes.lista`.
- **Por onde começar:** pela `hyperframes`, que encaminha para as outras.

Na versão 0.8.185, o HyperFrames publica 7 skills. Ele aposentou as de domínio e de fluxo (`hyperframes-core`,
`embedded-captions`, `general-video` e outras) e juntou o conteúdo delas na `hyperframes` e na `media-use`. O kit
instala as aposentadas também, do último commit que as tem, porque os guias e o editor de badges ainda as citam.

| Skill | Uso no nosso fluxo |
|---|---|
| `hyperframes` | **ler primeiro** para qualquer composição: contrato de render, ciclo de trabalho, referências de legenda, overlay, movimento e formato |
| `hyperframes-cli` | `init`, `check`, `snapshot`, `preview`, `render`; leitura de erros de build/render |
| `hyperframes-registry` | ~450 blocos prontos (transições, overlays, títulos, kinetic type, gráficos): use antes de construir à mão |
| `media-use` | **SFX** (`audio/assets/sfx/`), trilhas, imagens, ícones, cutouts, tratamento de cor de footage, mixagem |
| `figma`, `remotion-to-hyperframes`, `slideshow` | Figma no vídeo, migração do Remotion, apresentação ao vivo |
| `captions-overlay` | doutrina da legenda: overlay por cima do filme, nunca faixa reservada |
| `motion-doctrine`, `cut-the-curve`, `seam-craft`, `oversized-cursor` | doutrina de movimento contínuo, catálogo de transições, emendas sem flash, cursor grande em demos |
| `changelog-video` | fluxo de vídeo de changelog da própria HeyGen (exemplo de projeto completo) |

Aposentadas, instaladas do commit `207c8a4` (21/10/2026):

| Skill | Uso no nosso fluxo |
|---|---|
| `hyperframes-core` | contrato da composição: `data-start`/`data-duration`, `class="clip"`, trilhas, `window.__timelines`, regras determinísticas |
| `hyperframes-animation` | regras de movimento, blueprints de cena, transições, GSAP e outros runtimes |
| `hyperframes-keyframes` | punch-in, zoom, reenquadramento, Ken Burns, movimentos de câmera seek-safe |
| `hyperframes-audio` | mixagem dentro da composição: fades, ducking, EQ, compressor, grupos |
| `hyperframes-creative`, `hyperframes-studio` | direção criativa (paleta, tipografia, beats); Studio e safe zones |
| `embedded-captions` | legenda cinematográfica atrás do assunto (35 identidades) para uma tomada sem cortes |
| `talking-head-recut` | cartelas, lower-thirds, callouts e painéis sobre talking head (o clipe roda intacto) |
| `motion-graphics`, `general-video` | peça curta de motion; composição livre/multicena (autoria padrão dos nossos projetos) |
| `faceless-explainer`, `product-launch-video`, `pr-to-video`, `music-to-video` | explicador sem rosto, lançamento de produto, PR em vídeo, clipe musical |

### Atualizar as skills do HyperFrames

Para mudar de versão, troque a tag em `hyperframes.lista` e rode o instalador de novo com `--forcar` (Windows: `-Forcar`).
Antes de fixar a versão nova nos comandos (`hyperframes@0.8.185`), confira se os modelos ainda passam no `check`.
Também dá para instalar direto pelo CLI deles (`npx hyperframes skills`), mas ele só traz as 7 atuais.
