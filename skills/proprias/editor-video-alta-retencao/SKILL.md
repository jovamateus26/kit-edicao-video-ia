---
name: editor-video-alta-retencao
description: "Editor de vídeo falado profissional e estilo-neutro para redes sociais (Shorts, Reels, TikTok, YouTube, LinkedIn, X). Corta silêncios, filler words (éee, hum, ãhn), gaguejos e repetições com micro-crossfade de áudio, transcreve palavra a palavra e entrega versões com e sem legenda em pasta isolada por tema. Conhece todo o arsenal HyperFrames (modelos caption-*, 35 identidades de /embedded-captions, 13 badges do kit, 447 itens do registry, presets de cor, B-roll, gflow) e posiciona overlays sem cobrir rosto, informação ou legenda. NÃO escolhe estilo: cor, legenda, badges, B-roll e movimento vêm do prompt ou de um estilo.json. Use para cortar, editar, remover hesitações, legendar, adicionar badges/cards/motion ou preparar vídeos para publicação."
---

# Editor de vídeo (profissional e estilo-neutro)

## 0. Princípio: a skill executa, o estilo decide

Esta skill tem dois papéis separados:

- **Técnico (sempre aplicado):** corte limpo, áudio contínuo, transcrição correta, sincronia, formato, zonas proibidas, legibilidade verificada, render válido. É o que faz o trabalho ser profissional.
- **Estético (nunca decidido pela skill):** preset de cor, modelo e cores da legenda, caixa do texto, agrupamento de palavras, badges, B-roll, movimento, tipografia, tom da copy. Vem do **prompt** ou de um **`estilo.json`** ([referencias/estilo.md](referencias/estilo.md)).

Regras de neutralidade:
1. Não escolha estilo por nicho, assunto, plataforma ou preferência própria. Não existe "estilo padrão da skill".
2. Se o prompt definir o estilo, traduza-o para `estilo.json` na pasta do projeto, mostre ao usuário e rode.
3. Se faltar uma decisão estética necessária (ex.: qual legenda), liste as opções do inventário que cabem tecnicamente na cena e **pergunte**. Não preencha sozinho.
4. Se o usuário delegar ("escolha você"), proponha uma opção com o motivo e espere confirmação.
5. Os estilos em `referencias/estilos-exemplo/` só valem quando o prompt pedir por nome.
6. Alertas técnicos são bem-vindos (ex.: "este modelo perde contraste nesta cena clara"); trocar o estilo por conta própria não é. Avise e pergunte.

Inventário completo do que existe: [referencias/ferramentas.md](referencias/ferramentas.md) (pipeline, presets de cor, B-roll, todos os modelos de legenda, 35 identidades, 13 badges, 24 modelos baixados, skills HyperFrames) e [referencias/catalogo_hyperframes.md](referencias/catalogo_hyperframes.md) (os 447 itens do registry por função).

---

## 1. Estrutura de pastas (projeto auto-contido)

```text
Videos para editar/
└── [nome-do-tema]/
    ├── gravacao_principal.mp4       <-- vídeo falado bruto (o maior vídeo da pasta)
    ├── imagem_ou_broll.png/mp4      <-- (opcional) assets do usuário
    ├── estilo.json                  <-- (opcional) decisões estéticas (referencias/estilo.md)
    ├── plano_editorial.json         <-- (opcional) intervalos autorizados
    ├── .cache/                      <-- temporários, auto-limpo
    └── final/
        ├── final_sem_legenda.mp4
        ├── final_com_legenda.mp4    <-- só existe se o estilo definir a legenda
        ├── palavras.json            <-- palavras com tempo, caixa original (transcript.json do HyperFrames)
        ├── legendas.srt / legendas.ass
        ├── hyperframes/             <-- projeto HyperFrames (spec.json: legenda + badges + estilo)
        ├── relatorio_cortes.json
        └── publicacao_copy.md       <-- palavras-chave + transcrição (base para a copy no tom do prompt)
```

---

## 2. Fluxo de trabalho

1. **Entender o pedido.** Separe o que é técnico (o que cortar, formato, plataforma) do que é estético (cor, legenda, badges, B-roll, movimento). Para o estético, monte o `estilo.json` a partir do prompt; o que não foi definido fica ausente.
2. **Corte técnico:**
   ```bash
   uv run ~/.claude/skills/editor-video-alta-retencao/scripts/corte_alta_retencao.py "Videos para editar/nome-do-tema" --formato vertical
   ```
   Precedência: flags > `estilo.json` (da pasta ou `--estilo`) > neutro (cor `none`, B-roll `none`, sem versão legendada).
3. **Revisar a transcrição** em `final/palavras.json` (nomes próprios, termos técnicos), sem mexer nos tempos.
4. **Legenda** (se o estilo definiu `legenda.modelo`): o script já renderiza. Se não definiu, pergunte o modelo e rode o kit (§4).
5. **Overlays** (só se o prompt pedir): siga §3 e §4.
6. **Conferir** (§5) e entregar com um resumo do que foi aplicado e de onde veio cada decisão estética.

### O que o corte técnico garante
- Remoção de silêncios acima de `--min-silence` (0,35 s), filler words, gaguejos e repetições de frase, com padding de 60/80 ms e micro-crossfade de áudio de 8 ms nas emendas.
- Recorte/escala para o formato (9:16 1080×1920 ou 16:9 1920×1080), CRF 20, áudio intacto sob B-rolls.
- Cor só quando o estilo pedir; filtro aplicado no mesmo grafo do corte (sem re-encode extra).
- **HDR do iPhone (HLG/bt2020):** converta para SDR bt709 antes do HyperFrames (o `badge_kit.py init` já faz): `zscale=tin=arib-std-b67:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p`.

---

## 3. Zonas proibidas para overlays (regra técnica, vale para qualquer estilo)

> Todo overlay: badges, cards, terminais, keycaps, CTAs, stickers, motion graphics, B-roll em janela.

**Nunca cobrir:**
- **Rosto**: da testa/cabelo ao queixo, inclusive quando a pessoa se mexe.
- **Informação em cena**: texto de terminal/código, tela de aparelho mostrando resultado, produto mostrado, mãos executando a ação narrada.
- **Legenda**: a faixa da legenda definida pelo estilo (no 1080×1920 com `baseline_y` 1640, a faixa começa em `y ≈ 1500`).
- **Interface do app**: topo `y < 150`; evitar a coluna de botões da direita (`x ≥ 980`, `y ≥ 1180`).

**Onde colocar:** espaço livre ao lado/acima/abaixo do assunto → mesmo card em escala menor (mín. 0,72) → variante compacta → outro instante da mesma fala → não mostrar. Nunca forçar por cima.

**Processo obrigatório antes de renderizar overlay:**
1. `uv run scripts/overlay_safe_zones.py grid VIDEO --at 3,10,24 --out .cache/grid` (quadros com grade e rostos).
2. Escrever `keepout.json` com os retângulos de informação por intervalo (pesos: `1.0` informação, `2.0` crítico, `0.1–0.5` pode ser levemente coberto; `"ignore_faces": true` quando o detector acusar rosto em objetos).
3. Medir w×h reais de cada card (o `badge_kit.py auto` mede sozinho).
4. `uv run scripts/overlay_safe_zones.py place VIDEO --cards cards.json --keepout keepout.json --out placements.json --debug .cache/placements`.
5. Resolver todo `clean=false` (variante, outro momento ou remoção).
6. Conferir `placements_sheet.jpg`: verde (card) nunca sobre vermelho/laranja (rosto/keepout) ou amarelo (legenda).

Dicas: um card por plano estável (detecte cortes com `ffmpeg -vf "select='gt(scene,0.22)',showinfo"`); close de rosto quase nunca comporta card grande.

---

## 4. Legenda e badges com o kit

Tudo em `~/.claude/skills/editor-video-alta-retencao/badges/` ([badges/README.md](badges/README.md)).

```bash
KIT=~/.claude/skills/editor-video-alta-retencao/badges
python3 $KIT/badge_kit.py captions-models      # modelos de legenda disponíveis
python3 $KIT/badge_kit.py models               # 13 badges do kit (campos e deixas)
python3 $KIT/badge_kit.py hf-models --funcao "codigo"   # modelos HyperFrames baixados
python3 $KIT/badge_kit.py init --project DIR --video final/final_sem_legenda.mp4
python3 $KIT/badge_kit.py auto spec.json --project DIR --keepout keepout.json
npx hyperframes lint DIR/public && npx hyperframes snapshot DIR/public --at 5,20,40
npx hyperframes render DIR/public -o final/final_com_legenda.mp4 --fps 30
```

Spec mínimo (os valores estéticos saem do `estilo.json`; nada é preenchido pela skill):
```json
{"duration": 60.0, "fps": 30, "width": 1080, "height": 1920,
 "estilo": {"badges": {...}, "motion": {...}},
 "badges": [{"id": "c01", "model": "...", "start": 1.0, "end": 4.0, "fields": {...}, "cues": {...}}],
 "captions": {"model": "<do estilo>", "words": "palavras.json", "vars": {...}, "case": "original", "group": {...}}}
```
Exemplo completo (com o estilo do Reel 3 explícito): `badges/examples/reel3_sailfish.json`.

**Ordem de busca de um modelo pedido pelo estilo:** kit da skill → modelos baixados → registry (`npx hyperframes catalog --query`) → criar do zero (registrar lacuna com `npx hyperframes feedback --search-miss`). A ordem é de disponibilidade, não de preferência: se o estilo nomeia um item, use esse item.

**Limites técnicos dos modelos** (informar, não decidir): modelos de destaque (`caption-kinetic-slam`, `caption-texture`, `caption-camera-follow`, `caption-editorial-emphasis`, `caption-parallax-layers`, `mk-callout-highlight`) não funcionam como trilha contínua; `/embedded-captions` só aceita uma tomada sem cortes com um assunto; `caption-parallax-layers` e `freeze-frame-dressing` exigem recorte; blocks 16:9 precisam de wrapper em 9:16.

---

## 5. Controle de qualidade (antes de entregar)

- Emendas de áudio sem clique; nenhuma palavra cortada no meio; sincronia legenda × fala dentro de 1 frame.
- Transcrição revisada (nomes, termos técnicos).
- Snapshot em 3+ instantes: legenda legível sobre o fundo real (se não estiver, **avise** e sugira ajuste dentro do estilo pedido, sem trocar o estilo).
- Nenhum overlay em zona proibida (§3).
- `npx hyperframes lint` sem erros; render com a duração do corte.
- Resumo final: cortes (tempo economizado, fillers), arquivos entregues e, para cada decisão estética, a origem (prompt, `estilo.json`, flag).
