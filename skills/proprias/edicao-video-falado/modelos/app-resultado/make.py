"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> fillers.py -> captions.py -> make.py mantém tudo sincronizado.
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

MODE = {0: "take", 24: "take"}
MODE.update({k: "split" for k in (2, 4, 5, 6, 7, 8, 11, 12, 13, 15)})

flat = [(w["x"].lower(), w["t"]) for g in data["caps"] for w in g["w"]]


def at(word, nth=1, after=-1.0):
    hits = [t for x, t in flat if x == word.lower() and t > after]
    if len(hits) < nth:
        raise SystemExit(f"palavra não encontrada: {word} #{nth} depois de {after}")
    return round(hits[nth - 1], 3)


# ---------- câmera: modo por item da EDL, punch-in alternado a cada corte (esconde o jump cut) ----------
cam, prev, z = [], None, 1.0
for s in segs:
    mode = MODE.get(s["edl"], "full")
    if mode != prev or mode == "take":
        z = 1.0
    else:
        z = 1.0 if z > 1.0 else (1.07 if mode == "split" else 1.12)
    cam.append([round(s["out"], 3), mode, z])
    prev = mode

# ---------- painel: kicker e recorte da gravação de tela (px da tela 1920x1080; largura w cabe em 1000 px) ----------
KICKS = [((2,), "MOTOR DE VOZ NOVO", ""), ((4, 5), "DICIONÁRIO FONÉTICO", ""), ((6, 7), "BANCADA DE TESTE", ""),
         ((8,), "ANTES · SEM A REGRA", "red"), ((11, 12), "NOVA REGRA NO DICIONÁRIO", ""),
         ((13,), "DEPOIS · COM A REGRA", ""), ((15,), "DICIONÁRIO FONÉTICO", "")]
kicks = [{"t0": first[e[0]], "t1": last[e[-1]]} for e, _, _ in KICKS]
HEADER = {"x": 372, "y": 292, "w": 640}
LIST_TOP = {"x": 385, "y": 330, "w": 600}
LIST_LOW = {"x": 385, "y": 610, "w": 600}
BANCADA = {"x": 1040, "y": 458, "w": 560}
FORM = {"x": 375, "y": 440, "w": 640}
crops = [dict(HEADER, t=first[2]), dict(LIST_TOP, t=first[4]), dict(LIST_LOW, t=at("pronúncia", 1, first[5]) - 0.3, d=0.7),
         dict(BANCADA, t=first[6]), dict(FORM, t=first[11]), dict(BANCADA, t=first[13]), dict(LIST_TOP, t=first[15])]
ROW_FM, ROW_WA = 610, 400          # centro das linhas "FM" e "whatsapp → uatizape" na lista (depois da regra nova)
t_fm = at("fm", 1, first[15])
hls = [{"id": "hl-wa", "t0": first[15] + 0.15, "t1": t_fm}, {"id": "hl-fm", "t0": t_fm, "t1": last[15]}]

cues = {"ia2": first[24], "proj": round(first[1] + 0.05, 3), "projR": at("exemplo", 1, first[1]),
        "motor": round(first[3] + 0.05, 3), "motorNew": round(first[3] + 0.35, 3), "motorR": at("natural"),
        "steps": round(first[19] + 0.05, 3), "pronto": at("pronto"), "infra": at("infraestrutura"),
        "integ": at("integração", 1, first[20]), "rule": round(first[14] + 0.1, 3), "nome": round(first[17] + 0.1, 3),
        "follow": at("acompanhe")}

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    sp = "".join(f'<span class="cw{" k" if w["k"] else ""}{" r" if w["r"] else ""}" id="w{gi}_{wi}">{w["x"]}</span>'
                 for wi, w in enumerate(g["w"]))
    caps_dom.append(f'          <div class="cg{" ai" if g["ai"] else ""}" id="g{gi}">{sp}</div>')

kick_dom = "\n".join(f'        <div class="kick {cls}" id="kk{i}"><span class="dot"></span>{txt}</div>' for i, (_, txt, cls) in enumerate(KICKS))

# ---------- SFX (poucos e baixos) ----------
SFX_DUR = {"whoosh-short": 0.57, "click-soft": 0.37, "click": 0.37, "pop": 0.72, "ping": 1.32}
sfx = [(first[e], "whoosh-short", 0.2) for e in (2, 4, 6, 11, 15)]
sfx += [(cues["proj"], "pop", 0.18), (cues["motor"], "pop", 0.18), (cues["steps"], "pop", 0.18),
        (cues["rule"], "ping", 0.2), (cues["nome"], "pop", 0.2), (cues["follow"], "pop", 0.2),
        (cues["pronto"], "click-soft", 0.25), (cues["pronto"] + 0.15, "click-soft", 0.22), (t_fm, "click-soft", 0.22)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "kicks": kicks, "crops": crops, "hls": hls, "cues": cues, "caps": data["caps"]}
r = lambda v: f"{v:.3f}"
fill = {
    "%%DUR%%": r(DUR),
    "%%IA1_D%%": r(first[1]), "%%IA2_S%%": r(first[24]), "%%IA2_D%%": r(DUR - first[24]),
    "%%PROJ_S%%": r(cues["proj"]), "%%PROJ_D%%": r(first[2] - cues["proj"]),
    "%%MOTOR_S%%": r(cues["motor"]), "%%MOTOR_D%%": r(first[4] - cues["motor"]),
    "%%STEPS_S%%": r(cues["steps"]), "%%STEPS_D%%": r(first[24] - cues["steps"]),
    "%%RULE_S%%": r(cues["rule"]), "%%RULE_D%%": r(first[15] - cues["rule"]),
    "%%NOME_S%%": r(cues["nome"]), "%%NOME_D%%": r(first[19] - cues["nome"]),
    "%%FOL_S%%": r(cues["follow"]), "%%FOL_D%%": r(DUR - cues["follow"]),
    "%%HL_FM_Y%%": str(ROW_FM - 20), "%%HL_WA_Y%%": str(ROW_WA - 20),
    "%%KICKS%%": kick_dom,
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "\ncues", cues, "\nkicks", kicks, "\ncrops", crops, "\nhls", hls)
print("cam", cam)
