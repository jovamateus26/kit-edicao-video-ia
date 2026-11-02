"""Legenda revisada (pt-BR) alinhada às palavras do whisper na fala editada -> data.json

Entrada: transcript_edit.json (transcribe_edit.py sobre audio/edit.wav). O texto revisado abaixo é a fonte da verdade;
os tempos vêm do whisper por alinhamento de sequência (difflib). Palavra-chave em menta: prefixo '*'.
Uso: python3 -I captions.py
"""
import difflib, json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
TEXT = """
Frase do *gancho | com a *palavra-chave. |
Segunda frase | da *notícia. |
"""


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


raw_toks = TEXT.split()
BREAK = set()  # '|' força quebra de grupo antes da próxima palavra
toks = []
for t in raw_toks:
    if t == "|":
        BREAK.add(len(toks))
    else:
        toks.append(t)
ws = [w for seg in json.load(open(os.path.join(W, "transcript_edit.json"))) for w in seg["words"]]
# whisper escreve "70%" como "70" "%": junta símbolos soltos na palavra anterior
wl = []
for w in ws:
    if wl and norm(w["w"]) == "" and w["w"].strip():
        wl[-1]["e"] = w["e"]
        continue
    wl.append(dict(w))
A = [norm(t) for t in toks]
B = [norm(w["w"]) for w in wl]
times = [None] * len(toks)
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
        for k in range(i2 - i1):
            times[i1 + k] = (wl[j1 + k]["s"], wl[j1 + k]["e"])
    elif tag == "replace":  # n palavras do texto <-> m do whisper: reparte o intervalo
        s0, e0 = wl[j1]["s"], wl[j2 - 1]["e"]
        for k in range(i2 - i1):
            times[i1 + k] = (s0 + (e0 - s0) * k / (i2 - i1), s0 + (e0 - s0) * (k + 1) / (i2 - i1))
        print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "delete":
        print("  sem tempo:", " ".join(toks[i1:i2]))
# preenche faltas por interpolação
for i, t in enumerate(times):
    if t is None:
        p = next(times[k] for k in range(i - 1, -1, -1) if times[k])
        n = next((times[k] for k in range(i + 1, len(times)) if times[k]), (p[1] + 0.3, p[1] + 0.6))
        times[i] = (p[1], max(p[1] + 0.05, n[0]))

segs = json.load(open(os.path.join(W, "segs.json")))
DUR = segs["duration"]
words = [{"w": t, "t": round(s, 3), "e": round(e, 3), "brk": i in BREAK} for i, (t, (s, e)) in enumerate(zip(toks, times))]

# grupos: quebra em pontuação, gap > 0.6 s, máx. 3 palavras / 18 caracteres
groups, cur = [], []
def text_of(g): return " ".join(x["w"].lstrip("*") for x in g)
for tk in words:
    if cur:
        gap = tk["t"] - cur[-1]["e"]
        if tk["brk"] or cur[-1]["w"][-1] in ".,?!:" or gap > 0.6 or len(cur) >= 3 or len(text_of(cur + [tk])) > 18:
            groups.append(cur); cur = []
    cur.append(tk)
groups.append(cur)
CAPS = []
for gi, g in enumerate(groups):
    t0 = max(0.0, g[0]["t"] - 0.04)
    nxt = groups[gi + 1][0]["t"] - 0.04 if gi + 1 < len(groups) else DUR
    t1 = min(nxt, g[-1]["e"] + 0.5)
    CAPS.append({"t0": round(t0, 3), "t1": round(t1, 3),
                 "w": [{"x": x["w"].lstrip("*").rstrip(".,?!:"), "k": x["w"].startswith("*"), "t": x["t"]} for x in g]})
json.dump({"caps": CAPS, "words": words, "dur": DUR}, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
# palavras.json (transcript HyperFrames) e SRT para entrega
json.dump([{"text": w["w"].lstrip("*"), "start": w["t"], "end": w["e"]} for w in words],
          open(os.path.join(W, "palavras.json"), "w"), ensure_ascii=False, indent=1)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} " + " ".join(("*" if w["k"] else "") + w["x"] for w in c["w"]))
print("dur", DUR, "grupos", len(CAPS))
