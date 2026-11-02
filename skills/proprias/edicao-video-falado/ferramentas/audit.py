"""Auditoria da fala montada NA FONTE, em janelas curtas: acha repetição escondida, gaguejo e filler que o `wh edit` e janelas
longas do whisper engolem (giro de 26/10: "a Reuters acabou de… a Reuters acabou de divulgar" virou um "de" de 1,4 s).
Roda na pasta .work do projeto, depois do build.py:

  python3 -I audit.py chave=FONTE.MOV [chave=FONTE2.MOV ...] [> audit.txt]

chave = a mesma do SRC do build.py. Cada trecho de segs.json é retranscrito (`wh snip`) em janelas de 2,4 s com passo de 1,8 s.
Marca no fim:
  REPETE   palavra ou sequência de palavras dita duas vezes seguidas dentro da janela ("de de", "a reuters acabou a reuters acabou")
  ESTICADA palavra com `!` (duração longa: vogal esticada, hesitação ou repetição colada)
  FILLER   "é", "eh", "hã", "hum", "tipo" soltos com 0,15 s ou mais (fora da 1ª palavra da janela)
Toda marca se confere com `vad.py`/`wh try` na fonte antes de mexer na EDL; janela que começa ou termina no meio de palavra
gera lixo nas pontas ("Tchau, tchau" = pedaço de "site"), então olhe o texto do meio.
"""
import json, os, re, subprocess, sys, unicodedata

WH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wh")
SRC = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
FILL = {"é", "éé", "ééé", "éééé", "eh", "hã", "ãã", "hum", "hm", "tipo"}   # "e"/"a" sem acento são conjunção/artigo, não filler


def norm(w):
    w = unicodedata.normalize("NFKD", w.lower())
    return re.sub(r"[^a-z0-9]", "", "".join(c for c in w if not unicodedata.combining(c)))


def flags(line):
    ws = re.findall(r"(\S+?)@([\d.]+)-([\d.]+)(\S*)", line)
    dur = [float(b) - float(a) for _, a, b, _ in ws]
    ws = [(w, m) for w, _, _, m in ws]
    toks = [norm(w) for w, _ in ws]
    out = []
    for n in range(4, 0, -1):                      # sequência repetida (n palavras), da maior para a menor
        for i in range(len(toks) - 2 * n + 1):
            a, b = toks[i:i + n], toks[i + n:i + 2 * n]
            if a == b and all(a) and (n > 1 or len(a[0]) > 1):
                out.append("REPETE '" + " ".join(a) + "'")
                break
        if out:
            break
    for i, ((w, m), t) in enumerate(zip(ws, toks)):
        if "!" in m and 0 < i < len(ws) - 1:          # as pontas da janela costumam vir cortadas: só o miolo conta
            out.append(f"ESTICADA '{w}'")
        if re.sub(r"[^\wãé]", "", w.lower()) in FILL and dur[i] >= 0.15 and i > 0:
            out.append(f"FILLER '{w}'")
    return out


segs = json.load(open("segs.json"))["segments"]
win = {}
for s in segs:
    if s["src"] not in SRC:
        sys.exit(f"falta a fonte '{s['src']}=ARQUIVO' (chaves usadas: {sorted({x['src'] for x in segs})})")
    t = s["a"]
    while True:
        e = min(s["b"], t + 2.4)
        win.setdefault(s["src"], []).append((round(t, 2), round(e, 2), s["out"], s["label"]))
        if e >= s["b"]:
            break
        t += 1.8
total = 0
for k, ws in win.items():
    res = subprocess.run([WH, "snip", SRC[k], *[f"{a}-{b}" for a, b, *_ in ws]], capture_output=True, text=True).stdout
    lines = [l for l in res.splitlines() if l[:1].isdigit()]
    lab = None
    for (a, b, o, label), l in zip(ws, lines):
        if label != lab:
            print(f"\n## {k} saída {o:.2f} s | {label}")
            lab = label
        f = flags(l)
        total += len(f)
        print("  ", l, ("   <<< " + "; ".join(f)) if f else "")
print(f"\n{total} marca(s) para conferir na fonte")
