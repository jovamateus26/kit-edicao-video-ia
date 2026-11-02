# Kit de edição de vídeo com IA

Instruções, skills, ferramentas e modelos para uma IA (Claude Code, Gemini CLI, Codex ou parecida) editar vídeo falado
vertical para Reels, Shorts e TikTok. O padrão de edição é:

- fala limpa de verdade;
- legenda karaokê revisada;
- prints reais nas notícias;
- fundo de estúdio LED;
- áudio em −14 LUFS;
- um único vídeo final, pronto para postar.

Tudo aqui saiu de vídeos publicados. Nomes, perfis, marcas e falas foram trocados por marcadores: preencha os seus no
`perfil.md`.

Funciona no Linux, no macOS e no Windows, nativo ou pelo WSL2.

## Como usar

### 1. Instale

**Linux, macOS ou WSL2:**

- Instale `ffmpeg` (com `zscale`; os estáticos têm), [`uv`](https://docs.astral.sh/uv/), Node.js 22+, Python 3.10+,
  `git` e Chrome/Chromium (para os prints de notícia).
- Rode `./instalar.sh`. Ele liga as skills do kit em `~/.claude/skills`, baixa as do HyperFrames e confere o que falta.
  Outras pastas de skills e outras opções: `./instalar.sh --help`.

**Windows:**

- Rode `instalar.cmd -Dependencias` no terminal. Ele instala pelo winget o ffmpeg completo, o uv, o Node, o Python, o Git
  e o Chrome.
- Depois rode `instalar.cmd` (dois cliques servem).
- Leia `skills/proprias/edicao-video-falado/guias/11-windows.md`: lá estão as diferenças do Windows e o caminho pelo WSL2.

GPU NVIDIA é opcional: acelera o whisper, o recorte e a composição.

### 2. Crie o seu perfil

Copie `perfil.exemplo.md` para `perfil.md` e preencha: @, estilo, formato padrão, CTA. A IA também pode preencher com
você na primeira conversa.

### 3. Peça a edição

Abra a IA nesta pasta, ou copie `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` e `perfil.md` para a raiz da sua pasta de vídeos.
Ponha os brutos em `projetos/<categoria>/NN - Título/` e peça, por exemplo:

> Edita o giro de hoje que está em projetos/Noticias/2026-10-30, as fontes estão no briefing.md

## O que tem aqui

```text
kit-edicao-video-ia/
├── AGENTS.md               instruções principais para a IA (CLAUDE.md e GEMINI.md apontam para ele)
├── perfil.exemplo.md       o que é seu: @, estilo, formato padrão, CTA, como você grava
├── instalar.sh             instalador para Linux, macOS e WSL
├── instalar.cmd / .ps1     instalador para Windows
├── LICENSE                 MIT (o kit)
├── THIRD_PARTY_NOTICES.md  o que é de terceiros e a licença de cada coisa
├── projetos/               seus vídeos (um episódio por pasta; fica fora do git)
└── skills/
    ├── README.md           catálogo: o que cada skill faz e quando usar
    ├── hyperframes.lista   skills do HyperFrames que o instalador baixa (e de qual versão)
    └── proprias/
        ├── edicao-video-falado/        O FLUXO
        │   ├── SKILL.md                resumo, regras e checklist
        │   ├── guias/                  01 fluxo · 02 limpeza da fala · 03 material bruto · 04 notícias · 05 layout
        │   │                           06 estúdio LED · 07 áudio · 08 entrega · 09 desempenho · 10 erros · 11 Windows
        │   ├── formatos/               giro de notícias, notícia com prova, app + resultado, loop + split,
        │   │                           bancada narrada, entrevista game show, loja/moda Clean Luxury, estilos visuais
        │   ├── ferramentas/            whisper (wh), sync, audit, edgecheck, vad, build, RVM, estúdio LED, finalize...
        │   └── modelos/                projeto completo do giro + tpl/make/captions dos outros formatos, briefing, plano
        └── editor-video-alta-retencao/ editor estilo-neutro com kit de badges e zonas seguras
```

As skills do HyperFrames (motor de composição HTML → vídeo, da HeyGen) não vêm no kit. O instalador baixa do
repositório original (github.com/heygen-com/hyperframes) as versões que os modelos usam.

## O fluxo em uma frase

Transcrever (whisper palavra a palavra) → decupar numa EDL → montar com limpeza de fala → auditar cada emenda na fonte →
legendar → compor no HyperFrames → conferir em snapshots → renderizar uma vez → normalizar → entregar com o texto de
publicação. Os detalhes estão em `skills/proprias/edicao-video-falado/guias/01-fluxo.md`.

## Licença

- **O kit:** MIT (`LICENSE`). Pode usar, mudar, redistribuir e usar comercialmente; só mantenha o aviso de licença nas cópias.
- **Peças de terceiros:** cada uma com a sua licença, em `THIRD_PARTY_NOTICES.md`. Fazem parte delas:
  - as skills do HyperFrames (Apache-2.0), baixadas pelo instalador;
  - as fontes do editor de badges (OFL e Ubuntu Font Licence);
  - o modelo RVM (GPL-3.0), baixado no primeiro uso.
- **MusicGen:** os pesos são CC-BY-NC 4.0, ou seja, **não comerciais**. Para vídeo monetizado ou de cliente, use trilha
  licenciada.

## Privacidade

O kit não traz senhas, chaves, contas, endereços de máquinas nem dados de pessoas. O `.gitignore` deixa fora do
repositório:

- o `perfil.md`;
- tudo em `projetos/`, menos o LEIA-ME.
