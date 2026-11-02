"""Legenda revisada (pt-BR) + palavras da voz de IA (karaokê do player) + ondas sonoras -> data.json

Entrada: words_fala.json (mapwords.py), assets/footage/fala.mp4. Trechos da voz de IA (segs 0, 14-16 da EDL) saem
da legenda comum e viram o texto do player. Palavra-chave em menta: prefixo '*'.
"""
import json, os, subprocess
import numpy as np

W = os.path.dirname(os.path.abspath(__file__))
words = json.load(open(os.path.join(W, "words_fala.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
AI_EDL = {0, 14}  # índices da EDL com a voz gerada
ai_segs = {i for i, s in enumerate(segs) if s["edl"] in AI_EDL}

# correções por índice de palavra (None apaga); inserções (antes do índice): [(texto, tempo)]
FIX = {}   # POR EPISÓDIO: correções por índice de palavra, ex.: {12: "*palavra", 25: None (apaga)}
INS = {}   # POR EPISÓDIO: inserções antes do índice, ex.: {78: [("palavra", 26.25)]}
SHIFT = {}   # POR EPISÓDIO: tempo corrigido de uma palavra, ex.: {131: 45.32}

toks = []
for i, w in enumerate(words):
    if words[i]["seg"] in ai_segs:
        continue
    for txt, t in INS.get(i, []):
        toks.append({"w": txt, "t": t if t is not None else round(w["t"] - 0.12, 3), "seg": w["seg"]})
    txt = FIX.get(i, w["w"])
    if txt is None:
        continue
    toks.append({"w": txt, "t": SHIFT.get(i, w["t"]), "seg": w["seg"]})
toks.sort(key=lambda x: x["t"])

# grupos: quebra em pontuação, gap > 0.35 s, máx. 3 palavras / 17 caracteres
groups, cur = [], []
def text_of(g): return " ".join(x["w"].lstrip("*") for x in g)
for k, tk in enumerate(toks):
    if cur:
        gap = tk["t"] - cur[-1]["t"]
        if (cur[-1]["w"][-1] in ".,?!:" or gap > 0.8 or len(cur) >= 3 or tk["seg"] != cur[-1]["seg"]
                or len(text_of(cur + [tk])) > 17):
            groups.append(cur); cur = []
    cur.append(tk)
groups.append(cur)

AI_TIMES = [(segs[i]["out"], segs[i]["out"] + segs[i]["dur"]) for i in sorted(ai_segs)]
def in_ai(t): return any(a - 0.05 <= t < b for a, b in AI_TIMES)
CAPS = []
for gi, g in enumerate(groups):
    t0 = g[0]["t"] - 0.04
    nxt = groups[gi + 1][0]["t"] - 0.04 if gi + 1 < len(groups) else 63.53
    t1 = min(nxt, g[-1]["t"] + 1.1)
    # não invade os trechos de IA
    for a, b in AI_TIMES:
        if t0 < a < t1:
            t1 = a
    CAPS.append({"t0": round(t0, 3), "t1": round(t1, 3),
                 "w": [{"x": x["w"].lstrip("*").rstrip(".,?!:"), "k": x["w"].startswith("*"), "t": round(x["t"], 3)} for x in g]})

# voz de IA: palavras (karaokê) por trecho
lines = []
for i in sorted(ai_segs):
    for w in words:
        if w["seg"] == i:
            x = w["w"]
            if x == "a" and w["t"] > 30 and w["t"] < 37:  # correção de nome próprio que o whisper errou (ex.: "a unir Satyr" -> "Nome Artista")
                continue
            x = {"FM.": "FM!", "Satyr.": "Artista,", "unir": "Nome", "E": "e"}.get(x, x)
            lines.append({"x": x, "t": round(w["t"], 3), "seg": i})

# ondas: envelope RMS do áudio editado nos trechos de IA (barras)
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(W, "..", "assets", "footage", "fala.mp4"), "-f", "f32le",
                      "-ac", "1", "-ar", "16000", "-"], capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
def bars(a, b, n):
    seg = x[int(a * 16000):int(b * 16000)]
    ch = np.array_split(seg, n)
    r = np.array([np.sqrt(np.mean(c ** 2)) for c in ch])
    r = r / (r.max() + 1e-9)
    return [round(float(max(0.06, v ** 0.7)), 3) for v in r]
ai1 = (segs[min(ai_segs)]["out"], segs[min(ai_segs)]["out"] + segs[min(ai_segs)]["dur"])
ai2s = sorted(i for i in ai_segs if i != min(ai_segs))
ai2 = (segs[ai2s[0]]["out"], segs[ai2s[-1]]["out"] + segs[ai2s[-1]]["dur"])
data = {"caps": CAPS, "ai_words": lines, "ai1": [round(v, 3) for v in ai1], "ai2": [round(v, 3) for v in ai2],
        "bars1": bars(*ai1, 48), "bars2": bars(*ai2, 48),
        "cuts": [round(s["out"], 3) for s in segs][1:], "dur": round(segs[-1]["out"] + segs[-1]["dur"], 3)}
json.dump(data, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} " + " ".join(("*" if w["k"] else "") + w["x"] for w in c["w"]))
print("AI:", " ".join(f"{w['x']}@{w['t']}" for w in lines))
print("ai1", data["ai1"], "ai2", data["ai2"], "dur", data["dur"])
