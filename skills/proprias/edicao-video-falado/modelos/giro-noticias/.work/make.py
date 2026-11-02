"""Monta ../index.html a partir de tpl.html + data.json (captions.py) + segs.json (build.py) + prints.json + chin.json (chin.py).

Layout desde 28/10/2026 (pedido do usuário: "não quero que fique cortando mais a tela"): nada de split. Ele fica sempre em tela
cheia no estúdio; tags e prints flutuam no espaço livre entre o queixo e a legenda, sobre o tronco, e nunca cobrem o rosto nem a
legenda. Quando o print não cabe, a câmera sobe (até DMAX px) para abrir espaço, e o piso escuro do estúdio esconde a borda de
baixo do vídeo. Se ainda assim não couber, o print vai para tela cheia ("cover") com o estúdio desfocado atrás.
O queixo vem de chin.py (detector de rosto a 5 q/s na fala montada).
Uso: FALA=fala_estudio.mp4 HANDLE=@seu_perfil python3 -I make.py

O que muda a cada episódio está nas seções marcadas "POR EPISÓDIO" (blocos, climas, fontes, tags, prints, texto das fontes).
Os valores que estão lá são do exemplo (um giro com 5 notícias) e servem de modelo: troque pelos do seu roteiro.
"""
import json, math, os, re, statistics, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))["segments"]
P = json.load(open(os.path.join(W, "prints.json")))
CH = json.load(open(os.path.join(W, "chin.json")))
DUR_V = data["dur"]
HANDLE = os.environ.get("HANDLE", "@seu_perfil")
HOLD = 2.2                                       # tela final escura com a tag da pergunta, o @ e as fontes (≥ 2 s para ler)
DUR = round(DUR_V + HOLD, 3)
OUT = [round(s["out"], 3) for s in segs]

CAP_Y = 1428                                     # topo da faixa da legenda (110 px): fixa no vídeo todo
CARD_BOTTOM = 1404                               # tags e prints assentam aqui, logo acima da legenda
CARD_X, CARD_W, STRIP = 60, 900, 52              # 120 px livres à direita (botões do Reels/TikTok)
GAP = 34                                         # folga abaixo do queixo
DMAX, TOPMIN = 340, 120                          # câmera sobe no máx. 340 px; o alto do rosto não passa de y = 120 (com reframe.py: DMAX = 0)
ORIGIN = 1056                                    # origem do zoom da câmera (altura do queixo: o zoom não empurra o queixo)
ZALT = 1.035                                     # micro-zoom alternado nos cortes (com reframe.py: 1.0, ele já alterna os planos)
FLOOR0 = 1740                                    # piso escuro: começa aqui com a câmera parada e sobe junto com ela
COVER_MIN = 230                                  # abaixo disso o print vai para tela cheia
COV_TOP, COV_W, COV_MAXH = 330, 960, 1000


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
    return min(OUT, key=lambda o: abs(o - t))


# ---------- rosto (chin.json): mediana de 1 s contra detecção falsa, pior caso no intervalo ----------
F = CH["fps"]
_box = CH["box"]


def _smooth(vals):
    return [statistics.median(vals[max(0, i - 2):i + 3]) for i in range(len(vals))]


CHIN = _smooth([b[1] + 1.12 * b[3] for b in _box])
FTOP = _smooth([b[1] for b in _box])


def chin_max(t0, t1):
    i0, i1 = max(0, int((t0 - 0.2) * F)), min(len(CHIN), int(t1 * F) + 1)
    return max(CHIN[i0:i1]) + 8                  # + o que o micro-zoom empurra


def ftop_min(t0, t1):
    i0, i1 = max(0, int(t0 * F)), min(len(FTOP), int(t1 * F) + 1)
    return min(FTOP[i0:i1])


# ---------- POR EPISÓDIO: blocos (início = corte da fala) ----------
def seg_of(t):                                     # corte onde começa o trecho que contém o instante t
    return max(o for o in OUT if o <= t + 1e-3)


N1 = 0.0                                           # notícia 1 — Binance (a 1ª frase já é o gancho: TecMundo/Estadão 29/10, Fox Business 29/10)
N2 = seg_of(at("acabou"))                          # notícia 2 — anúncios no Modo IA do Google, Brasil até dezembro (Canaltech 29/10)
N3 = seg_of(at("Gemini"))                          # notícia 3 — Gemini edita PDF, planilha e documento no chat (Olhar Digital 29/10)
N4 = seg_of(at("chip"))                            # notícia 4 — TIM Brasil "não é estratégica" para a Poste Italiane (BPMoney 27/10, Teletime 27/07)
N5 = seg_of(at("General"))                         # notícia 5 — GM paga US$ 220 mi por vender dados de direção (TechCrunch 29/10, AG do Colorado 29/10)
END = seg_of(at("Qual"))                           # pergunta final + CTA
print("blocos", dict(N2=N2, N3=N3, N4=N4, N5=N5, END=END, DUR=DUR))
STORIES = [("n1", 0.0, N2), ("n2", N2, N3), ("n3", N3, N4), ("n4", N4, N5), ("n5", N5, END), ("cta", END, DUR_V)]

# ---------- POR EPISÓDIO: clima de cor por notícia (o mesmo do estudio.json: fitas de LED e brilho dos prints) ----------
CLIMA = {"n1": "#ff3b4e", "n2": "#c084fc", "n3": "#38bdf8", "n4": "#ffb020", "n5": "#ff2d55", "cta": "#5eead4"}
SRC = {"tm": ("estadao.com.br/tecmundo", "29/10/2026"), "fox": ("foxbusiness.com", "29/10/2026"), "ctg": ("canaltech.com.br", "29/10/2026"),
       "od": ("olhardigital.com.br", "29/10/2026"), "bpm": ("bpmoney.com.br", "27/10/2026"), "ttl": ("teletime.com.br", "27/07/2026"),
       "tcg": ("techcrunch.com", "29/10/2026"), "coag": ("coag.gov", "29/10/2026")}
DARK = {"tcg_card"}                                # título branco sobre o verde do TechCrunch: grifo sem multiply

K = "#0b0d10"
ICON = {
    "siren": '<svg viewBox="0 0 24 24" class="ico"><path d="M6 18v-5a6 6 0 0 1 12 0v5z" fill="#e11d2e"/><path d="M9.5 13a2.5 2.5 0 0 1 2.5-2.5" stroke="#fff" stroke-width="1.6" fill="none" stroke-linecap="round"/><rect x="4" y="18" width="16" height="3.2" rx="1" fill="#0b0d10"/><path d="M12 1.8v2.4M4.3 4.6l1.6 1.6M19.7 4.6l-1.6 1.6M1.8 11h2.3M19.9 11h2.3" stroke="#0b0d10" stroke-width="2.2" stroke-linecap="round"/></svg>',
    "browser": (f'<svg viewBox="0 0 24 24" class="ico"><rect x="2.5" y="4" width="19" height="16" rx="2.5" fill="none" stroke="{K}" stroke-width="2.2"/>'
                f'<path d="M2.5 8.6h19" stroke="{K}" stroke-width="2.2"/><circle cx="5.6" cy="6.3" r="0.9" fill="{K}"/><circle cx="8.4" cy="6.3" r="0.9" fill="{K}"/>'
                f'<path d="M12 11.5l4.2 1.6v2.6c0 2-1.8 3.3-4.2 4-2.4-.7-4.2-2-4.2-4v-2.6z" fill="{K}"/></svg>'),
    "laptop": (f'<svg viewBox="0 0 24 24" class="ico"><rect x="4.5" y="4.5" width="15" height="10.5" rx="1.6" fill="none" stroke="{K}" stroke-width="2.2"/>'
               f'<path d="M1.8 18.3h20.4l-1.4 1.9H3.2z" fill="{K}"/></svg>'),
    "car": (f'<svg viewBox="0 0 24 24" class="ico"><path d="M3.5 15.5v-3.2l2.2-5.1a2 2 0 0 1 1.8-1.2h9a2 2 0 0 1 1.8 1.2l2.2 5.1v3.2z" fill="{K}"/>'
            f'<rect x="3.5" y="15" width="17" height="2.6" rx="1" fill="{K}"/><circle cx="7.4" cy="17.6" r="2.1" fill="{K}"/><circle cx="16.6" cy="17.6" r="2.1" fill="{K}"/>'
            f'<path d="M7.6 11.4l1.3-3.1h6.2l1.3 3.1z" fill="#ffe500"/></svg>'),
    "chip": (f'<svg viewBox="0 0 24 24" class="ico"><rect x="6" y="6" width="12" height="12" rx="2" fill="{K}"/><rect x="9.2" y="9.2" width="5.6" height="5.6" rx="1" fill="#ffe500"/>'
             f'<path d="M9 2.5v3M12 2.5v3M15 2.5v3M9 18.5v3M12 18.5v3M15 18.5v3M2.5 9h3M2.5 12h3M2.5 15h3M18.5 9h3M18.5 12h3M18.5 15h3" stroke="{K}" stroke-width="1.8" stroke-linecap="round"/></svg>'),
    "chat": '<svg viewBox="0 0 24 24" class="ico"><path d="M3.5 4.5h17v12H9.5l-6 4.5z" fill="#0b0d10"/><circle cx="8.5" cy="10.5" r="1.4" fill="#ffe500"/><circle cx="12" cy="10.5" r="1.4" fill="#ffe500"/><circle cx="15.5" cy="10.5" r="1.4" fill="#ffe500"/></svg>',
    "phone": (f'<svg viewBox="0 0 24 24" class="ico"><rect x="6.2" y="1.8" width="11.6" height="20.4" rx="2.4" fill="{K}"/>'
              f'<rect x="7.9" y="4.4" width="8.2" height="13.4" rx="0.8" fill="#ffe500"/><circle cx="12" cy="19.7" r="1" fill="#ffe500"/></svg>'),
    "pix": (f'<svg viewBox="0 0 24 24" class="ico"><path d="M12 2.2l4.2 4.2-4.2 4.2-4.2-4.2zM12 13.4l4.2 4.2-4.2 4.2-4.2-4.2z" fill="{K}"/>'
            f'<path d="M6.4 7.8l4.2 4.2-4.2 4.2-4.2-4.2zM17.6 7.8l4.2 4.2-4.2 4.2-4.2-4.2z" fill="{K}"/><circle cx="12" cy="12" r="1.3" fill="{K}"/></svg>'),
    "server": (f'<svg viewBox="0 0 24 24" class="ico"><rect x="3" y="3.5" width="18" height="7" rx="1.6" fill="{K}"/><rect x="3" y="13.5" width="18" height="7" rx="1.6" fill="{K}"/>'
               f'<circle cx="6.8" cy="7" r="1.2" fill="#ffe500"/><circle cx="6.8" cy="17" r="1.2" fill="#ffe500"/>'
               f'<path d="M11 7h7M11 17h7" stroke="#ffe500" stroke-width="1.6" stroke-linecap="round"/></svg>'),
    "play": f'<svg viewBox="0 0 24 24" class="ico"><path d="M7 4.5v15l12.5-7.5z" fill="{K}"/></svg>',
    "search": (f'<svg viewBox="0 0 24 24" class="ico"><circle cx="10" cy="10" r="6.2" fill="none" stroke="{K}" stroke-width="2.6"/>'
               f'<path d="M14.6 14.6l6 6" stroke="{K}" stroke-width="3" stroke-linecap="round"/><path d="M7.4 10h5.2" stroke="#ffe500" stroke-width="2.2" stroke-linecap="round"/></svg>'),
    "file": (f'<svg viewBox="0 0 24 24" class="ico"><path d="M5.5 2.5h9l4 4v15h-13z" fill="{K}"/><path d="M14.5 2.5v4h4" fill="none" stroke="#ffe500" stroke-width="1.6"/>'
             f'<path d="M8.5 11.5h7M8.5 15h7M8.5 18.5h4.5" stroke="#ffe500" stroke-width="1.8" stroke-linecap="round"/></svg>'),
    "plus": f'<svg viewBox="0 0 24 24" class="ico"><path d="M12 5v14M5 12h14" stroke="{K}" stroke-width="3.2" stroke-linecap="round"/></svg>',
}
DOC = ('<svg viewBox="0 0 24 24" class="ico"><path d="M6 3h8l4 4v14H6z" fill="none" stroke="#aab2bc" stroke-width="2" stroke-linejoin="round"/>'
       '<path d="M9 12h6M9 16h6" stroke="#aab2bc" stroke-width="2" stroke-linecap="round"/></svg>')

# ---------- POR EPISÓDIO: o que entra na faixa livre: tags (abertura de cada notícia) e prints reais ----------
# tags: (story, início, fim, ícone, tag principal, sub-lettering) — o texto das tags nunca exagera o que as fontes dizem
TAG_H = 168
TAGS = [
    ("n1", 0.0, round(at("maior") - 0.1, 3), "siren", "[ ATAQUE HACKER NA BINANCE ]", "SAQUES SUSPENSOS ÀS PRESSAS"),
    ("n2", N2, round(at("respostas") - 0.1, 3), "search", "[ ANÚNCIOS NA IA DO GOOGLE ]", "BRASIL ENTRA NA LISTA ATÉ DEZEMBRO"),
    ("n3", N3, round(at("Agora", 1, N3) - 0.1, 3), "file", "[ GEMINI EDITA ARQUIVOS ]", "PDF, PLANILHA E DOC DIRETO NO CHAT"),
    ("n4", N4, round(at("controladora") - 0.1, 3), "phone", "[ ATENÇÃO, CLIENTE TIM ]", "NOVA DONA: BRASIL NÃO É ESTRATÉGICO"),
    ("n5", N5, round(at("220") - 0.1, 3), "car", "[ GM PAGA US$ 220 MILHÕES ]", "ACORDO POR VENDER DADOS DE MOTORISTAS"),
    ("cta", END, DUR, "chat", "[ QUAL TE PEGOU DE SURPRESA? ]", "COMENTA E COMPARTILHA COM A GALERA"),
]
NUM = {"n1": "1/5", "n2": "2/5", "n3": "3/5", "n4": "4/5", "n5": "5/5"}
TOPIC = {"n1": ("siren", "CRIPTO"), "n2": ("search", "GOOGLE"), "n3": ("file", "IA"), "n4": ("phone", "TELECOM"), "n5": ("car", "PRIVACIDADE")}

# POR EPISÓDIO — prints: (id, chave do prints.json, story, início, fim, y0, y1, [(trecho grifado, instante, duração)]); y0/y1 no vão entre linhas (sem meia linha)
T_PROD = round(at("produtos") - 0.25, 3)
T_MEXER = seg_of(at("mexer"))
CARDS = [
    ("pc-tm", "tm_card", "n1", round(at("maior") - 0.1, 3), round(at("Eles") - 0.1, 3), 0, None,
     [("Binance confirma ataque hacker bilionário", at("maior") + 0.15, 0.9), ("Saques foram suspensos temporariamente", at("suspendeu") - 0.05, 0.8)]),
    ("pc-fox", "fox_card", "n1", round(at("Eles") - 0.1, 3), N2, 0, None,
     [("pledging to cover", at("cobrir") - 0.1, 0.6), ("$6.3B", at("perdas") - 0.05, 0.4)]),
    ("pc-ctg", "ctg_card", "n2", round(at("respostas") - 0.1, 3), round(at("patrocinados") - 0.1, 3), 0, None,
     [("Google vai colocar anúncios no Modo IA", at("anúncios") - 0.15, 0.9)]),
    ("pc-ctg2", "ctg_lede", "n2", round(at("patrocinados") - 0.1, 3), T_PROD, 0, 500,
     [("incluindo o Brasil", at("Brasil", 1, N2) - 0.05, 0.5), ("até dezembro", at("dezembro") - 0.1, 0.5)]),
    ("pc-ctg3", "ctg_ads", "n2", T_PROD, N3, 0, None, [("dentro ou ao lado das respostas", at("misturados") - 0.05, 0.9)]),
    ("pc-od", "od_lede", "n3", round(at("Agora", 1, N3) - 0.1, 3), N4, 0, None,
     [("criem, visualizem e editem documentos diretamente nas conversas", at("abrir") - 0.1, 1.2),
      ("elimina a necessidade de baixar arquivos", at("baixar") - 0.1, 0.8)]),
    ("pc-bpm", "bpm_card", "n4", round(at("controladora") - 0.1, 3), T_MEXER, 18, None,
     [("não vê TIM Brasil como ativo estratégico", at("estratégica") - 0.45, 0.9)]),
    ("pc-ttl", "ttl_lede", "n4", T_MEXER, N5, 0, None, [("61,87 milhões usuários de telefonia móvel", at("60") - 0.05, 0.8)]),
    ("pc-tcg", "tcg_card", "n5", round(at("220") - 0.1, 3), round(at("vender") - 0.1, 3), 0, 420, [("GM reaches $220M settlement", at("220") + 0.05, 0.7)]),
    ("pc-coag", "coag_data", "n5", round(at("vender") - 0.1, 3), END, 0, 606,
     [("how many times they braked or accelerated quickly", at("aceleração") - 0.1, 1.0),
      ("sometimes increasing their premiums", at("aumentando") - 0.05, 0.9)]),
]

def print_h(key, y0, y1):
    p = P[key]
    y1 = p["h"] if y1 is None else y1
    return round((y1 - y0) * CARD_W / p["w"]) + STRIP


# ---------- câmera: quanto sobe em cada notícia para o maior print caber entre o queixo e a legenda ----------
DCAM = {}
for sid, s0, s1 in STORIES:
    need = [chin_max(c[3], c[4]) + GAP + print_h(c[1], c[5], c[6]) - CARD_BOTTOM for c in CARDS if c[2] == sid]
    need += [chin_max(t[1], t[2]) + GAP + TAG_H - CARD_BOTTOM for t in TAGS if t[0] == sid]
    room = ftop_min(s0, s1) - TOPMIN                  # o alto do rosto não pode subir demais
    DCAM[sid] = math.ceil(max(0, min(DMAX, room, max(need + [0]))))
print("câmera sobe", DCAM)


def story_of(t):
    return next(sid for sid, s0, s1 in STORIES if s0 - 1e-3 <= t < s1 - 1e-3) if t < DUR_V else "cta"


# ---------- prints ----------
marks, cards, MARK_T, COVERS = [], [], [], []
SC, JS = [], []


def card_html(cid, key, sid, t0, t1, y0, y1, hl):
    p = P[key]
    s = CARD_W / p["w"]
    y1 = p["h"] if y1 is None else y1
    full_h = round((y1 - y0) * s)
    D = DCAM[sid]
    top_min = chin_max(t0, t1) - D + GAP             # nunca acima do queixo
    avail = int(CARD_BOTTOM - top_min)
    cover = avail < min(COVER_MIN, full_h + STRIP)
    if cover:
        shot_h = min(full_h, COV_MAXH)
        top = COV_TOP
        COVERS.append([round(t0, 3), round(t1, 3)])
    else:
        shot_h = min(full_h, avail - STRIP)
        top = CARD_BOTTOM - shot_h - STRIP
    dom, dt = SRC[key.split("_")[0]]
    ico, topic = TOPIC[sid]
    dark = key in DARK
    out = [f'<div class="pc{" dk" if dark else ""}{" cv" if cover else ""}" id="{cid}" style="top: {top}px; --c: {CLIMA[sid]}">'
           f'<div class="pc-src"><span class="tp">{ICON[ico]}<b>{topic}</b></span>{DOC}<b>{dom}</b><span class="dt">{dt}</span></div>',
           f'<div class="pc-shot" style="height: {shot_h}px"><div class="pc-in" style="height: {full_h}px">'
           f'<img src="assets/img/{p["file"]}" alt="" style="width: {CARD_W}px; top: {round(-y0 * s)}px" />']
    groups = {}
    for i, q in enumerate(p["hls"]):
        if q["y"] + q["h"] < y0 or q["y"] > y1:
            continue
        hid = f"{cid}-h{i}"
        groups.setdefault(q["text"], []).append((hid, q["w"] * s))
        out.append(f'<div class="hl" id="{hid}" style="left: {round(q["x"] * s - 4)}px; top: {round((q["y"] - y0) * s + 2)}px; '
                   f'width: {round(q["w"] * s + 8)}px; height: {round(q["h"] * s - 2)}px"></div>')
    out.append("</div></div></div>")
    c = {"id": cid, "t": round(t0, 3), "d": round(t1 - t0, 3), "cover": cover}
    if full_h > shot_h:
        c.update(pan=full_h - shot_h, p0=round(t0 + 0.5, 3), p1=round(t1 - 0.2, 3))
    cards.append(c)
    for text, t, d in hl:
        ids = next(v for k, v in groups.items() if k.startswith(text))
        sw = sum(w for _, w in ids)
        MARK_T.append(round(t, 3))
        cur = t
        for hid, w in ids:
            dd = round(max(0.08, d * w / sw), 3)
            marks.append([hid, round(cur, 3), dd])
            cur += dd
    return "".join(out), top, shot_h + STRIP, cover


plan = []
for cid, key, sid, t0, t1, y0, y1, hl in CARDS:
    html, top, h, cover = card_html(cid, key, sid, t0, t1, y0, y1, hl)
    SC.append(f'      <div id="sc-{cid[3:]}" class="scene clip" data-start="{t0:.3f}" data-duration="{t1 - t0:.3f}" data-track-index="2">\n'
              f'        {html}\n      </div>')
    plan.append((cid, sid, t0, t1, top, h, "COVER" if cover else ""))

# ---------- tags (assentam na mesma faixa, logo acima da legenda) ----------
tags_dom = []
for sid, t0, t1, ico, main, sub in TAGS:
    top = CARD_BOTTOM - TAG_H
    chin = chin_max(t0, min(t1, DUR_V)) - DCAM[sid]
    plan.append((f"tag-{sid}", sid, t0, t1, top, TAG_H, "" if chin + GAP <= top else f"QUEIXO {int(chin)}"))
    num = f'<span class="num">{NUM[sid]}</span>' if sid in NUM else ""
    inner = (f'<div class="tg-main" id="tm-{sid}">{ICON[ico]}<span>{main}</span>{num}</div>'
             f'<div class="tg-sub{" long" if len(sub) > 34 else ""}" id="ts-{sid}">{sub}</div>')
    extra = ""
    if sid == "cta":
        extra = (f'\n        <div id="fontes">FONTES: <b>TECMUNDO/ESTADÃO · FOX BUSINESS · CANALTECH · OLHAR DIGITAL · BPMONEY · TELETIME · TECHCRUNCH · PROCURADORIA DO COLORADO</b></div>'
                 f'\n        <div class="slot" style="top: 1050px"><div class="chip" id="c-follow"><span class="plus">{ICON["plus"]}</span>'
                 f'<div id="end-follow">Segue <span class="h" data-var-text="handle">{HANDLE}</span> pra não perder</div></div></div>')
    tags_dom.append(f'      <div id="tag-{sid}-w" class="ov clip" data-start="{t0:.3f}" data-duration="{t1 - t0:.3f}" data-track-index="4">\n'
                    f'        <div class="tag" id="tag-{sid}" style="top: {top}px; --c: {CLIMA[sid]}">{inner}</div>{extra}\n      </div>')
    JS.append(f'      slam("#tm-{sid}", {round(t0 + 0.04, 3)}, 0.24);')
    JS.append(f'      slideIn("#ts-{sid}", {round(t0 + 0.16, 3)}, 0.26);')
T_FOLLOW = round(DUR_V + 0.05, 3)                 # chip e fontes só na tela escura: enquanto ele fala não há espaço sem cobrir o queixo
JS.append(f'''      gsap.set(["#fontes", "#c-follow"], {{ opacity: 0 }});
      rise("#fontes", {round(DUR_V - 0.25, 3)}, 0.3);
      pop("#c-follow", {T_FOLLOW}, 0.36);''')
for c in cards:
    JS.append(f'      enter("#{c["id"]}", {c["t"]});')

for row in sorted(plan, key=lambda r: r[2]):
    print(f"  {row[0]:9s} {row[1]:4s} {row[2]:6.2f}-{row[3]:6.2f}  top {row[4]:5d}  h {row[5]:4d}  {row[6]}")

# ---------- câmera: sobe na troca de notícia (0,45 s), micro-zoom alternado nos cortes ----------
cam, last_t, alt = [], -9, False
story_t = {s0: sid for sid, s0, _ in STORIES}
for t in sorted(set(OUT) | set(story_t)):
    if t >= DUR_V:
        continue
    sid = story_of(t)
    if t in story_t:
        alt = False
        cam.append([round(t, 3), 1.0, DCAM[sid], 1])
    else:
        if t - last_t < 0.6:
            continue
        alt = not alt
        cam.append([round(t, 3), ZALT if alt else 1.0, DCAM[sid], 0])
    last_t = t

# ---------- legenda (DOM estático) ----------
caps_dom = []
for gi, g in enumerate(data["caps"]):
    sp = "".join(f'<span class="cw{" k" if w["k"] else ""}" id="w{gi}_{wi}">{w["x"]}</span>' for wi, w in enumerate(g["w"]))
    caps_dom.append(f'          <div class="cg" id="g{gi}">{sp}</div>')

# ---------- SFX ----------
SFX_DUR = {"whoosh-short": 0.57, "whoosh": 0.57, "click-soft": 0.37, "click": 0.37, "pop": 0.72, "ping": 1.32,
           "sparkle": 1.8, "impact-bass-1": 2.1, "impact-bass-2": 2.59, "key-press": 0.43, "glitch-1": 0.55}
sfx = [(0.0, "impact-bass-2", 0.55), (0.06, "whoosh-short", 0.26)]
for sid, t0, *_ in TAGS:
    sfx.append((t0, "whoosh", 0.4))
for c in cards:
    if all(abs(c["t"] - t) > 0.15 for t, *_ in sfx):
        sfx.append((c["t"], "whoosh-short", 0.18))
for t in MARK_T:                                    # clique no instante exato do grifo
    sfx.append((t, "click-soft", 0.26))
sfx += [(T_FOLLOW, "pop", 0.26)]
tags_a, lanes = [], {}
for i, (t, name, vol) in enumerate(sorted(sfx)):
    d = min(SFX_DUR[name], round(DUR - t, 3))
    lane = next(k for k in range(11, 30) if lanes.get(k, -1) <= t)
    lanes[lane] = t + d
    tags_a.append(f'      <audio id="sfx{i:02d}" src="assets/sfx/{name}.mp3" data-start="{t:.3f}" data-duration="{d}" '
                  f'data-track-index="{lane}" data-volume="{vol}"></audio>')

D = {"cam": cam, "caps": data["caps"], "marks": marks, "cards": cards, "covers": COVERS, "endfade": round(DUR_V - 0.35, 3), "durv": DUR_V}
fill = {
    "%%DUR%%": f"{DUR:.3f}", "%%FALA%%": os.environ.get("FALA", "fala.mp4"), "%%DURV%%": f"{DUR_V:.3f}",
    "%%CAP_Y%%": str(CAP_Y), "%%ORIGIN%%": str(ORIGIN), "%%FLOOR0%%": str(FLOOR0), "%%CARD_X%%": str(CARD_X), "%%CARD_W%%": str(CARD_W),
    "%%COV_W%%": str(COV_W), "%%STRIP%%": str(STRIP),
    "%%SCENES%%": "\n".join(SC),
    "%%TAGS%%": "\n".join(tags_dom),
    "%%HANDLE%%": (f'      <div id="handle-w" class="ov clip" data-start="0" data-duration="{END:.3f}" data-track-index="7">'
                   f'<div id="handle" data-var-text="handle">{HANDLE}</div></div>'),
    "%%CAPS_DOM%%": "\n".join(caps_dom),
    "%%SFX%%": "\n".join(tags_a),
    "%%JS%%": "\n".join(JS),
    "%%DATA%%": json.dumps(D, ensure_ascii=False),
}
html = open(os.path.join(W, "tpl.html")).read().replace('"default":"@seu_perfil"', f'"default":"{HANDLE}"')
for k, v in fill.items():
    html = html.replace(k, v)
assert "%%" not in html, [l for l in html.splitlines() if "%%" in l][:3]
open(os.path.join(W, "..", "index.html"), "w").write(html)
print("dur", DUR, "| prints", len(cards), "| cover", COVERS, "| marcas", len(marks), "| sfx", len(tags_a))
