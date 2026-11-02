"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> _pipeline/wh edit segs/cat.wav segs.json transcript_edit.json -> captions.py -> make.py mantém tudo sincronizado.
Visual meio-termo Apresentador x MARCA: cards escuros com kicker mono menta (Terminal Noir) + creme/champanhe e legenda
branca Montserrat (Clean Luxury). Legenda com quem fala: menta = Apresentador (atrás da câmera), champanhe = Convidada.
Uso: python3 -I make.py
"""
import ast, json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
SPEECH = data["speech"]
END_D = 4.6                      # tela final (enquete da prenda): precisa de tempo de leitura
DUR = round(SPEECH + END_D, 3)
OUT = [round(s["out"], 3) for s in segs]
CAP_Y = 1400                     # centro da legenda: sobre a blusa, abaixo do queixo mesmo no close
ORIGIN = "500px 880px"           # rosto no quadro 1080x1920 (câmera na mão: média das folhas)
WIDE, MID, CLOSE = 1.0, 1.12, 1.24

# quem fala em cada segmento: opções @j/@m da EDL (lida do build.py sem importar numpy)
tree = ast.parse(open(os.path.join(W, "build.py")).read())
EDL = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "EDL")
SPK = ["m" if "@m" in EDL[s["edl"]][4].split() else "j" for s in segs]


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in s if not unicodedata.combining(c)))


flat = [(norm(w["w"]), w["t"]) for w in data["words"]]


def at(phrase, nth=1):
    """início da n-ésima ocorrência da sequência de palavras (sem acento/pontuação)"""
    q = [norm(x) for x in phrase.split()]
    hits = [flat[i][1] for i in range(len(flat) - len(q) + 1) if [x for x, _ in flat[i:i + len(q)]] == q]
    if len(hits) < nth:
        raise SystemExit(f"frase não encontrada: {phrase} #{nth}")
    return round(hits[nth - 1], 3)


def cut(t):
    """corte da fala mais próximo (até 0,35 s antes da palavra); senão, 30 ms antes da palavra"""
    near = [o for o in OUT if -0.05 <= t - o <= 0.35]
    return near[-1] if near else round(t - 0.03, 3)


def K(s):
    """*palavra -> destaque champanhe; [x] -> emoji"""
    s = re.sub(r"\*([^\s*<]+)", r'<span class="k">\1</span>', s)
    return re.sub(r"\[([^\]]+)\]", r'<span class="em">\1</span>', s)


# ---------- câmera: todo corte troca o enquadramento; Apresentador perguntando = aberto/médio, Convidada = close/médio ----------
cam = [[0.0, MID]]
for i in range(1, len(segs)):
    s, prev = segs[i], cam[-1][1]
    if not s["label"]:
        z = CLOSE                                     # ela pensando
    elif SPK[i] == "j":
        z = WIDE if prev != WIDE else MID
    else:
        z = CLOSE if prev != CLOSE else MID
    if z == prev:
        z = MID if prev != MID else WIDE
    if s["label"] and s["dur"] < 0.5 and SPK[i] == SPK[i - 1]:
        continue                                      # pedaço curto da mesma fala ("e"): sem troca, evita piscar
    cam.append([round(s["out"], 3), z])
    if s["dur"] > 3.4:                                # trecho longo: um punch a mais no meio, num começo de bloco
        inner = [c["t0"] for c in data["caps"] if s["out"] + 1.4 < c["t0"] < s["out"] + s["dur"] - 1.2]
        if inner:
            cam.append([round(inner[0], 3), MID if z != MID else (CLOSE if SPK[i] == "m" else WIDE)])
for a, b in zip(cam, cam[1:]):
    assert b[0] > a[0], (a, b)

# ---------- cards do topo ----------
TOK1 = '<span class="tokw"><span class="tok mono"><span class="em">🎁</span>PULO ×1</span></span>'
TOK0 = '<span class="tokw"><span class="tok used mono"><span class="em">🎁</span>PULO ×0</span></span>'
TOKSW = ('<span class="tokw"><span class="tok mono"><span class="em">🎁</span>PULO ×1</span>'
         '<span class="tok used swap mono"><span class="em">🎁</span>PULO ×0</span></span>')
DOT, RED = '<i class="dot"></i>', '<i class="dot red"></i>'
SPICY = '<span class="spicy">· [🌶️] SAIA JUSTA</span>'
cards = []


def card(cid, t, kick, title="", big=False, sub="", rows=None, opts=None, pick=None, pick_at=None, tok=""):
    cards.append({"id": cid, "t": round(t, 3), "kick": kick, "title": title, "big": big, "sub": sub, "rows": rows or [],
                  "opts": opts, "pick": pick, "pickAt": pick_at, "tok": tok})


t_oi = cut(at("Oi Convidada"))
card("c_hook", 0.0, RED + "REC · ENTREVISTA", "Ela *pulou uma pergunta [👀]", big=True)
card("c_intro", t_oi, DOT + "EP. 01 · SUA MARCA", '<span data-var-text="quadro">Nome do Quadro</span>', big=True,
     sub="5 perguntas · <b>1 pulo</b> · 1 prenda [🎁]")
card("c_rules", cut(at("Eu vou fazer cinco")), DOT + "REGRAS DO JOGO", rows=[
    (at("cinco perguntas"), '<span class="n">5</span>perguntas'),
    (at("pular uma delas"), '<span class="n">1</span>pulo <small>(só um!)</small>'),
    (at("pagar alguma"), '<span class="n">[🎁]</span>pulou? paga *prenda'),
    (at("desconto um sorteio"), '<small>→ desconto, sorteio, alguma coisa assim</small>'),
])
# versão curta (24/10): sem "o que dá trabalho" e sem "pessoalmente ou internet"; o defeito vira a 5ª pergunta
card("c_q1", cut(at("Qual é o produto")), DOT + "PERGUNTA 01/05", "Produto *mais *vendido?", tok=TOK1)
card("c_q3", cut(at("Qual produto você achou")), DOT + "PERGUNTA 02/05", "Achou que ia bombar… e *encalhou?", tok=TOKSW)
card("c_q4", cut(at("Você já pensou")), DOT + "PERGUNTA 03/05", "Já pensou em *desistir?", sub='a "mais fácil" [😅]', tok=TOK0)
card("c_pp", cut(at("Aí agora vai ser")), DOT + "RODADA RÁPIDA", "Pingue-*pongue [🏓]", big=True, sub="responde sem pensar", tok=TOK0)
VS = [  # (início da pergunta, opções, escolhida, deixa da resposta)
    ("Nos meios de pagamento", ["[💸] Pix", "[💳] Cartão"], 0, at("Pix", 2)),
    ("Você prefere um cliente", ["Pechincha", "“Vou pensar”… e some"], 0, at("o que pechincha")),
    ("Responder direct", ["Responder direct", "Embalar pedido"], 1, at("mas embalar pedido") + 0.15),
    ("E agora marido", ["Marido ajudando", "Marido longe"], 0, at("meu marido ajudando") + 0.15),
]
for i, (q, o, p, pa) in enumerate(VS):
    card(f"c_vs{i + 1}", cut(at(q)), DOT + f"PINGUE-PONGUE {i + 1}/{len(VS)}", opts=o, pick=p, pick_at=round(pa, 3), tok=TOK0)
card("c_q5a", cut(at("Pode ser uma pergunta")), RED + "PERGUNTA 04/05 " + SPICY, "Agora uma *difícil…")
card("c_q5b", cut(at("Se você não fosse")), RED + "PERGUNTA 04/05 " + SPICY, "Se não fosse a dona, *compraria na loja?")
card("c_bonus", cut(at("Pra encerrar")), RED + 'PERGUNTA 05/05 <span class="spicy">· [🌶️🌶️]</span>', "Um *defeito da loja?", big=True)
END_CARDS = cut(at("Boa Muito obrigado"))
for p, c in zip(cards, cards[1:]):                 # a escolha do pingue-pongue fica ~0,9 s na tela antes do próximo card
    if p["opts"]:
        c["t"] = max(c["t"], round(p["pickAt"] + 0.9, 3))
for c, n in zip(cards, cards[1:] + [{"t": END_CARDS}]):
    c["t1"] = n["t"]

cards_dom = []
for c in cards:
    body = f'<div class="kick">{K(c["kick"])}{c["tok"]}</div>'
    if c["title"]:
        body += f'<div class="title{" big" if c["big"] else ""}">{K(c["title"])}</div>'
    for i, (_, r) in enumerate(c["rows"]):
        body += f'<div class="rule" id="{c["id"]}_r{i}">{K(r)}</div>'
    if c["opts"]:
        chk = ('<span class="chk"><svg viewBox="0 0 24 24" width="30" height="30"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" '
               'stroke="#121418" stroke-width="3.6" stroke-linecap="round" stroke-linejoin="round"/></svg></span>')
        oc = ["opt long" if len(re.sub(r"\[[^\]]*\]", "", o)) > 15 else "opt" for o in c["opts"]]
        body += (f'<div class="vs"><div class="{oc[0]}">{K(c["opts"][0])}{chk}</div><div class="vsx">vs</div>'
                 f'<div class="{oc[1]}">{K(c["opts"][1])}{chk}</div></div>')
    if c["sub"]:
        body += f'<div class="sub">{K(c["sub"])}</div>'
    cards_dom.append(f'        <div class="card" id="{c["id"]}">{body}</div>')

# ---------- figurinhas, carimbos e reação ----------
silent = [s for s in segs if not s["label"]]
pul2 = at("Eu vou pular essa", 2)
chips, rows_dom = [], []


def chip_row(*items):
    """items: (id, t, t1, html, extra_class) numa linha centralizada em y 1160"""
    rows_dom.append('        <div class="chip-row">' + "".join(
        f'<div class="chip{(" " + x) if x else ""}" id="{i}">{K(h)}</div>' for i, t, t1, h, x in items) + "</div>")
    chips.extend({"id": i, "t": round(t, 3), "t1": round(t1, 3), "kind": "chip"} for i, t, t1, h, x in items)


def stamp(cid, t, dur=1.7):
    rows_dom.append(f'        <div class="stamp" id="{cid}">PULOU!</div>')
    chips.append({"id": cid, "t": round(t, 3), "t1": round(t + dur, 3), "kind": "stamp"})


stamp("st0", at("Eu vou pular essa") + 0.4, dur=t_oi + 0.5 - at("Eu vou pular essa") - 0.4)
chip_row(("ch_reg", at("o produto") + 0.15, cut(at("Qual produto você achou")), "[🏷️] Produto X <small>o mais vendido</small>", ""))
th0, th1 = silent[0]["out"], silent[-1]["out"] + silent[-1]["dur"]
NUM = 9                                                        # o "pensando" real durou ~10 s: contador acelerado
chip_row(("ch_think", th0 - 0.1, pul2 - 0.05, '[🤔] pensando… <span id="think-n" class="mono">' +
          "".join(f"<span>00:{k + 1:02d}</span>" for k in range(NUM)) + "</span>", "dark"))
think = [[round(th0 + (th1 - th0) * k / NUM, 3), k] for k in range(NUM)]
stamp("st1", pul2 + 0.4)
chip_row(("ch_prenda", at("Vou pular", 3) + 0.35, cut(at("Você já pensou")), "[🎁] ela deve uma *prenda!", "dark"))
chip_row(("ch_forca", at("força de vontade"), cut(at("Aí agora vai ser")), "[💪] força de vontade", ""))
t_sei = at("Sei sei sei")
rows_dom.append('        <div class="sticker" id="sk_sei" style="left:700px;top:620px"><span class="em">🤨</span><div class="lbl">sei, sei…</div></div>')
chips.append({"id": "sk_sei", "t": round(t_sei, 3), "t1": round(cut(at("Pode ser uma pergunta")), 3), "kind": "chip"})
chip_row(("ch_cert", at("Com certeza", 3), cut(at("Aí justifica")), "[✅] com certeza!", ""))
chip_row(("ch_dif", at("É diferenciado"), cut(at("Pra encerrar")), "[✨] diferenciado", ""))
t_adap = at("está se adaptando")
chip_row(("ch_fis", at("loja física"), t_adap - 0.1, "[🏬] loja física <small>+</small> [📱] online", ""))
chip_row(("ch_adap", t_adap + 0.2, END_CARDS, "[💪] se adaptando", "dark"))

# ---------- legenda (DOM estático): rótulo de quem fala quando a voz troca ----------
caps_dom, last = [], None
for gi, g in enumerate(data["caps"]):
    g["who"] = g["spk"] != last
    last = g["spk"]
    lines = []
    for li, ln in enumerate(g["lines"]):
        sp = "".join(f'<span class="cw{" k" if w["k"] else ""}" id="w{gi}_{li}_{wi}">{w["x"]}</span>' for wi, w in enumerate(ln))
        lines.append(f'<div class="ln">{sp}</div>')
    who = (f'<div class="who"><i></i>{"APRESENTADOR" if g["spk"] == "j" else "CONVIDADA"}</div>' if g["who"] else "")
    caps_dom.append(f'        <div class="cg {g["spk"]}" id="g{gi}">{who}{"".join(lines)}</div>')

# ---------- SFX ----------
POLL_AT = 0.75
SFX_DUR = {"pop": 0.72, "whoosh-short": 0.57, "whoosh": 0.57, "sparkle": 1.8, "click-soft": 0.37, "ding": 0.7, "tick": 0.06, "buzz": 0.62}
sfx = []
for c in cards:
    q = c["id"] in ("c_q1", "c_q3", "c_q4", "c_q5a", "c_bonus")
    sfx.append((c["t"], "ding" if q else "whoosh-short", 0.22 if q else 0.16))
    sfx += [(t, "click-soft", 0.3) for t, _ in c["rows"]]
    if c["opts"]:
        sfx.append((c["pickAt"], "pop", 0.24))
for ch in chips:
    sfx.append((ch["t"], "buzz" if ch["id"].startswith("st") else "pop", 0.34 if ch["id"].startswith("st") else 0.18))
sfx += [(t, "tick", 0.32) for t, _ in think]
sfx += [(round(SPEECH - 0.05, 3), "whoosh", 0.2), (round(SPEECH + POLL_AT, 3), "sparkle", 0.16)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    t = max(0.0, round(t, 3))
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 40) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "caps": data["caps"], "end": SPEECH, "dur": DUR, "pollAt": POLL_AT,
     "cards": [{"id": c["id"], "t": c["t"], "t1": c["t1"], "rows": [t for t, _ in c["rows"]],
                **({"opts": 1, "pick": c["pick"], "pickAt": c["pickAt"]} if c["opts"] else {})} for c in cards],
     "chips": chips, "think": think, "tokSwap": {"card": "#c_q3", "t": round(pul2 + 0.4, 3)}}
fill = {
    "%%DUR%%": f"{DUR:.3f}", "%%SPEECH%%": f"{SPEECH:.3f}", "%%END_D%%": f"{END_D:.3f}",
    "%%ORIGIN%%": ORIGIN, "%%CAP_Y%%": str(CAP_Y),
    "%%CARDS_DOM%%": "\n".join(cards_dom), "%%CHIPS_DOM%%": "\n".join(rows_dom),
    "%%CAPS_DOM%%": "\n".join(caps_dom), "%%SFX%%": "\n".join(tags),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "| cards", len(cards), "| figurinhas", len(chips), "| blocos", len(caps_dom), "| sfx", len(tags))
for c in cards:
    print(f"  {c['t']:7.2f}-{c['t1']:7.2f} {c['id']}")
print("planos", len(cam), "| menor", min(round(b[0] - a[0], 2) for a, b in zip(cam, cam[1:])))
