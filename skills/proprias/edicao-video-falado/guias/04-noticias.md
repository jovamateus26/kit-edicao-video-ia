# Vídeo de notícia: credibilidade antes de tudo

O formato de notícia vende credibilidade e autoridade. O rosto do apresentador dá autoridade; o print real da matéria,
com a frase grifada no instante em que ela é falada, dá a prova.

## Regras

1. **Só o comprovado.** Antes de montar a EDL, confira cada frase falada contra as matérias. Frase sem fonte sai do corte,
   inclusive piada com número inventado. Se a notícia inteira não se sustenta, pergunte antes de montar.
2. **Nunca corrigir o apresentador na tela.** Nada de selo de "checagem", "na verdade…" ou correção. O que não confere sai;
   o que confere com ressalva fica e a tag/post usam o termo certo (ex.: a fala diz "multa", a fonte diz "acordo": a tag
   diz "acordo").
3. **Não acrescentar pessoas ou fatos que ele não falou** (nem no vídeo nem no post).
4. **Quando a fala arredonda**, o print mostra o número da fonte ("≈70%", "US$ 6,3 bi").
5. **Recorte o print** para não mostrar trechos que ele não falou.
6. **60 a 90 s no total** (fala + tela final), ideal ~85 s. Roteiro longo: mantenha todas as notícias e corte as frases de
   orientação e repetição dentro de cada uma (ficam o gancho, o fato principal e a prova); a abertura pode virar só "Bora lá".
7. **Data:** confira se a notícia é de hoje. Pauta de IA traz notícia velha como nova.
8. Registre o que saiu e por quê na tabela de conferência do `publicacao_copy.md` e no `relatorio_cortes.json`.

## Estrutura que funciona

- **Gancho** nos primeiros 1–3 s: a pergunta/frase mais provocativa (ou a 1ª manchete já marcada). Sub-bass no 0:00.
- **Uma tag por notícia** (caixa alta, ícone SVG, sub-lettering curto) marca a troca de assunto, com whoosh. A tag nunca
  exagera o que a fonte diz.
- **Prints reais** com faixa "domínio · data" e marca-texto varrendo o trecho no instante falado (clique suave no grifo).
- **Fecho:** pergunta para os comentários (tag de CTA) + "Segue @perfil" + "FONTES: …" na tela final escura (≥ 2 s para ler).

## Prints reais com `capture.mjs`

Requisitos: `npm i puppeteer-core` na `.work` (ou um `node_modules` compartilhado) e Chrome/Chromium
(`CHROME=/caminho/do/chrome` se não for `/usr/bin/google-chrome`).

```bash
node capture.mjs jobs.json ../assets/img            # todos os jobs  -> <id>_<shot>.png + shots-all.json
node capture.mjs jobs.json ../assets/img fox        # só um job      -> shots-fox.json
python3 -I juntar_prints.py                         # junta os shots-*.json em prints.json (lido pelo make.py)
node probe.mjs URL "trecho 1" "trecho 2"            # onde o trecho está na página (tag, classe, visível?)
node para.mjs URL "trecho"                          # o parágrafo inteiro que contém o trecho (para escrever from/to/hl)
```

Cada job do `jobs.json` (exemplo em `modelos/giro-noticias/.work/jobs.exemplo.json`):

```json
{ "id": "tcg", "url": "https://...", "lang": "en-US,en;q=0.9", "hide": [".seletor-do-anuncio"], "keepPaywall": false,
  "shots": [
    { "name": "card", "from": "início do trecho", "to": "fim do trecho", "hl": ["frase a grifar"] },
    { "name": "topo", "top": true, "end": "texto onde o recorte termina", "y0": 380, "hl": ["manchete"] }
  ] }
```

Como ele trabalha: viewport de iPhone 430×932 @3x, sem aceitar cookies (banners e anúncios só são escondidos), rola a página
para carregar o texto preguiçoso, normaliza acentos (NFC) e espaço não separável, remove fixos/sticky antes do print,
recorta com margem curta (sem meia linha vizinha) e mede os grifos depois de `document.fonts.ready`.

### Dicas por tipo de site (já aconteceu)

| Situação | O que fazer |
|---|---|
| Site bloqueia automação (Cloudflare, "Undeclared Automated Tool") | print da cópia na Wayback Machine, ou de outra matéria que cite o documento |
| Site traduz sozinho para pt-BR | `"lang": "en-US,en;q=0.9"` no job |
| Fundo escuro (página de imprensa de big tech, título branco sobre cor) | classe `.dk`/`DARK` no `make.py`: grifo translúcido + sublinhado (multiply some no preto) |
| Texto carrega com atraso e some um parágrafo | job separado, rolar antes; `keepPaywall: true` quando a limpeza de paywall esconde o texto |
| Limpeza de cookie esconde a página inteira (`<html class="cookies">`, `<body class="eu-cookie-…">`, `<article class="…">`) | o `capture.mjs` já força html/body/main/article visíveis |
| Selo/anúncio por cima do texto | `"hide": [".seletor"]`; título com anúncio fixo por cima: use só um trecho do texto |
| "Continuar lendo" esconde o resto | use só o começo da matéria ou outra fonte |
| Página troca de matéria no scroll (title muda) | confira o print; o recorte sai da matéria certa |
| `shots-all.json` sobrescrito a cada rodada | rode um job por vez (3º argumento) e junte com `juntar_prints.py` |

Recorte prints em linhas inteiras (o vão entre linhas). Entre o queixo e a legenda cabe ~415 px de imagem @3x sem rolar;
print maior rola devagar (pan) ou vai para tela cheia.

## Arquivo de publicação

`final/publicacao_copy.md` (modelo em `modelos/giro-noticias/publicacao_copy.modelo.md`): legenda do post, título do
Shorts, comentário fixado, lista de fontes com link direto (deep link, não a home do site), data e hora, e a tabela
"fala × situação × fonte" com o que saiu do vídeo.
