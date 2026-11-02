"""Montagem da fala editada — modelo do kit. Copie para <episódio>/<projeto>/.work/build.py e preencha o CONFIG.

  uv run --with numpy python -I build.py          (rodar de novo depois de mexer na EDL é rápido: usa o cache)

O que ele faz:
- áudio de cada fonte extraído uma vez (mono 48 kHz, aresample async p/ áudio do iPhone com furos);
  fontes com clean=True: highpass 70 Hz + adeclick (estalos de boca) + debreath (respiração −14 dB), feito uma vez;
- fala das fontes em REFINE: refina início/fim pela energia, apara ar morto, ripple em pausas > MAX_GAP (fica ~0,16 s);
- vídeo lido direto do original; HDR do iPhone (HLG/PQ) vira SDR bt709 (tonemap hable) só nos quadros usados;
- x264 veryfast nos intermediários (o render do HyperFrames recodifica tudo depois) e cache por segmento:
  só os trechos que mudaram são recodificados;
- micro-fades seno de 20–25 ms nas emendas, compressor + limiter no fim;
- gravação de tela (TELA) cortada no mesmo ritmo, com troca/aceleração opcional por item da EDL.
Saída: ../assets/footage/fala.mp4 (+ tela.mp4) e segs.json (segmentos e mapa fonte -> saída).
"""
import hashlib, json, os, subprocess, time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

W = os.path.dirname(os.path.abspath(__file__))


def P(*p):
    return os.path.normpath(os.path.join(W, *p))


# ============================== CONFIG DO EPISÓDIO ==============================
FPS = 30
OFF = 0.0              # tela − celular (palma: $PIPE/sync.py); 0 se não houver gravação de tela
# v/a: vídeo e áudio da fonte; voff: t_vídeo = t + voff; clean: limpeza de voz; gain: dB;
# toff: t_tela = t + toff para o painel do app (None = painel preto nesse trecho)
SRC = {
    "a": {"v": P("../../brutos/IMG_0001.MOV"), "a": P("../../brutos/IMG_0001.MOV"), "voff": 0.0, "clean": True,
          "gain": 0.0, "toff": None},
    # "b": {...}  uma chave curta por arquivo bruto (a mesma chave vai no audit.py: b=../../brutos/IMG_0002.MOV)
}
MAIN = "a"             # fonte principal da fala
REFINE = tuple(SRC)    # fontes com fala: refino de início/fim, aparo de ar morto e ripple em cada uma
TELA = None            # gravação de tela sincronizada, ex.: P("../../tela.mp4")
MAX_GAP = 0.25         # pausa interna maior que isso vira corte (ripple)
KEEP_PRE = 0.09        # respiro que fica depois da última palavra
KEEP_POST = 0.07       # respiro que fica antes da próxima palavra
THR = -37.0            # dB: abaixo disso é pausa (respiração e ruído de sala incluídos). Sala ruidosa: −31 a −30,5
BREATH_DB = -14        # atenuação das respirações

# (fonte, a, b, rótulo, opções[, tela_a, tela_b]) — tempos no relógio da fonte (segundos), rótulo = a fala do trecho.
# opções: ea/eb = borda exata (sem refino); nosplit = mantém pausas internas; fadeout = cauda de 0,9 s (último trecho);
#         xN = timelapse (vídeo N× mais rápido, áudio em silêncio), ex.: "x5".
# tela_a/tela_b: mostra esse trecho da gravação de tela (acelerado para caber) em vez do instante natural.
EDL = [
    # gancho
    ("a", 0.00, 1.00, "frase do gancho", ""),
    # notícia/bloco 1
    ("a", 2.00, 5.00, "frase seguinte", ""),
    # fim olhando pra câmera
    ("a", 6.00, 8.00, "frase final (CTA)", "fadeout"),
]
# ================================================================================

CACHE = os.path.join(W, "segs", "cache")
JOBS = int(os.environ.get("BUILD_JOBS", max(2, (os.cpu_count() or 4) - 2)))
TONEMAP = ("zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
           "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")
X264 = ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(FPS), "-g", str(FPS),
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]


def run(args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def load_mono(path, sr):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def fresh(out, *deps):
    return os.path.exists(out) and all(os.path.getmtime(out) >= os.path.getmtime(d) for d in deps)


def vfilter(path):
    """SDR bt709 a 30 fps; HDR (HLG/PQ) passa pelo tonemap só nos quadros que forem usados"""
    trc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True).stdout.strip()
    if trc in ("arib-std-b67", "smpte2084"):
        return TONEMAP.format(tin=trc) + f",fps={FPS}"
    return f"format=yuv420p,fps={FPS}"


def debreath(y):
    """Atenua respirações: trechos sem voz, de energia média e espectro grave (s/ch/x são agudos e ficam), longe das
    vogais. Vetorizado (quadros de 20 ms a cada 10 ms, em blocos para não estourar a RAM)."""
    H, N = 480, 960
    nfr = (len(y) - N) // H
    e, v, cen = np.zeros(nfr), np.zeros(nfr), np.zeros(nfr)
    win = np.hanning(N).astype(np.float32)
    freqs = np.fft.rfftfreq(N, 1 / 48000)
    for c0 in range(0, nfr, 8000):
        c1 = min(nfr, c0 + 8000)
        F = y[np.arange(N)[None, :] + H * np.arange(c0, c1)[:, None]]
        F = F - F.mean(axis=1, keepdims=True)
        e[c0:c1] = 20 * np.log10(np.sqrt(np.mean(F ** 2, axis=1)) + 1e-9)
        ac = np.fft.irfft(np.abs(np.fft.rfft(F[:, ::3], n=640, axis=1)) ** 2, n=640, axis=1)[:, :320]
        v[c0:c1] = ac[:, 40:230].max(axis=1) / (ac[:, 0] + 1e-9)       # pico de autocorrelação entre 70 e 400 Hz
        sp = np.abs(np.fft.rfft(F * win, axis=1))
        cen[c0:c1] = (sp * freqs).sum(axis=1) / (sp.sum(axis=1) + 1e-9)
    voiced = (v > 0.45) & (e > -40)
    prot = voiced.copy()
    for k in range(1, 6):                       # 50 ms de proteção em volta das vogais
        prot[k:] |= voiced[:-k]
        prot[:-k] |= voiced[k:]
    cand = (~prot) & (e < -27) & (e > -56) & (cen < 3500)
    breath = np.zeros(nfr, bool)
    i = 0
    while i < nfr:
        if cand[i]:
            j = i
            while j < nfr and cand[j]:
                j += 1
            if j - i >= 12:                     # só trechos de 120 ms ou mais
                breath[i:j] = True
            i = j
        else:
            i += 1
    g = np.where(breath, 10 ** (BREATH_DB / 20), 1.0)
    g = np.convolve(g, np.ones(3) / 3, "same")  # rampa de 30 ms
    print(f"debreath: {breath.sum() / 100:.2f} s atenuados")
    return (y * np.interp(np.arange(len(y)), np.arange(nfr) * H + N // 2, g)).astype(np.float32)


def prep_audio(name, S):
    """audio/<fonte>48.wav (bruto) e audio/<fonte>_voz.wav (limpo), feitos uma vez e refeitos se a fonte mudar"""
    os.makedirs(P("audio"), exist_ok=True)
    raw = P("audio", f"{name}48.wav")
    if not fresh(raw, S["a"]):
        run(["-i", S["a"], "-map", "0:a:0", "-af", "aresample=async=1:first_pts=0", "-ac", "1", "-ar", "48000",
             "-c:a", "pcm_f32le", raw])
    if not S.get("clean"):
        return raw
    voz = P("audio", f"{name}_voz.wav")
    if not fresh(voz, raw):
        tmp = P("audio", f"{name}_dc.wav")
        run(["-i", raw, "-af", "highpass=f=70,adeclick=w=55:o=75:t=2.5", "-c:a", "pcm_f32le", tmp])
        y = debreath(load_mono(tmp, 48000).copy())
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ac", "1", "-ar", "48000", "-i", "-", "-c:a", "pcm_f32le", voz],
                       input=y.tobytes(), check=True)
        os.remove(tmp)
    return voz


def cached(args, inputs, ext):
    """roda o ffmpeg só se esse mesmo comando (com as mesmas entradas) ainda não estiver no cache"""
    key = json.dumps(args) + "".join(f"{p}:{os.path.getsize(p)}:{os.path.getmtime(p)}" for p in inputs)
    out = os.path.join(CACHE, hashlib.sha1(key.encode()).hexdigest()[:16] + ext)
    return out, (None if os.path.exists(out) else [*args, out + ".tmp" + ext])


# ---------- refino da fala pela energia (10 ms) da fonte MAIN ----------
x = None
DB = None


def fr(t):
    return int(round(t * 100))


def refine_start(t):
    lo, hi = max(0, fr(t - 0.25)), min(len(DB), fr(t + 0.05))
    quiet = [f for f in range(lo, hi) if DB[f] < THR - 3]   # começa logo depois da respiração
    if quiet:
        return (quiet[-1] + 1) / 100 - 0.05
    lo, hi = fr(t - 0.08), fr(t + 0.08)
    return (lo + int(np.argmin(DB[lo:hi]))) / 100


def refine_end(t):
    lo, hi = max(0, fr(t - 0.05)), min(len(DB), fr(t + 0.45))
    for k in (5, 2):
        quiet = [f for f in range(lo, hi) if DB[f] < THR - k]
        if quiet:
            return quiet[0] / 100 + 0.07
    lo, hi = fr(t - 0.08), fr(t + 0.08)
    return (lo + int(np.argmin(DB[lo:hi]))) / 100


def trim(a, b):
    """tira o ar morto (silêncio/respiração abaixo de THR) do começo e do fim do trecho"""
    f = fr(a)
    while f < fr(b) and DB[f] < THR:
        f += 1
    g = fr(b) - 1
    while g > f and DB[g] < THR:
        g -= 1
    return max(a, f / 100 - KEEP_POST), min(b, (g + 1) / 100 + KEEP_PRE)


def split_gaps(a, b):
    out, cur = [], a
    f, end = fr(a + 0.1), fr(b - 0.1)
    while f < end:
        if DB[f] < THR:
            g = f
            while g < end and DB[g] < THR:
                g += 1
            if (g - f) / 100 > MAX_GAP:
                out.append([cur, f / 100 + KEEP_PRE])
                cur = g / 100 - KEEP_POST
            f = g
        else:
            f += 1
    out.append([cur, b])
    return out


def main():
    global DB
    os.makedirs(CACHE, exist_ok=True)
    with ThreadPoolExecutor(len(SRC)) as ex:
        apath = dict(zip(SRC, ex.map(lambda kv: prep_audio(*kv), SRC.items())))
    DBS = {}
    for k in REFINE:
        y = load_mono(P("audio", f"{k}48.wav"), 16000)
        n = len(y) // 160
        DBS[k] = 20 * np.log10(np.sqrt(np.mean(y[:n * 160].reshape(n, 160) ** 2, axis=1) + 1e-12))
    vf = {k: vfilter(S["v"]) for k, S in SRC.items()}

    segs = []
    for k, e in enumerate(EDL):
        src, a, b, label, opt = e[:5]
        o = opt.split()
        speed = next((float(w[1:]) for w in o if w[0] == "x" and w[1:].replace(".", "").isdigit()), 1.0)
        if src in DBS and speed == 1.0:
            DB = DBS[src]
            ra = a if "ea" in o else refine_start(a)
            rb = b if "eb" in o else refine_end(b)
            if "nosplit" not in o:
                ra, rb2 = trim(ra, rb)
                rb, tail = (rb2, rb) if "fadeout" in o else (rb2, None)
            else:
                tail = None
            parts = [[ra, rb]] if "nosplit" in o else split_gaps(ra, rb)
            if tail:                                # cauda olhando para a câmera fica inteira no último trecho
                parts[-1][1] = tail
        else:
            parts = [[a, b]]
        for p, q in parts:
            segs.append({"edl": k, "src": src, "label": label, "a": p, "b": q, "fadeout": "fadeout" in o and [p, q] == parts[-1],
                         "speed": speed, "scr": list(e[5:7]) if len(e) > 5 else None})
    for p, q in zip(segs, segs[1:]):            # vizinhos da mesma fonte nunca se sobrepõem (evita repetir som)
        if p["src"] == q["src"] and p["a"] < q["a"] < p["b"]:
            p["b"] = q["a"]

    t, edl_dur = 0.0, {}
    for s in segs:
        S = SRC[s["src"]]
        s["va"] = round((s["a"] + S["voff"]) * FPS)         # quadro exato no vídeo
        nf = round((s["b"] - s["a"]) * FPS / s["speed"])
        s["a"] = round(s["va"] / FPS - S["voff"], 4)        # áudio alinhado ao quadro
        s["b"] = round(s["a"] + nf * s["speed"] / FPS, 4)
        s["out"], s["dur"], s["nf"] = round(t, 4), round(nf / FPS, 4), nf
        t += s["dur"]
        edl_dur[s["edl"]] = edl_dur.get(s["edl"], 0) + s["dur"]

    jobs, files, tfiles, used = [], [], [], {}
    for s in segs:
        S, va, nf, d = SRC[s["src"]], s["va"], s["nf"], s["dur"]
        fade = (f"afade=t=out:st={max(0, d - 0.9):.4f}:d={min(0.9, d):.4f}" if s["fadeout"] else f"afade=t=out:st={d - 0.025:.4f}:d=0.025:curve=qsin")
        args = ["-ss", f"{va / FPS:.6f}", "-i", S["v"], "-ss", f"{s['a']:.6f}", "-i", apath[s["src"]],
                "-map", "0:v:0", "-map", "1:a:0", "-vf", vf[s["src"]], "-frames:v", str(nf),
                "-af", f"aresample=48000,atrim=end_sample={nf * 1600},asetpts=PTS-STARTPTS,volume={S['gain']}dB,"
                       f"afade=t=in:d=0.02:curve=qsin,{fade}",
                *X264, "-crf", "16", "-c:a", "pcm_f32le", "-ar", "48000"]
        if s["speed"] != 1.0:                             # timelapse: vídeo acelerado, áudio em silêncio
            args = ["-ss", f"{va / FPS:.6f}", "-i", S["v"], "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
                    "-map", "0:v:0", "-map", "1:a:0", "-vf", f"{vf[s['src']]},setpts=(PTS-STARTPTS)/{s['speed']},fps={FPS}",
                    "-frames:v", str(nf), "-af", f"atrim=end_sample={nf * 1600}",
                    *X264, "-crf", "16", "-c:a", "pcm_f32le", "-ar", "48000"]
        out, job = cached(args, [S["v"], apath[s["src"]]], ".mov")
        files.append(out)
        if job:
            jobs.append((job, out))
        if TELA:                                          # painel do app no mesmo ritmo
            if S.get("toff") is None:
                targs = ["-f", "lavfi", "-i", f"color=c=0x0b0d10:s=1920x1080:r={FPS}", "-frames:v", str(nf)]
            elif s["scr"]:
                ta, tb = s["scr"]
                k0 = used.get(s["edl"], 0.0)
                span = (tb - ta) * d / edl_dur[s["edl"]]
                used[s["edl"]] = k0 + span
                s["tela"] = [round(ta + k0, 3), round(ta + k0 + span, 3)]
                targs = ["-ss", f"{ta + k0:.4f}", "-i", TELA, "-vf", f"setpts=(PTS-STARTPTS)/{span / d:.5f},fps={FPS}",
                         "-frames:v", str(nf)]
            else:
                ta = s["a"] + S["toff"]
                s["tela"] = [round(ta, 3), round(ta + d, 3)]
                targs = ["-ss", f"{ta:.4f}", "-i", TELA, "-vf", f"fps={FPS}", "-frames:v", str(nf)]
            tout, tjob = cached([*targs, "-an", *X264, "-crf", "18"], [TELA], ".mp4")
            tfiles.append(tout)
            if tjob:
                jobs.append((tjob, tout))

    def go(job):
        args, out = job
        run(args)
        os.replace(args[-1], out)
    print(f"{len(segs)} segmentos: {len(jobs)} para codificar, {len(files) + len(tfiles) - len(jobs)} do cache")
    with ThreadPoolExecutor(JOBS) as ex:               # o tonemap do zscale usa ~1 núcleo por processo
        list(ex.map(go, jobs))

    foot = P("..", "assets", "footage")
    os.makedirs(foot, exist_ok=True)
    lst = P("segs", "list.txt")
    open(lst, "w").write("".join(f"file '{f}'\n" for f in files))
    cat = P("segs", "cat.wav")
    run(["-f", "concat", "-safe", "0", "-i", lst, "-map", "0:a:0", "-c:a", "pcm_f32le", cat])
    run(["-f", "concat", "-safe", "0", "-i", lst, "-i", cat, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
         "-af", "acompressor=threshold=-26dB:ratio=3:attack=5:release=90:makeup=4,alimiter=limit=0.89",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", os.path.join(foot, "fala.mp4")])
    if TELA:
        tl = P("segs", "tlist.txt")
        open(tl, "w").write("".join(f"file '{f}'\n" for f in tfiles))
        run(["-f", "concat", "-safe", "0", "-i", tl, "-c:v", "copy", "-movflags", "+faststart", os.path.join(foot, "tela.mp4")])
    keep = set(files) | set(tfiles)                       # cache: o que a EDL atual usa + versões de até 1 dia
    for f in keep:
        os.utime(f)
    for f in os.listdir(CACHE):
        f = os.path.join(CACHE, f)
        if f not in keep and time.time() - os.path.getmtime(f) > 86400:
            os.remove(f)
    json.dump({"duration": round(t, 3), "segments": segs}, open(P("segs.json"), "w"), ensure_ascii=False, indent=1)
    for s in segs:
        print(f"{s['out']:6.2f} +{s['dur']:.2f}  {s['src']:6s} [{s['a']:.2f}-{s['b']:.2f}] {s['label'][:70]}")
    print("total", round(t, 3))


if __name__ == "__main__":
    main()
