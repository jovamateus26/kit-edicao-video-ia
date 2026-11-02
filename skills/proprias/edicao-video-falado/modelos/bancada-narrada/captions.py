"""Legenda revisada (pt-BR) a partir de transcript_edit.json (whisper na fala montada) + segs.json -> data.json

Palavra-chave em menta: prefixo '*'. Prefixo '!' pinta de vermelho (erro, problema, travou).
  python3 -I captions.py
"""
import json, os

W = os.path.dirname(os.path.abspath(__file__))
words = json.load(open(os.path.join(W, "transcript_edit.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
DUR = round(segs[-1]["out"] + segs[-1]["dur"], 3)

# correções por índice de palavra (None apaga); inserções depois do índice: [(texto, tempo)]
FIX = {}   # POR EPISÓDIO: correções por índice de palavra, ex.: {12: "*palavra", 25: None (apaga)}
INS = {}   # POR EPISÓDIO: inserções antes do índice, ex.: {78: [("palavra", 26.25)]}
SHIFT = {}   # POR EPISÓDIO: tempo corrigido de uma palavra, ex.: {131: 45.32}
CONT = {1, 2, 4, 5, 6, 13, 14, 16, 20, 21, 28, 29, 31}   # itens da EDL que continuam a frase do anterior


def seg_of(t):
    return max(i for i, s in enumerate(segs) if s["out"] <= t + 0.13)


toks = []
for i, w in enumerate(words):
    txt = FIX.get(i, w["w"])
    if txt is not None:
        t = SHIFT.get(i, w["s"])
        toks.append({"w": txt, "t": t, "seg": seg_of(t)})
    for txt, t in INS.get(i, []):
        toks.append({"w": txt, "t": t, "seg": seg_of(t)})
toks.sort(key=lambda x: x["t"])
for tk in toks:
    e = segs[tk["seg"]]["edl"]
    while e in CONT:
        e -= 1
    tk["edl"] = e


def bare(x):
    return x.lstrip("*!")


def text_of(g):
    return " ".join(bare(x["w"]) for x in g)


# grupos: quebra em pontuação, gap > 0,8 s, troca de item da EDL, máx. 3 palavras / 18 caracteres
groups, cur = [], []
for tk in toks:
    if cur:
        gap = tk["t"] - cur[-1]["t"]
        if (cur[-1]["w"][-1] in ".,?!:" or gap > 0.8 or len(cur) >= 3 or tk["edl"] != cur[-1]["edl"]
                or len(text_of(cur + [tk])) > 18):
            groups.append(cur); cur = []
    cur.append(tk)
groups.append(cur)

# leitura: artigo/preposição no fim da linha desce para a próxima ("no boot | do Windows"), "4 | GB" fica junto,
# e token curto sozinho ("o", "26", "PC") gruda no vizinho — sempre dentro de 4 palavras / 18 caracteres
FUNC = {"a", "o", "as", "os", "um", "de", "do", "da", "no", "na", "pra", "e"}


def fits(g):
    return len(g) <= 4 and len(" ".join(bare(x["w"]).rstrip(".,?!:") for x in g)) <= 18


changed = True
while changed:
    changed = False
    for i in range(len(groups) - 1):
        g, h = groups[i], groups[i + 1]
        if len(g) > 1 and g[-1]["w"][-1] not in ".,?!:" and (bare(g[-1]["w"]).lower() in FUNC or bare(h[0]["w"]) == "GB") \
                and fits([g[-1]] + h):
            h.insert(0, g.pop()); changed = True
        elif len(g) == 1 and len(bare(g[0]["w"]).rstrip(".,?!:")) <= 2 and g[0]["w"][-1] not in ".,?!:" and fits(g + h):
            groups[i + 1] = g + h; groups[i] = []; changed = True
        elif len(h) == 1 and len(bare(h[0]["w"]).rstrip(".,?!:")) <= 3 and g[-1]["w"][-1] not in ".,?!:" and fits(g + h):
            groups[i] = g + h; groups[i + 1] = []; changed = True
    groups = [g for g in groups if g]

CAPS = []
for gi, g in enumerate(groups):
    t0 = max(0.0, g[0]["t"] - 0.04)
    nxt = groups[gi + 1][0]["t"] - 0.04 if gi + 1 < len(groups) else DUR
    t1 = DUR if gi + 1 == len(groups) else min(nxt, g[-1]["t"] + 1.1, DUR)
    CAPS.append({"t0": round(t0, 3), "t1": round(t1, 3),
                 "w": [{"x": bare(x["w"]).rstrip(".,?!:") if not bare(x["w"]).endswith(("?", "!")) else bare(x["w"]),
                        "k": x["w"].startswith("*"), "r": x["w"].startswith("!"), "t": round(x["t"], 3)} for x in g]})

data = {"caps": CAPS, "dur": DUR, "cuts": [round(s["out"], 3) for s in segs][1:]}
json.dump(data, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} " + " ".join(("*" if w["k"] else "") + ("!" if w["r"] else "") + w["x"] for w in c["w"]))
print("dur", DUR, "grupos", len(CAPS))
