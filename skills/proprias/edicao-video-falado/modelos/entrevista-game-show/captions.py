"""Legenda revisada (pt-BR) alinhada às palavras do whisper na fala editada -> data.json

Entrada: transcript_edit.json (_pipeline/wh edit sobre segs/cat.wav). O texto abaixo é a fonte da verdade; os tempos vêm
do whisper por alinhamento de sequência (difflib).
Marcas: '|' fecha o bloco, '/' quebra a linha dentro do bloco (máx. 2 linhas, 3-5 palavras), '*palavra' = destaque
(menta na fala de quem pergunta, champanhe na de quem responde), '@j (quem pergunta) / @m (quem responde) no começo do bloco = quem fala a partir dali.
Uso: python3 -I captions.py
"""
import difflib, json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
TEXT = """
@m Frase da *convidada / que abre o vídeo... |
@j Oi, / *Convidada! |
Primeira *pergunta / do quadro? |
@m Resposta / com *destaque. |
"""


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


blocks, spk = [], "j"                           # [{"spk": "j"|"m", "lines": [[token, ...], ...]}]
for raw in TEXT.split("|"):
    raw = raw.strip()
    if not raw:
        continue
    m = re.match(r"@([jm])\s+", raw)
    if m:
        spk, raw = m.group(1), raw[m.end():]
    blocks.append({"spk": spk, "lines": [ln.split() for ln in raw.split("/")]})
toks = [t for b in blocks for ln in b["lines"] for t in ln]

TR = json.load(open(os.path.join(W, "transcript_edit.json")))   # wh edit: lista de palavras {w, s, e, p, src}
wl = [w for seg in TR for w in seg["words"]] if TR and "words" in TR[0] else TR
A = [norm(t) for t in toks]
B = [norm(w["w"]) for w in wl]
times = [None] * len(toks)
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
        for k in range(i2 - i1):
            times[i1 + k] = (wl[j1 + k]["s"], wl[j1 + k]["e"])
        if tag == "replace":
            print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "replace":  # n palavras do texto <-> m do whisper: reparte o intervalo
        s0, e0 = wl[j1]["s"], wl[j2 - 1]["e"]
        for k in range(i2 - i1):
            times[i1 + k] = (s0 + (e0 - s0) * k / (i2 - i1), s0 + (e0 - s0) * (k + 1) / (i2 - i1))
        print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "delete":
        print("  sem tempo:", " ".join(toks[i1:i2]))
    elif tag == "insert":
        print("  só no whisper:", " ".join(w["w"] for w in wl[j1:j2]))
for i, t in enumerate(times):                   # faltas: interpolação
    if t is None:
        p = next(times[k] for k in range(i - 1, -1, -1) if times[k])
        n = next((times[k] for k in range(i + 1, len(times)) if times[k]), (p[1] + 0.3, p[1] + 0.6))
        times[i] = (p[1], max(p[1] + 0.05, n[0]))
for i in range(1, len(times)):                  # palavras coladas pelo whisper: no mínimo 0,1 s cada
    if times[i][0] < times[i - 1][0] + 0.1:
        s0 = times[i - 1][0] + 0.1
        times[i] = (s0, max(times[i][1], s0 + 0.1))

segs = json.load(open(os.path.join(W, "segs.json")))
SPEECH = segs["duration"]
# Falas curtas que o whisper engole ou junta com a vizinha ("Pix.", a troca "Eu vou pular essa. / Vai pular? / Vou pular!"):
# o tempo vem do próprio segmento da EDL (o mais próximo do bloco com o mesmo texto), palavras repartidas por igual.
ANCHOR = ["Eu vou pular essa.", "Vai pular?", "Vou pular!", "Pix."]
ti, bounds = 0, []
for b in blocks:
    n = sum(len(ln) for ln in b["lines"])
    bounds.append((ti, ti + n))
    ti += n
for lab in ANCHOR:
    cand = [x for x in segs["segments"] if norm(x["label"]) == norm(lab)]
    for bi, (i0, i1) in enumerate(bounds):
        if norm("".join(toks[i0:i1])) != norm(lab):
            continue
        sg = min(cand, key=lambda x: abs(x["out"] - times[i0][0]))
        a0, a1 = sg["out"] + 0.08, sg["out"] + sg["dur"] - 0.08
        for k2 in range(i0, i1):
            f = (k2 - i0) / (i1 - i0)
            times[k2] = (round(a0 + (a1 - a0) * f, 3), round(a0 + (a1 - a0) * (f + 1 / (i1 - i0)), 3))
words, CAPS, k = [], [], 0
for b in blocks:
    lines = []
    for ln in b["lines"]:
        out = []
        for tok in ln:
            s, e = times[k]
            words.append({"w": tok, "t": round(s, 3), "e": round(e, 3)})
            x = tok.lstrip("*").rstrip(".,:")                   # sem ponto/vírgula na tela (fica ? ! … e aspas)
            out.append({"x": x, "k": tok.startswith("*") or tok.startswith('"*'), "t": round(s, 3)})
            k += 1
        lines.append(out)
    CAPS.append({"spk": b["spk"], "lines": lines, "t0": round(max(0.0, lines[0][0]["t"] - 0.04), 3), "e": round(times[k - 1][1], 3)})
for i, c in enumerate(CAPS):
    nxt = CAPS[i + 1]["t0"] if i + 1 < len(CAPS) else SPEECH
    c["t1"] = round(min(nxt, c.pop("e") + 0.5), 3)
json.dump({"caps": CAPS, "words": words, "speech": SPEECH}, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} {c['spk']} " +
          " / ".join(" ".join(("*" if w["k"] else "") + w["x"] for w in ln) for ln in c["lines"]))
print("fala", SPEECH, "blocos", len(CAPS))
