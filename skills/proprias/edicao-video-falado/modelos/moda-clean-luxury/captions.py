"""Legenda revisada (pt-BR) alinhada às palavras do whisper na fala editada -> data.json

Entrada: transcript_edit.json (_pipeline/wh edit sobre segs/cat.wav). O texto abaixo é a fonte da verdade; os tempos vêm
do whisper por alinhamento de sequência (difflib).
Marcas: '|' fecha o bloco, '/' quebra a linha dentro do bloco (máx. 2 linhas, 3-5 palavras), '*palavra' = destaque
champanhe, '#' no começo do bloco = título (bloco grande, ex.: NOVIDADES DA SEMANA).
Uso: python3 -I captions.py
"""
import difflib, json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
TEXT = """
# TÍTULO DO VÍDEO |
Frase de / *abertura |
que continua / na *segunda linha. |
"""


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


blocks = []                                     # [{"big": bool, "lines": [[token, ...], ...]}]
for raw in TEXT.split("|"):
    raw = raw.strip()
    if not raw:
        continue
    big = raw.startswith("#")
    raw = raw.lstrip("#").strip()
    blocks.append({"big": big, "lines": [ln.split() for ln in raw.split("/")]})
toks = [t for b in blocks for ln in b["lines"] for t in ln]

TR = json.load(open(os.path.join(W, "transcript_edit.json")))   # wh edit: lista de palavras {w, s, e, p, src}
wl = [w for seg in TR for w in seg["words"]] if TR and "words" in TR[0] else TR
A = [norm(t) for t in toks]
B = [norm(w["w"]) for w in wl]
times = [None] * len(toks)
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
        for k in range(i2 - i1):
            times[i1 + k] = (wl[j1 + k]["s"], wl[j1 + k]["e"])
        if tag == "replace":
            print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "replace":  # n palavras do texto <-> m do whisper: reparte o intervalo
        s0, e0 = wl[j1]["s"], wl[j2 - 1]["e"]
        for k in range(i2 - i1):
            times[i1 + k] = (s0 + (e0 - s0) * k / (i2 - i1), s0 + (e0 - s0) * (k + 1) / (i2 - i1))
        print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "delete":
        print("  sem tempo:", " ".join(toks[i1:i2]))
    elif tag == "insert":
        print("  só no whisper:", " ".join(w["w"] for w in wl[j1:j2]))
for i, t in enumerate(times):                   # faltas: interpolação
    if t is None:
        p = next(times[k] for k in range(i - 1, -1, -1) if times[k])
        n = next((times[k] for k in range(i + 1, len(times)) if times[k]), (p[1] + 0.3, p[1] + 0.6))
        times[i] = (p[1], max(p[1] + 0.05, n[0]))
for i in range(1, len(times)):                  # palavras coladas pelo whisper: no mínimo 0,1 s cada
    if times[i][0] < times[i - 1][0] + 0.1:
        s0 = times[i - 1][0] + 0.1
        times[i] = (s0, max(times[i][1], s0 + 0.1))

segs = json.load(open(os.path.join(W, "segs.json")))
SPEECH = segs["duration"]
words, CAPS, k = [], [], 0
for b in blocks:
    lines = []
    for ln in b["lines"]:
        out = []
        for tok in ln:
            s, e = times[k]
            words.append({"w": tok, "t": round(s, 3), "e": round(e, 3)})
            out.append({"x": tok.lstrip("*").rstrip(".,"), "k": tok.startswith("*"), "t": round(s, 3)})   # sem ponto/vírgula na tela
            k += 1
        lines.append(out)
    CAPS.append({"big": b["big"], "lines": lines, "t0": round(max(0.0, lines[0][0]["t"] - 0.04), 3),
                 "e": round(times[k - 1][1], 3)})
for i, c in enumerate(CAPS):
    nxt = CAPS[i + 1]["t0"] if i + 1 < len(CAPS) else SPEECH
    c["t1"] = round(min(nxt, c.pop("e") + 0.5), 3)
json.dump({"caps": CAPS, "words": words, "speech": SPEECH}, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} {'#' if c['big'] else ' '} " +
          " / ".join(" ".join(("*" if w["k"] else "") + w["x"] for w in ln) for ln in c["lines"]))
print("fala", SPEECH, "blocos", len(CAPS))
