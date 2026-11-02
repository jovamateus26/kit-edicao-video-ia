"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> mapwords.py -> captions.py -> make.py mantém tudo sincronizado.
Uso: python3 -I make.py
"""
import json, os

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
DUR = data["dur"]

# início de cada item da EDL na fala editada
first = {}
for s in segs:
    first.setdefault(s["edl"], s["out"])
SPLIT_EDL = {0, *range(5, 15), 24, 25, 26}

flat = [(w["x"].lower(), w["t"]) for g in data["caps"] for w in g["w"]]


def at(word, nth=1, after=-1.0):
    hits = [t for x, t in flat if x == word.lower() and t > after]
    if len(hits) < nth:
        raise SystemExit(f"palavra não encontrada: {word} #{nth} depois de {after}")
    return round(hits[nth - 1], 3)


# ---------- câmera: split/tela cheia por trecho, zoom alternado a cada corte (esconde o jump cut) ----------
cam, prev_mode, z = [], None, 1.0
for s in segs:
    mode = "split" if s["edl"] in SPLIT_EDL else "full"
    if mode != prev_mode:
        z = 1.0
    else:
        z = 1.0 if z > 1.0 else (1.1 if mode == "split" else 1.12)
    if s["edl"] == 19:  # "voz": punch forte
        z = 1.2
    cam.append([round(s["out"], 3), mode, z])
    prev_mode = mode
assert cam[-1][1:] == ["split", 1.0], cam[-1]  # último quadro = primeiro quadro (loop)

# ---------- voz de IA ----------
ai = data["ai_words"]
MINT = {"exemplo", "fm!", "artista", "convidado,", "ar."}
hook = [w for w in ai if w["t"] < data["ai1"][1]]
air = [w for w in ai if w["t"] >= data["ai1"][1]]
air_lines = []
for w in air:
    if not air_lines or w["seg"] != air_lines[-1][0]["seg"]:
        air_lines.append([])
    air_lines[-1].append(w)

ROBOT = ('<svg viewBox="0 0 24 24" class="ico"><rect x="4" y="7" width="16" height="12" rx="3" fill="none" stroke="#5eead4" '
         'stroke-width="2"/><circle cx="9.5" cy="13" r="1.6" fill="#5eead4"/><circle cx="14.5" cy="13" r="1.6" fill="#5eead4"/>'
         '<path d="M12 7V4M9 4h6" stroke="#5eead4" stroke-width="2" stroke-linecap="round"/></svg>')


def player(wp, bp, lines, bars, line_ids=None):
    head = ('<div class="p-head"><span class="onair"><span class="dot"></span>NO AR</span>'
            f'<span class="p-name">Rádio Exemplo FM</span><span class="p-ai">{ROBOT}voz IA</span></div>')
    k, ls = 0, []
    for li, ln in enumerate(lines):
        spans = []
        for w in ln:
            spans.append(f'<span class="kw" id="{wp}{k}">{w["x"]}</span>')
            k += 1
        lid = f' id="{line_ids[li]}"' if line_ids else ""
        ls.append(f'<div class="p-line"{lid}>{"".join(spans)}</div>')
    wave = "".join(f'<div class="bar" id="{bp}{i}" style="height: {max(8, round(v * 110))}px"></div>' for i, v in enumerate(bars))
    return f'<div class="player">{head}<div class="p-text">{"".join(ls)}</div><div class="p-wave">{wave}</div></div>'


def kw(words):
    return [{"t": w["t"], "m": w["x"].lower() in MINT} for w in words]


# ---------- deixas ----------
T_IDE, T_FLOW, T_AIR, T_FULL2, T_SIM = first[5], first[9], first[14], first[15], first[24]
ide = {"s": T_IDE, "ag": at("Antigravity"), "agent": at("como"), "tree": at("e", 1, at("IA")), "run": at("rodando")}
flow = {"s": T_FLOW, "r1": at("receber") - 0.04, "texto": at("texto"), "audio": at("áudio", 1, at("texto")),
        "r2": at("vai", 1, at("áudio")), "recado": at("recado"), "musica": at("música"), "pick": at("estiver"),
        "r3": at("procurar"), "r4": at("baixar"), "r5": at("deixar"), "noar": at("transmitir")}
air_d = {"s": T_AIR, "lines": [{"t0": round(first[14] if i == 0 else ln[0]["t"] - 0.05, 3)} for i, ln in enumerate(air_lines)]}
TEXT = "Alô, ouvintes da Exemplo FM!"
t_type0, t_type1 = at("ele", 1, T_SIM), at("mensagem", 1, T_SIM) + 0.4
typed = [round(t_type0 + i * (t_type1 - t_type0) / len(TEXT), 3) for i in range(len(TEXT))]
sim = {"s": T_SIM, "gen": at("transformar", 1, T_SIM)}
cards = {"proj": round(first[1] + 0.05, 3), "projR": at("pra", 1, first[4] - 0.1), "piper": at("piper") - 0.05,
         "piperR": at("gerou"), "novo": at("lançado"), "novoTag": at("usando", 1, at("lançado")),
         "follow": at("modelo", 1, at("lançado")) + 0.1}

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    sp = "".join(f'<span class="cw{" k" if w["k"] else ""}" id="w{gi}_{wi}">{w["x"]}</span>' for wi, w in enumerate(g["w"]))
    caps_dom.append(f'          <div class="cg" id="g{gi}">{sp}</div>')

# ---------- SFX ----------
SFX_DUR = {"whoosh-short": 0.57, "whoosh": 0.57, "click-soft": 0.37, "click": 0.37, "pop": 0.72, "ping": 1.32,
           "sparkle": 1.8, "typing": 1.54}
sfx = [(first[1], "whoosh-short", 0.28), (T_IDE, "whoosh-short", 0.28), (ide["agent"], "click-soft", 0.3),
       (ide["tree"], "click-soft", 0.3), (ide["run"], "pop", 0.22), (T_FLOW, "whoosh-short", 0.28),
       (flow["r1"], "pop", 0.2), (flow["r2"], "pop", 0.2), (flow["pick"], "click", 0.25), (flow["r3"], "pop", 0.2),
       (flow["r4"], "pop", 0.2), (flow["r5"], "pop", 0.2), (flow["noar"], "ping", 0.28), (T_FULL2, "whoosh-short", 0.28),
       (cards["piper"], "pop", 0.22), (cards["novo"], "pop", 0.24), (cards["follow"], "click", 0.25),
       (T_SIM, "whoosh-short", 0.28), (typed[0], "typing", 0.28), (sim["gen"], "click-soft", 0.3)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "hook_words": kw(hook), "air_words": kw(air), "bars1": data["bars1"], "bars2": data["bars2"],
     "ai1": data["ai1"], "ai2": data["ai2"], "ide": ide, "flow": flow, "air": air_d, "sim": sim, "typed": typed,
     "cards": cards, "caps": data["caps"]}
r = lambda v: f"{v:.3f}"
fill = {
    "%%DUR%%": r(DUR),
    "%%HOOK_D%%": r(first[1]),
    "%%IDE_S%%": r(T_IDE), "%%IDE_D%%": r(T_FLOW - T_IDE),
    "%%FLOW_S%%": r(T_FLOW), "%%FLOW_D%%": r(T_AIR - T_FLOW),
    "%%AIR_S%%": r(T_AIR), "%%AIR_D%%": r(T_FULL2 - T_AIR),
    "%%SIM_S%%": r(T_SIM), "%%SIM_D%%": r(DUR - T_SIM),
    "%%PROJ_S%%": r(cards["proj"]), "%%PROJ_D%%": r(T_IDE - cards["proj"]),
    "%%PIPER_S%%": r(cards["piper"]), "%%PIPER_D%%": r(first[21] - cards["piper"]),
    "%%NOVO_S%%": r(cards["novo"]), "%%NOVO_D%%": r(T_SIM - cards["novo"]),
    "%%FOL_S%%": r(cards["follow"]), "%%FOL_D%%": r(T_SIM - cards["follow"]),
    "%%CAP_S%%": r(first[1]), "%%CAP_D%%": r(DUR - first[1]),
    "%%PLAYER_HOOK%%": player("hk", "hb", [hook], data["bars1"]),
    "%%PLAYER_AIR%%": player("ak", "ab", air_lines, data["bars2"], [f"al{i}" for i in range(len(air_lines))]),
    "%%PLAYER_SIM%%": player("sk", "sb", [hook], data["bars1"]),
    "%%TYPED%%": "".join(f'<span class="ch" id="sc{i}">{c}</span>' for i, c in enumerate(TEXT)),
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "| ide", ide, "\nflow", flow, "\nair", air_d, "\nsim", sim, "\ncards", cards)
print("cam", cam)
