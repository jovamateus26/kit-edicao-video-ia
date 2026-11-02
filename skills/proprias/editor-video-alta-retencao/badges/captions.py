"""
Legendas com os modelos de caption do HyperFrames (registry `caption-*`), adaptados para Reels 9:16.

Os modelos do registry são composições 1920x1080 com um texto de exemplo fixo no código. Este
módulo gera uma cópia adaptada para o vídeo:
  - troca as palavras de exemplo (WORDS / TRANSCRIPT) pelas palavras reais com tempos;
  - troca os grupos fixos (RAW_GROUPS / GROUPS) por grupos calculados a partir das palavras reais
    (parâmetros max_words / max_chars / pause vêm do estilo; sem estilo, valores técnicos de leitura);
  - ajusta DURATION / data-duration, largura máxima do texto e as variáveis de estilo PASSADAS no spec.
    Nenhuma cor, fonte ou caixa é imposta aqui: sem `vars`, o modelo roda com os valores originais dele;
  - monta como sub-composição escalada e ancorada na faixa da legenda (base em y≈1640 de 1920).

Modelos de LEGENDA CONTÍNUA (carregam o texto todo):
  caption-pill-karaoke, caption-highlight, caption-clip-wipe, caption-particle-burst,
  caption-neon-glow, caption-gradient-fill, caption-matrix-decode, caption-neon-accent,
  caption-emoji-pop, caption-weight-shift, caption-glitch-rgb
Modelos de DESTAQUE (frase única, momento de pico — use como card, não como trilha):
  caption-kinetic-slam, caption-texture, caption-camera-follow, caption-editorial-emphasis,
  caption-parallax-layers (precisa de recorte), mk-callout-highlight (block)
"""
import json
import os
import re

SHOWCASE = os.path.expanduser("~/Projetos/hyperframes-showcase")

CONTINUOUS = {
    # nome: (padrão de dados, descrição pt-BR)
    "caption-pill-karaoke": ("transcript", "Pílula com karaokê por palavra; cores ativa/inativa e fonte via vars."),
    "caption-highlight": ("raw_groups", "Fundo que varre a palavra ativa; cor do fundo via vars."),
    "caption-clip-wipe": ("raw_groups", "Cada palavra revelada por wipe da esquerda para a direita."),
    "caption-particle-burst": ("raw_groups", "Palavras-chave se desfazem em partículas."),
    "caption-neon-glow": ("groups", "Texto com brilho (glow) e palavras-chave destacadas; cores via vars."),
    "caption-gradient-fill": ("groups", "Texto com preenchimento em gradiente e entrada elástica."),
    "caption-matrix-decode": ("groups", "Letras embaralhadas antes de revelar a palavra."),
    "caption-neon-accent": ("transcript", "Acentos luminosos multicor nas palavras-chave, com leve deriva."),
    "caption-emoji-pop": ("transcript", "Texto com contorno e entrada espremida (emoji opcional)."),
    "caption-weight-shift": ("transcript", "Transição de peso da fonte entre linhas."),
    "caption-glitch-rgb": ("transcript", "Aberração RGB com scanlines."),
}
HERO_ONLY = {
    "caption-kinetic-slam": "Uma palavra por vez em tela cheia, entradas alternadas (pico/abertura).",
    "caption-texture": "Palavras grandes com textura (lava, mármore, metal...) — título de impacto.",
    "caption-camera-follow": "Uma frase escrita num 'mundo' maior que a tela, câmera seguindo.",
    "caption-editorial-emphasis": "Duas fontes com contraste dramático de tamanho (frase-tese).",
    "caption-parallax-layers": "Texto 3D atrás do assunto (exige recorte/matting).",
    "mk-callout-highlight": "Frase com destaque palavra a palavra guiado por um escalar (block).",
}

# Sem modelo nem variáveis padrão: o modelo, as cores, a fonte e a caixa vêm do estilo (prompt / estilo.json).
DEFAULT_MODEL = None
DEFAULT_GROUP = {"max_words": 3, "max_chars": 20, "pause": 0.35}  # limites técnicos de leitura; o estilo pode trocar


# ───────────────────────── palavras ─────────────────────────
def load_words(path):
    """Aceita transcript.json do HyperFrames ([{text,start,end}]), palavras.json da skill ou legendas.ass (karaokê)."""
    if path.endswith(".ass"):
        return words_from_ass(path)
    data = json.load(open(path, encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("words") or data.get("transcript") or []
    out = []
    for w in data:
        t = str(w.get("text") or w.get("word") or "").strip()
        if t:
            out.append({"text": t, "start": round(float(w["start"]), 3), "end": round(float(w["end"]), 3)})
    return out


def _ass_time(s):
    h, m, rest = s.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def words_from_ass(path):
    """Reconstrói palavras com tempo a partir do karaokê da skill (uma linha Dialogue por palavra ativa)."""
    words = []
    for line in open(path, encoding="utf-8"):
        if not line.startswith("Dialogue:"):
            continue
        parts = line.rstrip("\n").split(",", 8)  # Layer,Start,End,Style,Name,MarginL,MarginR,Effect,Text
        start, end, text = _ass_time(parts[1]), _ass_time(parts[2]), parts[8].split(",,")[-1] if parts[8].startswith(",") else parts[8]
        m = re.search(r"\{\\c&H0000EAFF&\}(.+?)\{\\c&H00FFFFFF&\}", text)
        if not m:
            continue
        w = {"text": m.group(1).strip(), "start": round(start, 3), "end": round(end, 3)}
        # junta a mesma palavra repetida em linhas contíguas (correções manuais no .ass)
        if words and words[-1]["text"] == w["text"] and abs(words[-1]["end"] - w["start"]) < 0.06:
            words[-1]["end"] = w["end"]
            continue
        words.append(w)
    return words


def group_words(words, max_words=3, max_chars=20, pause=0.35):
    groups, cur = [], []
    for i, w in enumerate(words):
        cand = cur + [i]
        chars = len(" ".join(words[j]["text"] for j in cand))
        if cur and (len(cand) > max_words or chars > max_chars):
            groups.append((cur[0], cur[-1]))
            cand = [i]
        cur = cand
        nxt = words[i + 1] if i + 1 < len(words) else None
        if nxt is None or re.search(r"[.,!?:;]$", w["text"]) or (nxt["start"] - w["end"]) >= pause:
            groups.append((cur[0], cur[-1]))
            cur = []
    if cur:
        groups.append((cur[0], cur[-1]))
    return groups


# ───────────────────────── adaptação ─────────────────────────
def find_model(name, project=None):
    cands = []
    if project:
        cands += [os.path.join(project, "public", "compositions", "components", f"{name}.html"),
                  os.path.join(project, "public", "compositions", f"{name}.html")]
    cands += [os.path.join(SHOWCASE, "components", name, f"{name}.html"), os.path.join(SHOWCASE, "blocks", name, f"{name}.html")]
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def _replace_array(src, var, new_literal):
    """Troca `var NAME = [ ... ];` (colchetes balanceados) por um novo literal."""
    m = re.search(rf"\b(var|let|const)\s+{var}\s*=\s*\[", src)
    if not m:
        return src, False
    i = m.end() - 1
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "[":
            depth += 1
        elif src[j] == "]":
            depth -= 1
            if depth == 0:
                return src[:i] + new_literal + src[j + 1:], True
    return src, False


def _set_var(src, name, value):
    lit = json.dumps(value) if isinstance(value, str) else str(value)
    new, n = re.subn(rf"(\b(?:var|let|const)\s+{name}\s*=\s*)[^;]+;", lambda m: m.group(1) + lit + ";", src, count=1)
    return new, n > 0


def adapt(name, words, duration, scale=0.75, max_text_px=1000, keywords=(), variables=None, project=None, fps=30,
          case="original", group=None, extra_css=""):
    path = find_model(name, project)
    if not path:
        raise FileNotFoundError(f"Modelo de legenda '{name}' não encontrado. Baixe: npx hyperframes add {name} --dir <projeto>/public")
    src = open(path, encoding="utf-8").read()
    pattern = CONTINUOUS.get(name, ("hero", ""))[0]
    g = {**DEFAULT_GROUP, **(group or {})}
    groups = group_words(words, max_words=int(g["max_words"]), max_chars=int(g["max_chars"]), pause=float(g["pause"]))
    words_lit = json.dumps(words, ensure_ascii=False)
    for var in ("TRANSCRIPT", "WORDS"):
        src, ok = _replace_array(src, var, words_lit)
        if ok and var == "TRANSCRIPT":
            break
    if pattern == "raw_groups" or "RAW_GROUPS = [" in src:
        src, _ = _replace_array(src, "RAW_GROUPS", json.dumps([list(g) for g in groups]))
    if pattern == "groups":
        glist = []
        for gi, (a, b) in enumerate(groups):
            nxt = words[groups[gi + 1][0]]["start"] if gi + 1 < len(groups) else duration
            glist.append({"wordStart": a, "wordEnd": b, "start": words[a]["start"],
                          "end": round(min(words[b]["end"] + 0.5, nxt - 0.05), 3)})
        src, _ = _replace_array(src, "GROUPS", json.dumps(glist))
    # palavras-chave: índices (Set([8,12])) ou textos (Set(["html"]))
    kw = [k.lower() for k in keywords]
    idx = [i for i, w in enumerate(words) if re.sub(r"[^\wÀ-ú]", "", w["text"].lower()) in kw]
    src = re.sub(r"new Set\(\[\s*\d[\d,\s]*\]\)", f"new Set({json.dumps(idx)})", src)
    src = re.sub(r'new Set\(\[\s*"[^\]]*\]\)', f"new Set({json.dumps(kw, ensure_ascii=False)})", src)
    # duração
    src = re.sub(r'data-duration="[\d.]+"', f'data-duration="{duration}"', src, count=1)
    src, _ = _set_var(src, "DURATION", duration)
    src = re.sub(r"\]\]\.start\s*:\s*8(\.0)?\s*;", f"]].start : {duration};", src)
    src = re.sub(r"\]\[0\]\]\.start\s*:\s*8(\.0)?", f"][0]].start : {duration}", src)
    # largura máxima do texto (no canvas 1920) para caber em max_text_px na tela 1080
    canvas_max = int(max_text_px / scale)
    src = re.sub(r"(fitFontSize\([^;]*?,\s*)(\d{4})(\s*\))", lambda m: m.group(1) + str(canvas_max) + m.group(3), src)
    for wv in ("SAFE_ZONE_WIDTH", "PILL_MAX_WIDTH", "MAX_LINE_WIDTH", "LINE_MAX_WIDTH"):
        src, _ = _set_var(src, wv, canvas_max)
    # variáveis de estilo: só as que o spec passar (nenhum valor imposto pela skill)
    if "MAX_WORDS_PER_GROUP" not in (variables or {}):
        src, _ = _set_var(src, "MAX_WORDS_PER_GROUP", int(g["max_words"]))
    for k, v in (variables or {}).items():
        src, _ = _set_var(src, k, v)
    # caixa do texto: "original" mantém o modelo; upper/lower trocam no JS (medição + render ficam coerentes)
    if case == "upper":
        src = src.replace(".toLowerCase()", ".toUpperCase()")
    elif case == "lower":
        src = src.replace(".toUpperCase()", ".toLowerCase()")
    if extra_css:
        src = src.replace("</style>", "\n" + extra_css + "\n</style>", 1)
    return src, groups


def bottom_anchor(src):
    """y (no canvas 1080) da base do texto do modelo, lido do primeiro `bottom: Npx` do CSS."""
    m = re.search(r"bottom:\s*(\d+)px", src)
    return 1080 - int(m.group(1)) if m else 960


def mount_html(name, src, duration, canvas_w=1080, canvas_h=1920, scale=0.75, baseline_y=1640, track=6):
    w, h = round(1920 * scale), round(1080 * scale)
    left = round((canvas_w - w) / 2)
    top = round(baseline_y - bottom_anchor(src) * scale)
    return (f'<div id="captions-host" class="clip" data-composition-id="{name}" data-composition-src="compositions/captions.html" '
            f'data-start="0" data-duration="{duration}" data-track-index="{track}" data-width="1920" data-height="1080" '
            f'style="position:absolute;left:{left}px;top:{top}px;width:1920px;height:1080px;'
            f'transform:scale({scale});transform-origin:0 0;z-index:50;"></div>')
