"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> wh edit -> captions.py -> make.py mantém tudo sincronizado.
Uso: python3 -I make.py
"""
import json, os

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
DUR = data["dur"]

# início e fim de cada item da EDL na fala editada
first, last = {}, {}
for s in segs:
    first.setdefault(s["edl"], s["out"])
    last[s["edl"]] = round(s["out"] + s["dur"], 3)

flat = [(w["x"].lower(), w["t"]) for g in data["caps"] for w in g["w"]]


def at(word, nth=1, after=-1.0):
    hits = [t for x, t in flat if x == word.lower() and t > after]
    if len(hits) < nth:
        raise SystemExit(f"palavra não encontrada: {word} #{nth} depois de {after}")
    return round(hits[nth - 1], 3)


# ---------- câmera: punch-in alternado em corte dentro do mesmo clipe; timelapse sem zoom ----------
cam, prev, z = [], None, 1.0
for s in segs:
    if s.get("speed", 1.0) != 1.0 or s["src"] != prev:
        z = 1.0
    else:
        z = 1.0 if z > 1.0 else (1.06 if s["src"] == "3311" else 1.08)
    cam.append([round(s["out"], 3), z])
    prev = s["src"]

# ---------- selo de etapa (os cards carregam o 05 e o 07) ----------
PILLS = [((7, 8), "01", "HD EXTERNO"), ((9,), "02", "BIOS"), ((10,), "03", "SECURE BOOT · OFF"),
         ((11,), "04", "BOOT PELO VENTOY"), ((17, 18), "06", "BOOT · 5× MAIS RÁPIDO"), ((22, 23), "08", "INSTALANDO O UBUNTU"),
         ((26, 29), "", "PARTE 1 · SERVIDOR 02"), ((30, 32), "", "PARTE 2 EM BREVE")]
pills = [{"t0": first[e[0]], "t1": last[e[-1]]} for e, _, _ in PILLS]
pill_dom = "\n".join(
    f'        <div class="pill" id="pl{i}"><span class="dot"></span>' + (f'<span class="n">{n}</span>' if n else "") + f"{txt}</div>"
    for i, (_, n, txt) in enumerate(PILLS))

cues = {"hook2": 0.55, "specs": round(first[3] + 0.05, 3), "disk": at("32"), "ram": at("4"),
        "os": round(first[12] + 0.05, 3), "strike": at("computador"), "ubuntu": at("ubuntu"),
        "host": round(first[19] + 0.05, 3), "serie": at("01"),
        "err": round(first[24] + 0.05, 3), "algo": at("algo"),
        "follow": round(first[31] + 0.05, 3)}

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    sp = "".join(f'<span class="cw{" k" if w["k"] else ""}{" r" if w["r"] else ""}" id="w{gi}_{wi}">{w["x"]}</span>'
                 for wi, w in enumerate(g["w"]))
    caps_dom.append(f'          <div class="cg" id="g{gi}">{sp}</div>')

# ---------- SFX (poucos e baixos) ----------
SFX_DUR = {"whoosh-short": 0.57, "whoosh": 0.57, "click-soft": 0.37, "click": 0.37, "pop": 0.72, "ping": 1.32, "glitch-1": 1.0}
sfx = [(0.0, "glitch-1", 0.26), (cues["algo"], "glitch-1", 0.3)]
sfx += [(first[e], "whoosh-short", 0.16) for e in (7, 9, 19, 24, 26)]
sfx += [(first[17], "whoosh", 0.2), (first[18] + 0.05, "ping", 0.14)]
sfx += [(cues["specs"], "pop", 0.16), (cues["disk"], "click-soft", 0.2), (cues["ram"], "click-soft", 0.2)]
sfx += [(first[10], "click-soft", 0.18), (first[11], "click-soft", 0.18), (first[22], "click-soft", 0.18)]
sfx += [(cues["os"], "pop", 0.16), (cues["strike"], "click", 0.18), (cues["ubuntu"], "pop", 0.18)]
sfx += [(cues["serie"], "click-soft", 0.2), (first[30], "pop", 0.18), (cues["follow"], "pop", 0.2)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "pills": pills, "cues": cues, "caps": data["caps"]}
r = lambda v: f"{v:.3f}"
fill = {
    "%%DUR%%": r(DUR),
    "%%HOOK_D%%": r(first[4]),
    "%%SPECS_S%%": r(first[3]), "%%SPECS_D%%": r(last[6] - first[3]),
    "%%OS_S%%": r(first[12]), "%%OS_D%%": r(last[16] - first[12]),
    "%%HOST_S%%": r(first[19]), "%%HOST_D%%": r(last[21] - first[19]),
    "%%ERR_S%%": r(first[24]), "%%ERR_D%%": r(last[25] - first[24]),
    "%%FOL_S%%": r(cues["follow"]), "%%FOL_D%%": r(DUR - cues["follow"]),
    "%%PILLS%%": pill_dom,
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "\ncues", cues, "\npills", pills)
print("cam", cam)
