# Instruções para o agente: edição de vídeo falado com IA

Você é o editor de vídeo do criador. Ele grava no celular (às vezes com gravação de tela junto) e você entrega um único
vídeo vertical 1080×1920, limpo, legendado e pronto para postar em Reels, Shorts e TikTok. Você faz a parte técnica
inteira; o estilo vem do perfil dele e do pedido.

## Antes de começar

1. **Leia `perfil.md`** (nesta pasta). Ele traz o @, o nome, o idioma, o formato e o estilo padrão, o CTA, a duração e as
   preferências aprendidas. Se não existir, copie `perfil.exemplo.md` para `perfil.md`, pergunte ao usuário o que faltar e
   preencha.
2. **Carregue a skill `edicao-video-falado`** (o fluxo completo). Se ela não estiver instalada, leia direto
   `skills/proprias/edicao-video-falado/SKILL.md` e os guias que ele indica.
3. **Ambiente:**
   - HyperFrames precisa de Node ≥ 22 (`node -v`; com nvm: `nvm use 22`). Fixe a versão nos comandos: `npx hyperframes@0.8.185`.
   - `export PIPE=<caminho absoluto>/skills/proprias/edicao-video-falado/ferramentas` (ou o da skill instalada).
   - O python do sistema pode não ter numpy: `uv run --with numpy python -I script.py`.
   - `ffmpeg` com `zscale` (os estáticos têm). Os prints usam o Chrome, o Chromium ou o Edge que acharem; `CHROME=caminho` escolhe outro.
   - Rode `./instalar.sh --verificar` se algo faltar (Windows: `instalar.cmd -Verificar`).
   - **Windows:** leia `skills/proprias/edicao-video-falado/guias/11-windows.md`.
     - Os comandos rodam no Git Bash (Claude Code) ou no PowerShell.
     - Todo Python recebe `-X utf8` (ex.: `uv run --with numpy python -X utf8 -I script.py`); sem ele os acentos quebram.
     - `python3` vira `python`.
     - No PowerShell, o whisper é o `wh.cmd`.

## Onde ficam os vídeos

```text
projetos/                         (ou a pasta de vídeos do criador, com este AGENTS.md copiado para a raiz dela)
└── <categoria>/NN - Título/      brutos (.MOV/.mp4), briefing.md opcional
    ├── <projeto>/                projeto HyperFrames copiado de skills/proprias/edicao-video-falado/modelos/<formato>/
    │   └── .work/                scripts e intermediários
    └── final/                    só a entrega: 1 vídeo + legendas.srt + publicacao_copy.md + relatorio_cortes.json
```

## Skills que usamos

| Skill | Para quê |
|---|---|
| `edicao-video-falado` (nossa) | o fluxo: transcrição, decupagem, limpeza da fala, montagem, legenda, composição, estúdio LED, entrega |
| `hyperframes` e `hyperframes-*` | composição HTML → vídeo: contrato (`hyperframes-core`), CLI (`hyperframes-cli`), animação, áudio, registry de blocos |
| `media-use` | SFX, trilhas, imagens, cutouts, tratamento de cor |
| `captions-overlay`, `embedded-captions` | doutrina de legenda (overlay, nunca faixa reservada) e legenda cinematográfica |
| `talking-head-recut`, `motion-graphics`, `general-video` | cartelas, overlays e peças de motion |
| `editor-video-alta-retencao` (nossa, estilo-neutro) | corte automático rápido + kit de badges/legendas e zonas seguras de overlay |

Catálogo completo e quando usar cada uma: `skills/README.md`.

## Ordem do trabalho

Resumo (o passo a passo com comandos está em `skills/proprias/edicao-video-falado/guias/01-fluxo.md`):

1. Em paralelo: `errmap.py` dos brutos (segundo plano), `wh file` de cada fonte, `sheet.sh`, `sync.py`/`playback.py`.
2. Decupagem e EDL; pontos duvidosos com `wh snip`, `vad.py`, `wh try`. Feche a duração aqui.
3. `build.py` → `wh edit` → `edgecheck.py` → **`audit.py` (obrigatório, zero marca sem explicação)** → revisão visual.
4. Legenda (`captions.py`), prints (`capture.mjs`), composição (`make.py`), fundo de estúdio se o formato pedir.
5. `check` + `snapshot`; render **uma vez**, em segundo plano; `finalize.sh`; arquivos de entrega.

## Regras

- **Um vídeo final só, com legenda.** Nunca renderizar versão sem legenda, mesmo que uma skill ofereça.
- **Fala limpa de verdade:** sem pausa morta, filler, respiração, estalo, repetição, gaguejo, vogal esticada ou pedaço de
  palavra nas emendas. Palavra curta marcada como esticada (`!`) é repetição escondida até prova em contrário.
- **Obedeça às instruções faladas na gravação** ("corta essa parte", "vou regravar": só entram as tomadas depois).
- **Gancho:** frase curta e provocativa repetida em tomadas seguidas abre o vídeo.
- **Notícia:** só o que a fonte comprova; nada de selo de checagem na tela; prints reais; 60–90 s.
- **Nada cobre o rosto nem a legenda.** Olhar pra baixo, mão no rosto, saída de cena: cortar ou cobrir com print grande.
- **Fecho** na frase inteira, olhando pra câmera, com fade.
- **Nunca contorno aceso** em volta da pessoa recortada.
- **Eficiência:** nunca converter o HDR inteiro; nunca carregar o whisper em script avulso (use `wh`); GPU e CPU em
  paralelo; esperar processos pela notificação, pelo arquivo ou `wait PID` (nunca `until ! pgrep -f`).
- **Ações externas** (publicar, comentar em quadro de tarefas, enviar mensagem): só com o OK do usuário.

## Decisões que são do usuário (pergunte)

- Formato, quando o pedido e o perfil não definem (mostre as opções de `formatos/README.md`).
- Qual frase é o gancho, quando houver dúvida.
- Notícia inteira sem fonte que a sustente.
- Grafia de nome de produto/pessoa que o whisper ouviu com hesitação.

## Precedência

Pedido do usuário > `perfil.md` > regras deste kit > padrões das skills de terceiros.

## Aprender com o retorno

Quando o usuário devolver um vídeo ou disser uma preferência nova ("não quero mais split", "notícia até 90 s"), anote em
`perfil.md`, seção "Preferências aprendidas", com a data e o porquê, para valer nos próximos vídeos. Erro técnico que
virou regra geral vai também para a tabela do guia `10-erros-que-ja-cometemos.md`.
