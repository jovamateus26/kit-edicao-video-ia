# Contrato de estilo (`estilo.json`)

A skill não decide nada estético. Toda decisão visual chega por **uma** destas fontes, nesta ordem de precedência:

1. **O prompt da conversa** (ex.: "legenda caption-highlight em caixa baixa, sem badges, cor cinematic").
2. **Flags da linha de comando** (`--color`, `--legenda-modelo`, `--broll`).
3. **`estilo.json`** na pasta do projeto, ou o arquivo passado em `--estilo` (ex.: um preset salvo em `referencias/estilos-exemplo/`).
4. **Nada definido**: o pipeline só faz o técnico (veja "Comportamento neutro" abaixo).

Quando o prompt descreve o estilo em palavras, o agente o traduz para um `estilo.json` na pasta do projeto antes de rodar, e mostra o arquivo ao usuário. Os nomes dos modelos devem existir no inventário (`referencias/ferramentas.md`, `referencias/catalogo_hyperframes.md`).

## Esquema

Todos os campos são opcionais. Campo ausente = a skill não aplica nada naquele aspecto.

```jsonc
{
  "nome": "meu-estilo",                       // rótulo livre
  "cor":    { "preset": "none|studio|vibrant|cinematic|warm", "lut": "caminho/arquivo.cube" },
  "broll":  { "modo": "none|manual|auto",     // manual = só mídias da pasta; auto = local + gflow
              "duracao": 2.5,                 // segundos por inserção
              "zoom_max": 1.0,                // 1.0 = imagem parada; >1 = Ken Burns até esse zoom
              "dissolve": 0.2,                // dissolvência nas bordas (0 = corte seco)
              "prompt_sufixo": "..." },       // estética anexada ao prompt do gflow (texto livre)
  "legenda": {
    "modelo": "caption-...",                  // qualquer modelo de legenda do inventário; sem isto, não há versão legendada
    "vars":   { "COLOR_ACTIVE": "#...", "FONT_FAMILY": "..." },   // constantes do modelo (veja o topo do HTML dele)
    "case":   "original|upper|lower",
    "group":  { "max_words": 3, "max_chars": 20, "pause": 0.35 }, // agrupamento das palavras
    "keywords": ["termo"],                    // palavras destacadas (nos modelos que suportam)
    "scale": 0.75, "baseline_y": 1640, "max_text_px": 1000,       // geometria no quadro 1080×1920
    "css": "...",                             // CSS extra injetado no modelo
    "ass": { "font": "Arial", "size": 46, "primary": "&H00FFFFFF", "active": "&H00RRGGBB" | null,
             "outline": 3, "shadow": 0, "bold": 0, "case": "original", "margin_v": 300 }  // só para o fallback ASS
  },
  "badges": { "vars": { "--glass": "...", "--ink": "...", "--font-sans": "...", "--font-mono": "..." },
              "css": "...",                   // CSS extra para os modelos do kit
              "legibility": false,            // véu de gradiente topo/base atrás dos badges
              "legibility_css": "background: ..." },
  "motion": { "in":  { "x": 120, "y": 0, "blur": 12, "duration": 0.5,  "ease": "power4.out" },
              "out": { "x": -120, "y": 0, "blur": 12, "duration": 0.32, "ease": "power4.in" } },
  "embedded_captions": { "identidade": "anchor|ink|..." },   // quando usar /embedded-captions
  "restricoes": ["texto livre: o que NÃO pode aparecer"],
  "referencias": ["links ou arquivos de referência visual"]
}
```

Tokens de cor do kit de badges que podem ser sobrescritos: `--cyan --green --amber --red --violet --blue --ink --muted --glass --edge --font-sans --font-mono`.

## Comportamento neutro (nada definido)

| Aspecto | O que acontece |
|---|---|
| Cor | `none`: imagem original, só o recorte/escala do formato |
| B-roll | `none`: nenhum asset inserido |
| Legenda | `palavras.json` + `legendas.srt` gerados; **sem** `final_com_legenda.mp4`. O agente pergunta qual modelo usar |
| Badges / motion | nenhum. Só entram quando o prompt pedir |
| Copy | `publicacao_copy.md` com palavras-chave + transcrição; o texto final segue o tom do prompt |

O agente não escolhe estilo por nicho, assunto ou "gosto". Se o prompt deixar uma decisão em aberto, ele lista as opções do inventário e pergunta. Se o usuário disser "tanto faz" ou "escolha você", o agente propõe uma opção e explica por que, sem aplicar antes da confirmação.

## Exemplos salvos

`referencias/estilos-exemplo/*.json` são estilos já usados, guardados para reuso **quando o prompt pedir** (ex.: "use o estilo reel3-sailfish"). Nenhum deles é padrão.
