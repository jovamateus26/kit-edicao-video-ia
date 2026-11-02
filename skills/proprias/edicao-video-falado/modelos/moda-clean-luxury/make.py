"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> _pipeline/wh edit segs/cat.wav segs.json transcript_edit.json -> captions.py -> make.py mantém tudo sincronizado.
Uso: python3 -I make.py
"""
import json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
SPEECH = data["speech"]
END_D = 2.6                      # tela final (último quadro desfocado + CTA)
DUR = round(SPEECH + END_D, 3)
OUT = [round(s["out"], 3) for s in segs]
CAP_Y = 1330                     # centro da legenda: sobre a blusa, abaixo do queixo mesmo no close 1.28
ORIGIN = "470px 690px"           # rosto (entre os olhos) no quadro 1080x1920 já desespelhado
WIDE, MID, CLOSE = 1.0, 1.12, 1.28


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


flat = [(norm(w["w"]), w["t"]) for w in data["words"]]


def at(phrase, nth=1):
    """início da n-ésima ocorrência da sequência de palavras (sem acento/pontuação: "dá" casa com "da", por isso frases)"""
    q = [norm(x) for x in phrase.split()]
    hits = [flat[i][1] for i in range(len(flat) - len(q) + 1) if [x for x, _ in flat[i:i + len(q)]] == q]
    if len(hits) < nth:
        raise SystemExit(f"frase não encontrada: {phrase} #{nth}")
    return round(hits[nth - 1], 3)


def cut(t):
    """corte da fala mais próximo (até 0,35 s antes da palavra); senão, 30 ms antes da palavra"""
    near = [o for o in OUT if -0.05 <= t - o <= 0.35]
    return near[-1] if near else round(t - 0.03, 3)


# ---------- câmera: (deixa, zoom). Todo corte real da fala troca o enquadramento (esconde o jump cut) ----------
CAM = [
    (0.0, WIDE),
    (cut(at("que muita gente")), CLOSE),
    (cut(at("A gente também")), MID),
    (cut(at("plantão de vendas")), WIDE),           # título PLANTÃO DE VENDAS: loja e logo no quadro
    (cut(at("Como que funciona")), CLOSE),
    (cut(at("Ah eu preciso")), WIDE),
    (cut(at("a loja tá fechada")), MID),
    (cut(at("fora dos horários")), CLOSE),
    (cut(at("de atendimento")), WIDE),
    (cut(at("a gente faz plantão")), CLOSE),
    (cut(at("Se a gente")), WIDE),
    (cut(at("a gente vai ficar")), MID),
    (cut(at("A gente vem até")), CLOSE),
    (cut(at("ou faz entregas")), WIDE),
    (cut(at("É só mandar")), MID),                 # título É SÓ MANDAR UMA MENSAGEM
    (cut(at("Pode acontecer")), CLOSE),
    (cut(at("mas na grande")), WIDE),
    (cut(at("a gente tá por aqui")), MID),
    (cut(at("a gente dá um pulinho")), CLOSE),
    (cut(at("não tem problema")), WIDE),
    (cut(at("Eu sei que")), CLOSE),
    (cut(at("precisa de uma coisa")), MID),
    (cut(at("ou tá trabalhando")), WIDE),
    (cut(at("Então pode mandar")), CLOSE),            # CTA falado
]
CAM = [[round(t, 3), z] for t, z in CAM]
missing = [o for o in OUT[1:] if all(abs(o - t) > 1e-3 for t, _ in CAM)]
for i in range(1, len(CAM)):
    assert CAM[i][0] > CAM[i - 1][0] and CAM[i][1] != CAM[i - 1][1], CAM[i]
shots = [round(b[0] - a[0], 2) for a, b in zip(CAM, CAM[1:] + [[SPEECH, 0]])]

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    lines = []
    for li, ln in enumerate(g["lines"]):
        sp = "".join(f'<span class="cw{" k" if w["k"] else ""}" id="w{gi}_{li}_{wi}">{w["x"]}</span>' for wi, w in enumerate(ln))
        lines.append(f'<div class="ln">{sp}</div>')
    body = "".join(lines)
    cls = "cg"
    if g["big"]:
        cls += " big" + (" mid" if sum(len(w["x"]) for ln in g["lines"] for w in ln) > 16 else "")
        body = f'<div class="hair t"></div>{body}<div class="hair b"></div>'
    caps_dom.append(f'        <div class="{cls}" id="g{gi}">{body}</div>')

CHAT = ('<svg viewBox="0 0 24 24" class="ico"><path d="M12 3.2c-5 0-9 3.5-9 7.9 0 2.4 1.2 4.6 3.2 6l-.7 3.7 3.9-2.2c.8.2 1.7.3 2.6.3 '
        '5 0 9-3.5 9-7.8S17 3.2 12 3.2z" fill="none" stroke="#edd3a0" stroke-width="1.9" stroke-linejoin="round"/>'
        '<circle cx="8.2" cy="11.1" r="1.25" fill="#edd3a0"/><circle cx="12" cy="11.1" r="1.25" fill="#edd3a0"/>'
        '<circle cx="15.8" cy="11.1" r="1.25" fill="#edd3a0"/></svg>')

# ---------- SFX discretos: pop nos títulos e no CTA, whoosh suave na tela final ----------
CTA_AT = 0.32
SFX_DUR = {"pop": 0.72, "whoosh-short": 0.57, "whoosh": 0.57, "sparkle": 1.8, "click-soft": 0.37}
big_t = [g["lines"][0][0]["t"] for g in data["caps"] if g["big"]]
sfx = [(t, "pop", 0.2) for t in big_t] + [(round(SPEECH - 0.05, 3), "whoosh-short", 0.2), (round(SPEECH + CTA_AT, 3), "pop", 0.16)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": CAM, "push": 1.05, "caps": data["caps"], "end": SPEECH, "dur": DUR, "ctaAt": CTA_AT}
fill = {
    "%%DUR%%": f"{DUR:.3f}", "%%SPEECH%%": f"{SPEECH:.3f}", "%%END_D%%": f"{END_D:.3f}",
    "%%ORIGIN%%": ORIGIN, "%%CAP_Y%%": str(CAP_Y), "%%CHAT%%": CHAT,
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "| blocos", len(caps_dom), "| sfx", len(tags))
print("cam", CAM)
print("planos (s)", shots, "| cortes sem troca:", missing)
