"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py) + prints.json (capture/tops).

As deixas saem das palavras da legenda (tempo real da fala editada): re-editar a fala e rodar
build.py -> transcribe_edit.py -> captions.py -> make.py mantém tudo sincronizado.
Uso: python3 -I make.py
"""
import json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
P = json.load(open(os.path.join(W, "prints.json")))
DUR = data["dur"]
SPLIT_Y = 460
OUT = [round(s["out"], 3) for s in segs]


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    return re.sub(r"[^a-z0-9%]", "", "".join(c for c in s if not unicodedata.combining(c)))


flat = [(norm(w["w"]), w["t"]) for w in data["words"]]


def at(word, nth=1, after=-1.0):
    hits = [t for x, t in flat if x == norm(word) and t > after]
    if len(hits) < nth:
        raise SystemExit(f"palavra não encontrada: {word} #{nth} depois de {after}")
    return round(hits[nth - 1], 3)


def seg_at(t):
    """início do segmento (corte) mais próximo de t"""
    return min(OUT, key=lambda o: abs(o - t))


# ---------- cenas (início = corte da fala) ----------
S_CVE = seg_at(at("É"))
S_REQ = seg_at(at("Só"))
F_JA = seg_at(at("Já", 1, 15))
S_GOV = seg_at(at("Vários"))
S_BR = seg_at(at("Aqui"))
S_ANA = round(at("como", 1, S_BR) - 0.05, 3)
S_FIX = seg_at(at("Essa"))
S_TERM = seg_at(at("então", 1, S_FIX))
F_CUR = seg_at(at("curiosidade") - 0.3)
S_DEC = round(at("são", 1, F_CUR) - 0.04, 3)
S_IA = seg_at(at("elas"))
F_COM = seg_at(at("comunidade") - 0.2)
S_STAT = seg_at(at("Entre"))
F_END = seg_at(at("imagine") - 0.3)
print("cenas", dict(S_CVE=S_CVE, S_REQ=S_REQ, F_JA=F_JA, S_GOV=S_GOV, S_BR=S_BR, S_ANA=S_ANA, S_FIX=S_FIX, S_TERM=S_TERM,
                    F_CUR=F_CUR, S_DEC=S_DEC, S_IA=S_IA, F_COM=F_COM, S_STAT=S_STAT, F_END=F_END))

# ---------- câmera: split/tela cheia por trecho, zoom alternado a cada corte (esconde o jump cut) ----------
FULL_RANGES = [(F_JA, S_GOV), (F_CUR, S_DEC), (F_COM, S_STAT), (F_END, DUR + 1)]
def mode_at(t): return "full" if any(a <= t + 1e-3 < b for a, b in FULL_RANGES) else "split"
PUNCH = {F_JA: 1.12, at("estrago") - 0.05: 1.16}
events = sorted(set(OUT) | {a for a, _ in FULL_RANGES} | {b for _, b in FULL_RANGES if b < DUR} | set(PUNCH))
cam, prev_mode, z = [], None, 1.0
for t in events:
    mode = mode_at(t)
    if mode != prev_mode:
        z = 1.0
    else:
        z = 1.0 if z > 1.0 else (1.08 if mode == "split" else 1.12)
    z = PUNCH.get(t, z)
    cam.append([round(t, 3), mode, z])
    prev_mode = mode

# ---------- prints reais ----------
SRC = {"uol": ("noticias.uol.com.br", "21/10/2026 · 19h23"), "olhar": ("olhardigital.com.br", "22/10/2026 · 12h24"),
       "terra": ("terra.com.br", "22/10/2026 · 11h11"), "bbc": ("bbc.com/portuguese", "22/10/2026")}
DOC = ('<svg viewBox="0 0 24 24" class="ico"><path d="M6 3h8l4 4v14H6z" fill="none" stroke="#aab2bc" stroke-width="2" stroke-linejoin="round"/>'
       '<path d="M9 12h6M9 16h6" stroke="#aab2bc" stroke-width="2" stroke-linecap="round"/></svg>')
marks, premarked = [], []


def card(cid, key, w, top=0, left=0, y0=0, y1=None, strip=True, rot=0.0):
    """print real (imagem intacta, só recortada) + faixa de fonte; devolve html e ids dos marca-textos"""
    p = P["cards"].get(key) or P["shots"][key]
    s = w / p["w"]
    y1 = p["h"] if y1 is None else y1
    h = round((y1 - y0) * s)
    out = [f'<div class="pc" id="{cid}" style="left: {left}px; top: {top}px; width: {w}px; transform: rotate({rot}deg)">']
    if strip:
        dom, dt = SRC[key.split("_")[0]]
        out.append(f'<div class="pc-src">{DOC}<b>{dom}</b><span class="dt">{dt}</span></div>')
    out.append(f'<div class="pc-shot" style="height: {h}px"><img src="assets/img/{p["file"]}" alt="" '
               f'style="width: {w}px; top: {round(-y0 * s)}px" />')
    ids = []
    for i, q in enumerate(p["hls"]):
        hid = f"{cid}-h{i}"
        ids.append((hid, q["w"] * s))
        out.append(f'<div class="hl" id="{hid}" style="left: {round(q["x"] * s - 4)}px; top: {round((q["y"] - y0) * s + 2)}px; '
                   f'width: {round(q["w"] * s + 8)}px; height: {round(q["h"] * s - 2)}px"></div>')
    out.append("</div></div>")
    return "".join(out), ids


def mark(ids, t, total):
    sw = sum(w for _, w in ids)
    c = t
    for hid, w in ids:
        d = round(max(0.08, total * w / sw), 3)
        marks.append([hid, round(c, 3), d])
        c += d


def scene(sid, start, end, inner):
    return (f'      <div id="{sid}" class="scene clip" data-start="{start:.3f}" data-duration="{end - start:.3f}" data-track-index="1">\n'
            f'        {inner}\n      </div>')


ICON = {
    "laptop": '<svg viewBox="0 0 24 24" class="ico"><rect x="4" y="5" width="16" height="11" rx="1.6" fill="none" stroke="#e8eaed" stroke-width="1.8"/><path d="M2 19h20" stroke="#e8eaed" stroke-width="1.8" stroke-linecap="round"/></svg>',
    "server": '<svg viewBox="0 0 24 24" class="ico" id="srv-ico"><rect x="4" y="3.5" width="16" height="7" rx="1.6" fill="none" stroke="#e8eaed" stroke-width="1.8"/><rect x="4" y="13.5" width="16" height="7" rx="1.6" fill="none" stroke="#e8eaed" stroke-width="1.8"/><circle cx="8" cy="7" r="1.2" fill="#5eead4"/><circle cx="8" cy="17" r="1.2" fill="#5eead4"/><path d="M12 7h5M12 17h5" stroke="#e8eaed" stroke-width="1.8" stroke-linecap="round"/></svg>',
    "unlock": '<svg viewBox="0 0 24 24" class="ico"><rect x="5" y="11" width="14" height="10" rx="2" fill="none" stroke="#f87171" stroke-width="2"/><path d="M8 11V7.5a4 4 0 0 1 7.6-1.7" fill="none" stroke="#f87171" stroke-width="2" stroke-linecap="round"/></svg>',
    "check": '<svg viewBox="0 0 24 24" class="ico"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="#0b0d10" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg>',
}
SC, JS = [], []

# 1. gancho: pilha de manchetes reais (1º quadro = capa, com a frase já marcada)
c_t, h_t = card("pk-terra", "terra", 1000, top=6, y0=0, y1=990, strip=False)
c_u, h_u = card("pk-uol", "uol", 1000, top=96, strip=False, rot=1.2)
c_b, h_b = card("pk-bbc", "bbc", 790, top=12, left=105, strip=False, rot=-1.4)
premarked += [h for h, _ in h_t[:1]]
T_UOL, T_BBC = round(at("PHP") - 0.05, 3), round(at("hackear") - 0.08, 3)
mark(h_u, T_UOL + 0.28, 0.4)
SC.append(scene("sc-hook", 0, S_CVE, f'<div id="pile">{c_t}{c_u}{c_b}</div>'))
JS.append(f'''      // gancho: manchetes caem uma sobre a outra
      gsap.set(["#pk-uol", "#pk-bbc"], {{ opacity: 0 }});
      tl.fromTo("#pk-uol", {{ opacity: 0, scale: 1.1, y: -40 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "power3.out", ...IR }}, {T_UOL});
      tl.fromTo("#pk-bbc", {{ opacity: 0, scale: 1.1, y: -40 }}, {{ opacity: 1, scale: 1, y: 0, duration: 0.22, ease: "power3.out", ...IR }}, {T_BBC});''')

# 2. o que é: print UOL (execução remota sem autenticação + CVEs)
c, h = card("pc-cve", "uol_cve", 960, top=8, left=20)
mark(h[:3], at("executar"), 0.8)
mark(h[3:], at("senha"), 0.45)
SC.append(scene("sc-cve", S_CVE, S_REQ, c))
JS.append(f'      rise("#pc-cve", {S_CVE}, 0.28);')

# 3. como o ataque funcionava (diagrama)
T_SEND, T_ARR, T_RUN = at("enviava"), at("requisição"), at("rodava")
SC.append(scene("sc-req", S_REQ, F_JA, f'''<div id="rq-kick" class="kick">COMO O ATAQUE FUNCIONAVA</div>
        <div class="node" id="nd-a"><div class="tile">{ICON["laptop"]}</div><div class="n-lab">qualquer um<br>na internet</div></div>
        <div class="node" id="nd-s"><div class="tile" id="srv-tile">{ICON["server"]}</div><div class="n-lab">servidor<br>com PHP</div></div>
        <div id="rq-line"></div>
        <div id="rq-pkt">requisição + comando</div>
        <div id="rq-lock"><span class="xpill">{ICON["unlock"]}<s>login</s></span><span class="xpill"><s>senha</s></span><span class="xpill"><s>permissão</s></span></div>
        <div id="rq-term"><div class="win-bar"><i></i><i></i><i></i><span>servidor — php</span></div>
          <div class="t-body"><div id="tq1" class="dim">&gt; requisição recebida</div><div id="tq2"><span class="p">$</span> <span class="bad">comando_do_invasor</span></div><div id="tq3" class="bad">&gt; executado no servidor (sem senha)</div></div></div>'''))
JS.append(f'''      // diagrama: o pacote viaja até o servidor e o comando roda
      rise("#rq-kick", {S_REQ}, 0.26);
      pop("#nd-a", {S_REQ + 0.04}, 0.3); pop("#nd-s", {S_REQ + 0.1}, 0.3);
      gsap.set(["#rq-pkt", "#tq1", "#tq2", "#tq3"], {{ opacity: 0 }});
      rise("#rq-lock", {S_REQ + 0.16}, 0.3);
      rise("#rq-term", {S_REQ + 0.22}, 0.3);
      tl.fromTo("#rq-pkt", {{ opacity: 0, x: -40 }}, {{ opacity: 1, x: 0, duration: 0.2, ease: "power2.out", ...IR }}, {T_SEND});
      tl.to("#rq-pkt", {{ x: 300, duration: {round(max(0.4, T_ARR - T_SEND - 0.2), 3)}, ease: "power2.inOut" }}, {T_SEND + 0.2});
      tl.to("#rq-pkt", {{ opacity: 0, scale: 0.6, duration: 0.18 }}, {T_ARR + 0.05});
      tl.to("#srv-tile", {{ borderColor: "#f87171", backgroundColor: "rgba(248,113,113,0.16)", duration: 0.15 }}, {T_ARR + 0.05});
      tl.set("#tq1", {{ opacity: 1 }}, {T_ARR + 0.1});
      tl.set("#tq2", {{ opacity: 1 }}, {T_RUN});
      tl.set("#tq3", {{ opacity: 1 }}, {at("comando") + 0.1});''')

# 4. governos derrubando sites: manchete UOL + países
c, h = card("pc-gov", "uol", 1000, top=0)
mark(h, at("governos"), 0.45)
T_CH = at("desabilitando", 2)
chips = "".join(f'<span class="cchip" id="cc{i}"><span class="dot"></span>{n}</span>' for i, n in enumerate(["Holanda", "Finlândia", "França", "Dinamarca"]))
SC.append(scene("sc-gov", S_GOV, S_BR, c + f'<div id="gov-chips" style="top: 724px"><span class="cchip k" id="cck">FORA DO AR</span>{chips}</div>'))
JS.append(f'''      rise("#pc-gov", {S_GOV}, 0.28);
      gsap.set(["#cck", "#cc0", "#cc1", "#cc2", "#cc3"], {{ opacity: 0 }});
      ["#cck", "#cc0", "#cc1", "#cc2", "#cc3"].forEach((s, i) => pop(s, {T_CH} + i * 0.14, 0.26));''')

# 5. Brasil: manchete Olhar Digital -> parágrafo UOL (Anatel / TRF)
c, h = card("pc-br", "olhar", 1000, top=30, y0=0, y1=850)
mark(h, at("Brasil") - 0.05, 0.45)
SC.append(scene("sc-br", S_BR, S_ANA, c))
JS.append(f'      rise("#pc-br", {S_BR}, 0.28);')
c, h = card("pc-ana", "uol_anatel", 1000, top=70)
mark(h[:1], at("Anatel"), 0.45)
mark(h[1:], at("TRF"), 0.35)
SC.append(scene("sc-ana", S_ANA, S_FIX, c))
JS.append(f'      rise("#pc-ana", {S_ANA}, 0.26);')

# 6. já corrigida: Terra (versões corrigidas) + selo
c, h = card("pc-fix", "terra", 1000, top=10, y0=630, y1=1500)
mark(h[1:], at("corrigida"), 0.7)
T_ST = at("atualizações", 1, S_FIX)
SC.append(scene("sc-fix", S_FIX, S_TERM, c + f'<div class="stamp" id="fx-stamp" style="left: 590px; top: 700px; transform: rotate(-4deg)">{ICON["check"]}CORREÇÃO DISPONÍVEL</div>'))
JS.append(f'''      rise("#pc-fix", {S_FIX}, 0.28);
      gsap.set("#fx-stamp", {{ opacity: 0 }});
      tl.fromTo("#fx-stamp", {{ opacity: 0, scale: 1.5, rotation: -12 }}, {{ opacity: 1, scale: 1, rotation: -4, duration: 0.26, ease: "back.out(2)", ...IR }}, {T_ST});''')

# 7. tem servidor com PHP? atualize (terminal)
CMD = "sudo apt update && sudo apt upgrade"
T_TY0 = at("instale") - 0.05
T_TY1 = T_TY0 + 1.0
typed = [round(T_TY0 + i * (T_TY1 - T_TY0) / len(CMD), 3) for i in range(len(CMD))]
T_OK = at("agora", 1, S_TERM)
BAR = 20
SC.append(scene("sc-term", S_TERM, F_CUR, f'''<div id="fx-kick" class="kick">O QUE FAZER</div>
        <div id="fx-q">Tem servidor com PHP?</div>
        <div id="fx-term"><div class="win-bar"><i></i><i></i><i></i><span>servidor — bash</span></div>
          <div class="t-body"><div><span class="p">$</span> <span id="fx-cmd">{"".join(f'<span class="ch" id="fc{i}">{ch}</span>' for i, ch in enumerate(CMD))}</span></div><div id="fx-l2" class="dim">atualizando pacotes do php…</div><div id="fx-l3"><span class="ok" id="fx-bar">{"".join(f'<span id="fb{i}">█</span>' for i in range(BAR))}</span> <span id="fx-pct">100%</span></div><div id="fx-l4" class="ok">✓ PHP atualizado</div></div></div>'''))
JS.append(f'''      // terminal: digita o comando, barra enche, PHP atualizado
      rise("#fx-kick", {S_TERM}, 0.26); rise("#fx-q", {S_TERM + 0.05}, 0.28); rise("#fx-term", {S_TERM + 0.12}, 0.3);
      gsap.set(["#fx-cmd .ch", "#fx-l2", "#fx-l3", "#fx-l4", "#fx-bar span", "#fx-pct"], {{ opacity: 0 }});
      {json.dumps(typed)}.forEach((t, i) => tl.set("#fc" + i, {{ opacity: 1 }}, t));
      tl.set(["#fx-l2", "#fx-l3"], {{ opacity: 1 }}, {T_TY1 + 0.1});
      for (let i = 0; i < {BAR}; i++) tl.set("#fb" + i, {{ opacity: 1 }}, {T_TY1 + 0.1} + i * {round(max(0.02, (T_OK - T_TY1 - 0.2) / BAR), 3)});
      tl.set("#fx-pct", {{ opacity: 1 }}, {T_OK - 0.05});
      pop("#fx-l4", {T_OK}, 0.26);''')

# 8. curiosidade: falha de mais de uma década (BBC) -> detectada por IA (BBC)
c, h = card("pc-dec", "bbc_decada", 1000, top=190, y0=14)
mark(h, at("anos", 1, S_DEC), 0.4)
SC.append(scene("sc-dec", S_DEC, S_IA, c))
JS.append(f'      rise("#pc-dec", {S_DEC}, 0.26);')
c, h = card("pc-ia", "bbc", 740, top=0, left=130)
mark(h, at("inteligência"), 0.45)
SC.append(scene("sc-ia", S_IA, F_COM, c))
JS.append(f'      rise("#pc-ia", {S_IA}, 0.28);')

# 9. 70% dos sites: número + citação (Olhar Digital)
T_70 = at("70")
c, h = card("pc-ayub", "olhar_ayub", 1000, top=210, y0=0, y1=530)
mark(h, at("sites", 1, S_STAT), 0.45)
SC.append(scene("sc-stat", S_STAT, F_END, f'''<div id="st-row"><div id="st-num">≈<span id="st-n">0</span>%</div><div id="st-lab">dos sites<br>usam PHP<small>FONTE: OLHAR DIGITAL</small></div></div>
        {c}'''))
JS.append(f'''      // contador 0 -> 70
      pop("#st-row", {S_STAT}, 0.28);
      for (let n = 0; n <= 70; n += 2) tl.set("#st-n", {{ textContent: String(n) }}, {S_STAT} + 0.05 + (n / 70) * {round(max(0.5, T_70 - S_STAT + 0.25), 3)});
      tl.set("#st-n", {{ textContent: "70" }}, {round(T_70 + 0.32, 3)});
      rise("#pc-ayub", {S_STAT + 0.3}, 0.3);''')

# ---------- sobreposições em tela cheia ----------
NAME_S, NAME_D = 0.35, round(S_CVE + 3.6 - 0.35, 3)
JS.append(f'''      slideIn("#nametag", {NAME_S}, 0.3);
      slideIn("#cd-cur", {F_CUR}, 0.3);
      slideIn("#cd-com", {F_COM}, 0.3);
      gsap.set(["#cr-h", "#cr-hx", "#cr-i"], {{ opacity: 0 }});
      slideIn("#cr-h", {at("humanos") - 0.1}, 0.28);
      slideIn("#cr-i", {at("anos", 1, F_COM)}, 0.28);
      pop("#cr-hx", {at("percebido")}, 0.28);
      slideIn("#fontes", {F_END}, 0.3);
      pop("#c-follow", {at("imagine") + 0.2}, 0.36);''')

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    sp = "".join(f'<span class="cw{" k" if w["k"] else ""}" id="w{gi}_{wi}">{w["x"]}</span>' for wi, w in enumerate(g["w"]))
    caps_dom.append(f'          <div class="cg" id="g{gi}">{sp}</div>')

# ---------- SFX ----------
SFX_DUR = {"whoosh-short": 0.57, "whoosh": 0.57, "click-soft": 0.37, "click": 0.37, "pop": 0.72, "ping": 1.32,
           "sparkle": 1.8, "typing": 1.54, "impact-bass-1": 1.2}
sfx = [(T_UOL, "pop", 0.24), (T_BBC, "pop", 0.24), (S_CVE, "whoosh-short", 0.26), (at("executar"), "click-soft", 0.2),
       (S_REQ, "whoosh-short", 0.26), (T_SEND, "whoosh-short", 0.22), (T_RUN, "click", 0.26), (F_JA, "impact-bass-1", 0.3),
       (S_GOV, "whoosh-short", 0.26), (at("governos"), "click-soft", 0.2), (T_CH, "pop", 0.18), (S_BR, "whoosh-short", 0.26),
       (S_ANA, "whoosh-short", 0.22), (at("Anatel"), "click-soft", 0.2), (S_FIX, "whoosh-short", 0.26), (T_ST, "pop", 0.26),
       (S_TERM, "whoosh-short", 0.24), (T_TY0, "typing", 0.24), (T_OK, "ping", 0.24), (F_CUR, "whoosh-short", 0.24),
       (S_DEC, "whoosh-short", 0.24), (S_IA, "whoosh-short", 0.24), (at("inteligência"), "click-soft", 0.2),
       (F_COM, "whoosh-short", 0.22), (at("percebido"), "click", 0.22), (S_STAT, "whoosh-short", 0.26), (T_70 + 0.32, "sparkle", 0.2),
       (F_END, "whoosh-short", 0.22), (at("estrago"), "impact-bass-1", 0.26), (at("imagine") + 0.2, "pop", 0.24)]
tags, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "caps": data["caps"], "marks": marks, "premarked": premarked}
r = lambda v: f"{v:.3f}"
fill = {
    "%%DUR%%": r(DUR),
    "%%SPLIT_Y%%": str(SPLIT_Y),
    "%%SCENES%%": "\n".join(SC),
    "%%NAME_S%%": r(NAME_S), "%%NAME_D%%": r(NAME_D),
    "%%CUR_S%%": r(F_CUR), "%%CUR_D%%": r(S_DEC - F_CUR),
    "%%COM_S%%": r(F_COM), "%%COM_D%%": r(S_STAT - F_COM),
    "%%END_S%%": r(F_END), "%%END_D%%": r(DUR - F_END),
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags),
    "%%JS%%": "\n".join(JS),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read()
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "| marcas", len(marks), "| sfx", len(tags))
print("cam", cam)
