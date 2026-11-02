"""
Biblioteca de modelos de badge (origem: Reel 3 — Sailfish OS no Xperia XZ2, 2026-10-17).

Cada modelo define:
  - fields  : campos de texto/listas com valores padrão
  - cues    : "deixas" (segundos ABSOLUTOS no vídeo) que disparam cada revelação;
              quando faltar uma deixa, usa start + offset padrão
  - html(f) : HTML do badge
  - beats(f, cue, start, end) : lista de (seletor, tempo, tipo, extra) compilada para GSAP
  - layout  : largura (px ou "max-content"), xs/escalas permitidas, posição de rascunho,
              "zone" sugerida e se ignora detecção de rosto (cenas sem pessoa)

Marcação em textos: **trecho** vira <b>trecho</b> (destaque na cor de acento).
"""
import html as _html
import re

ACCENTS = {"cyan": "grad-cyan", "green": "grad-green", "amber": "grad-amber"}
LED = {
    "red": ("radial-gradient(circle at 35% 30%, #ffd1d9, #ff3355 55%, #8a0f23)", "0 0 34px 6px rgba(255,51,85,.7)"),
    "blue": ("radial-gradient(circle at 35% 30%, #d8ecff, #3d8bff 55%, #0b2e7a)", "0 0 44px 10px rgba(61,139,255,.85)"),
    "green": ("radial-gradient(circle at 35% 30%, #dcffe9, #2fd47a 55%, #0b5a2e)", "0 0 44px 10px rgba(74,222,128,.85)"),
    "amber": ("radial-gradient(circle at 35% 30%, #fff1cf, #ffb547 55%, #7a4a07)", "0 0 44px 10px rgba(255,181,71,.85)"),
}
DOTS = ("cyan", "green", "amber", "violet", "blue")


def md(s):
    """Escapa HTML e converte **x** em <b>x</b>."""
    s = _html.escape(str(s))
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def acc(text, color="cyan"):
    return f'<span class="{ACCENTS.get(color, "grad-cyan")}">{md(text)}</span>' if text else ""


def kicker(text, dot="cyan", extra=""):
    if not text:
        return ""
    dot = dot if dot in DOTS else "cyan"
    return f'<div class="kicker"><span class="dot {dot}{extra}"></span>{md(text)}</div>'


def _c(cue, name, start, off):
    v = cue.get(name)
    return float(v) if v is not None else round(start + off, 3)


MODELS = {}


def model(name, desc, zone, fields, width=992, xs=("center", "left", "right"),
          scales=(1.0, 0.92, 0.85, 0.78, 0.72), ignore_faces=True, draft_y=300, y_pref=None):
    def deco(factory):
        html_fn, beats_fn = factory()
        MODELS[name] = dict(name=name, desc=desc, zone=zone, fields=fields, html=html_fn, beats=beats_fn,
                            width=width, xs=list(xs), scales=list(scales), ignore_faces=ignore_faces,
                            draft_y=draft_y, y_pref=y_pref)
        return factory
    return deco


# 1 ─ pill-banner: banner fino (~70px) para close de rosto, acima do cabelo
@model("pill-banner", "Banner fino de 1 linha (chip + título). Para close de rosto: cabe na faixa acima da cabeça.",
       "topo, acima da cabeça (~70px de altura)",
       {"chip": "TENTATIVA #2", "chip_color": "red", "accent": "SAILFISH OS", "accent_color": "cyan", "title": "no Xperia XZ2"},
       width="max-content", ignore_faces=False, draft_y=150)
def _():
    def h(f):
        chip = f'<span class="chip {f["chip_color"]} sm">{md(f["chip"])}</span>' if f.get("chip") else ""
        return f'<div class="pillb">{chip}<span class="pt">{acc(f["accent"], f["accent_color"])} {md(f["title"])}</span></div>'

    def b(f, cue, s, e):
        out = [(".pt", _c(cue, "title", s, 0.25), "in", None)]
        if f.get("chip"):
            out.insert(0, (".chip", _c(cue, "chip", s, 0.1), "in", None))
        return out
    return h, b


# 2 ─ title-chips: título grande + linha de chips (specs, números)
@model("title-chips", "Título grande + linha de chips (specs, números, tags). ~180px.",
       "topo ou base livre", {"title": "MINI SERVIDOR", "accent": "LINUX", "accent_color": "green",
                              "chips": ["Xperia **XZ2**", "Snapdragon **845**", "**4 GB** RAM"]},
       ignore_faces=False, draft_y=150)
def _():
    def h(f):
        chips = "".join(f"<span>{md(c)}</span>" for c in f["chips"])
        return (f'<div class="glass slim"><div class="t2">{md(f["title"])} {acc(f["accent"], f["accent_color"])}</div>'
                f'<div class="chips">{chips}</div></div>')

    def b(f, cue, s, e):
        return [(".t2", _c(cue, "title", s, 0.3), "in", None), (".chips span", _c(cue, "chips", s, 1.5), "stagger", None)]
    return h, b


# 3 ─ swap: antes → depois (risca o antigo, destaca o novo)
@model("swap", "Antes → depois: risca o antigo e destaca o novo (trocas, migrações). ~200px.",
       "topo ou base livre", {"kicker": "O PLANO", "dot": "violet", "old": "Android", "new": "Sailfish OS",
                              "new_sub": "GNU/Linux de verdade"}, ignore_faces=False, draft_y=150)
def _():
    def h(f):
        return (f'<div class="glass slim">{kicker(f["kicker"], f["dot"])}<div class="swap sm">'
                f'<div class="os old"><span class="strike">{md(f["old"])}</span></div><div class="arrow big">→</div>'
                f'<div class="os new">{md(f["new"])}<small>{md(f["new_sub"])}</small></div></div></div>')

    def b(f, cue, s, e):
        return [(".kicker", _c(cue, "kicker", s, 0.05), "in", None), (".old", _c(cue, "old", s, 0.3), "in", None),
                (".old .strike", _c(cue, "strike", s, 1.3), "strike", None), (".big", _c(cue, "new", s, 1.8) - 0.22, "in", None),
                (".new", _c(cue, "new", s, 1.8), "pop", None)]
    return h, b


# 4 ─ keycaps-led: combinação de teclas/ações + LED que muda de cor
@model("keycaps-led", "Teclas/ações combinadas + LED de status que troca de cor no momento citado. ~380px.",
       "espaço livre grande (parede, janela)", {"kicker": "MODO FASTBOOT", "dot": "blue", "keys": ["VOL **+**", "CABO USB"],
                                                "led_from": "red", "led_to": "blue", "from_text": "vermelho…",
                                                "to_text": "AZUL = fastboot ativo"}, draft_y=200)
def _():
    def h(f):
        keys = '<span class="plus">+</span>'.join(f'<span class="key">{md(k)}</span>' for k in f["keys"])
        bg, sh = LED[f["led_from"]]
        return (f'<div class="glass">{kicker(f["kicker"], f["dot"])}<div class="keys">{keys}</div>'
                f'<div class="ledrow"><div class="led"><span class="bulb" style="background:{bg};box-shadow:{sh}"></span>'
                f'<span class="lbl">LED</span></div><div class="ledtxt"><span class="t-red">{md(f["from_text"])}</span>'
                f'<span class="t-blue">{md(f["to_text"])}</span></div></div></div>')

    def b(f, cue, s, e):
        return [(".kicker", _c(cue, "kicker", s, 0.05), "in", None), (".key", _c(cue, "keys", s, 0.2), "stagger", None),
                (".plus", _c(cue, "keys", s, 0.2) + 0.1, "in", None), (".led", _c(cue, "led", s, 1.6), "in", None),
                (".ledtxt", _c(cue, "led", s, 1.6) + 0.05, "in", None), ("LED", _c(cue, "led_switch", s, 3.5), "led", f["led_to"])]
    return h, b


# 5 ─ terminal-typing: mini terminal que digita o comando citado + saída
@model("terminal-typing", "Mini terminal: digita o comando citado na fala e mostra a saída. ~220px.",
       "abaixo da tela real (sobre o teclado)", {"window": "user@homelab: ~/sailfish", "command": "fastboot devices",
                                                 "output": "**QV7104MK2Z**   fastboot", "type_duration": 0.9}, draft_y=900)
def _():
    def h(f):
        out = md(f["output"]).replace("<b>", '<span class="c-blue">').replace("</b>", "</span>")
        return (f'<div class="term"><div class="tbar"><i class="r"></i><i class="y"></i><i class="g"></i><span>{md(f["window"])}</span></div>'
                f'<div class="tbody"><div class="ln"><span class="p">$</span> <span class="type"></span><span class="cur"></span></div>'
                f'<div class="ln out c-green">{out}</div></div></div>')

    def b(f, cue, s, e):
        return [("TYPE", _c(cue, "type", s, 0.6), "type", (f["command"], float(f.get("type_duration", 0.9)))),
                (".out", _c(cue, "output", s, 2.0), "in", None)]
    return h, b


# 6 ─ ok-pill: selo de sucesso em uma linha
@model("ok-pill", "Selo de sucesso de 1 linha (✓ DETECTADO, ✓ PRONTO). ~86px.",
       "faixa estreita livre (borda da tela, mesa)", {"text": "XPERIA XZ2 DETECTADO"}, width="max-content", draft_y=1330)
def _():
    def h(f):
        return f'<div class="okbadge"><span class="check">✓</span> {md(f["text"])}</div>'

    def b(f, cue, s, e):
        return [(".okbadge", _c(cue, "pop", s, 0.05), "pop", None)]
    return h, b


# 7 ─ ab-slots: duas (ou três) opções lado a lado, uma é selecionada
@model("ab-slots", "Opções lado a lado (A/B, plano X/Y) e uma é selecionada no momento citado. ~200px.",
       "abaixo da tela real / faixa livre", {"kicker": "2 SLOTS DE SISTEMA", "dot": "amber",
                                             "options": [{"name": "A", "label": "system_a"}, {"name": "B", "label": "system_b"}],
                                             "selected": 0, "selected_label": "ATIVO"},
       scales=(1.0, 0.92, 0.85), draft_y=1240)
def _():
    def h(f):
        opts = ""
        for i, o in enumerate(f["options"]):
            sel = f'<span class="sel">{md(f["selected_label"])}</span>' if i == int(f["selected"]) else ""
            opts += (f'<div class="slot" data-i="{i}"><span class="name">{md(o["name"])}</span>'
                     f'<span class="meta"><span class="lab">{md(o["label"])}</span>{sel}</span></div>')
        return f'<div class="glass slim">{kicker(f["kicker"], f["dot"])}<div class="slots sm">{opts}</div></div>'

    def b(f, cue, s, e):
        return [(".kicker", _c(cue, "kicker", s, 0.05), "in", None), (".slot", _c(cue, "options", s, 0.4), "stagger", None),
                ("SELECT", _c(cue, "select", s, 3.0), "select", int(f["selected"]))]
    return h, b


# 8 ─ progress-pill: barra de progresso em 1 linha com % e estado "concluído"
@model("progress-pill", "Progresso em 1 linha: barra + contagem até 100% + troca para ✓ concluído. ~90px.",
       "topo (sobre conteúdo antigo/sem importância)", {"label": "GRAVANDO SAILFISH OS", "done_label": "FLASH CONCLUÍDO"},
       draft_y=150, y_pref=150)
def _():
    def h(f):
        return (f'<div class="flashpill"><span class="fl-lab"><span class="fl-a">{md(f["label"])}</span>'
                f'<span class="fl-b"><span class="check sm">✓</span> {md(f["done_label"])}</span></span>'
                f'<div class="prog"><i></i></div><span class="pct"><span class="num">0</span><span class="unit">%</span></span></div>')

    def b(f, cue, s, e):
        p0 = _c(cue, "progress_start", s, 0.3)
        p1 = _c(cue, "progress_end", s, max(0.8, (e - s) * 0.5))
        return [("PROG", p0, "progress", p1), ("FLDONE", _c(cue, "done", s, max(1.0, (e - s) * 0.7)), "fldone", None)]
    return h, b


# 9 ─ stamp: kicker + carimbo grande de 1 linha (momento de tensão)
@model("stamp", "Kicker + carimbo grande de 1 linha que 'aterrissa' (tensão, virada). ~180px.",
       "topo/base livre", {"kicker": "CABO USB REMOVIDO · PRIMEIRO BOOT", "dot": "amber", "text": "HORA DA",
                           "accent": "VERDADE", "accent_color": "amber"}, draft_y=150)
def _():
    def h(f):
        return (f'<div class="glass slim center">{kicker(f["kicker"], f["dot"])}'
                f'<div class="stampline">{md(f["text"])} {acc(f["accent"], f["accent_color"])}</div></div>')

    def b(f, cue, s, e):
        return [(".kicker", _c(cue, "kicker", s, 0.1), "in", None), (".stampline", _c(cue, "stamp", s, 1.0), "stamp", None)]
    return h, b


# 10 ─ checklist-row: itens marcados um a um, em linha
@model("checklist-row", "Checklist em linha: cada item ganha ✓ no momento citado (máx. 3 itens curtos). ~160px.",
       "topo/base livre", {"kicker": "PRIMEIRO BOOT", "dot": "cyan", "items": ["Alerta normal", "Logo SONY", "Sem erro"]},
       draft_y=150)
def _():
    def h(f):
        items = "".join(f'<div class="ckc"><span class="box">✓</span>{md(t)}</div>' for t in f["items"])
        return f'<div class="glass slim">{kicker(f["kicker"], f["dot"])}<div class="ckrow">{items}</div></div>'

    def b(f, cue, s, e):
        times = cue.get("items") or [round(s + 0.6 + i * 1.5, 3) for i in range(len(f["items"]))]
        out = [(".kicker", _c(cue, "kicker", s, 0.05), "in", None)]
        out += [(f".ckc:nth-child({i + 1})", float(t), "check", None) for i, t in enumerate(times)]
        return out
    return h, b


# 11 ─ vertical-win: selo vertical estreito (comemoração) para a lateral livre
@model("vertical-win", "Selo vertical estreito (250px) de comemoração — para a lateral livre ao lado do aparelho.",
       "lateral (direita/esquerda)", {"line1": "DEU", "line2": "BOM!", "accent_color": "green", "sub": "SAILFISH OS\nINICIANDO"},
       width=250, xs=("right", "left"), draft_y=500)
def _():
    def h(f):
        sub = "<br/>".join(md(x) for x in str(f["sub"]).split("\n"))
        return f'<div class="vbadge"><div class="vb-t">{md(f["line1"])}<br/>{acc(f["line2"], f["accent_color"])}</div><div class="vb-c">{sub}</div></div>'

    def b(f, cue, s, e):
        return [(".vb-t", _c(cue, "stamp", s, 0.6), "stamp", None), (".vb-c", _c(cue, "sub", s, 1.4), "in", None)]
    return h, b


# 12 ─ side-status: painel lateral (kicker + título + chip)
@model("side-status", "Painel lateral 440px: kicker + título + chip (status, recurso citado).",
       "lateral livre", {"kicker": "SAILFISH OS · ONLINE", "dot": "green", "title": "Terminal", "accent": "nativo",
                         "accent_color": "cyan", "chip": "Shell root + **SSH**"},
       width=440, xs=("right", "left"), draft_y=500)
def _():
    def h(f):
        chip = f'<div class="chips"><span>{md(f["chip"])}</span></div>' if f.get("chip") else ""
        return f'<div class="glass slim">{kicker(f["kicker"], f["dot"])}<div class="t3">{md(f["title"])} {acc(f["accent"], f["accent_color"])}</div>{chip}</div>'

    def b(f, cue, s, e):
        out = [(".kicker", _c(cue, "kicker", s, 0.05), "in", None), (".t3", _c(cue, "title", s, 0.15), "in", None)]
        if f.get("chip"):
            out.append((".chips span", _c(cue, "chip", s, 0.35), "pop", None))
        return out
    return h, b


# 13 ─ final-cta: status + título + próximo passo + CTA
@model("final-cta", "Encerramento: status + título + próximo passo + botão de CTA ('Comenta X'). ~280px.",
       "base livre acima da legenda", {"kicker": "STATUS: PRONTO", "dot": "green", "title": "MINI SERVIDOR", "accent": "ONLINE",
                                       "accent_color": "green", "next_label": "próximo →",
                                       "next": "descobrir o IP e conectar via **SSH**",
                                       "cta": "Comenta **LINUX** que eu te mando o tutorial"}, draft_y=1150)
def _():
    def h(f):
        nxt = f'<div class="next"><span class="p">{md(f["next_label"])}</span> {md(f["next"])}</div>' if f.get("next") else ""
        cta = f'<div class="cta">{md(f["cta"])}</div>' if f.get("cta") else ""
        return (f'<div class="glass slim">{kicker(f["kicker"], f["dot"], " live")}'
                f'<div class="t2">{md(f["title"])} {acc(f["accent"], f["accent_color"])}</div>{nxt}{cta}</div>')

    def b(f, cue, s, e):
        out = [(".kicker", _c(cue, "kicker", s, 0.05), "in", None), (".t2", _c(cue, "title", s, 0.4), "in", None)]
        if f.get("next"):
            out.append((".next", _c(cue, "next", s, 2.0), "in", None))
        if f.get("cta"):
            out.append((".cta", _c(cue, "cta", s, 3.0), "pop", None))
        return out
    return h, b
