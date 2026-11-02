"""Varre todas as emendas da fala montada atrás de pedaço de palavra vizinha (começo da próxima no fim do trecho,
rabo da anterior no começo). Roda na pasta .work do projeto, depois do build.py:

  uv run --with numpy python -I edgecheck.py [fonte=transcricao.json ...] [-v]

Lê segs.json e audio/<fonte>48.wav. Com fonte=transcricao.json (saída do `wh file`) mostra as palavras perto de cada borda.
-v imprime o perfil de 20 ms de todas as bordas (V=vozeado ·=sem voz, número = −dB); sem -v, só as suspeitas.
Suspeita de FIM: energia sobe nos últimos 60 ms do trecho. Suspeita de INÍCIO: energia cai nos primeiros 60 ms.
Fala contínua (sem pausa entre palavras) também aparece: confira com `wh try` e com o perfil antes de mexer.
Lição do giro de 24/10: o `wh edit` da fala montada esconde esses pedaços (o contexto "completa" a palavra); a borda tem
que ser olhada no áudio da fonte. Ligação "carros e" vira "carroz‿e": cortar no fim do "o".
"""
import json, os, subprocess, sys
import numpy as np

SR = 16000
args = [a for a in sys.argv[1:] if a != "-v"]
VERB = "-v" in sys.argv
TRS = dict(a.split("=", 1) for a in args if "=" in a)
segs = json.load(open("segs.json"))["segments"]
X = {}
for src in {s["src"] for s in segs}:
    X[src] = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join("audio", f"{src}48.wav"), "-f", "f32le",
                                           "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout, np.float32)
WORDS = {k: [w for s in json.load(open(v)) for w in s["words"]] for k, v in TRS.items()}


def frame(x, t):
    i = int(t * SR)
    f = x[i:i + 320] - np.mean(x[i:i + 320])
    e = 20 * np.log10(np.sqrt(np.mean(f ** 2)) + 1e-9)
    ac = np.correlate(f, f, "full")[len(f) - 1:]
    return e, float(np.max(ac[40:230]) / (ac[0] + 1e-9))


def prof(x, a, b):
    out = []
    for t in np.arange(a, b, 0.02):
        e, v = frame(x, t)
        out.append(("V" if v > 0.45 and e > -40 else "·") + f"{-e:02.0f}")
    return " ".join(out)


def near(src, t):
    return " ".join(f"{w['w']}@{w['s']:.2f}-{w['e']:.2f}" for w in WORDS.get(src, []) if t - 0.45 < w["e"] and w["s"] < t + 0.45)


flags = []
for s in segs:
    x, a, b = X[s["src"]], s["a"], s["b"]
    tag = f"{s['out']:6.2f} {s['src']} [{a:.2f}-{b:.2f}] {s['label'][:55]}"
    if VERB:
        print(f"\n{tag}\n   início {a - 0.10:.2f}| {prof(x, a - 0.10, a)} || {prof(x, a, a + 0.16)}   {near(s['src'], a)}"
              f"\n   fim    {b - 0.24:.2f}| {prof(x, b - 0.24, b)} || {prof(x, b, b + 0.12)}   {near(s['src'], b)}")
    e_end = [frame(x, t)[0] for t in np.arange(b - 0.12, b - 0.019, 0.02)]
    if max(e_end[-3:]) > -35 and max(e_end[-3:]) > min(e_end[:-3]) + 8:
        flags.append(f"FIM    {tag}  {[round(v) for v in e_end]}  {near(s['src'], b)}")
    e_beg = [frame(x, t)[0] for t in np.arange(a, a + 0.121, 0.02)]
    if max(e_beg[:3]) > -35 and min(e_beg[2:]) < max(e_beg[:3]) - 8:
        flags.append(f"INÍCIO {tag}  {[round(v) for v in e_beg]}  {near(s['src'], a)}")
print("\n== bordas suspeitas ==")
print("\n".join(flags) or "nenhuma")
