"""Reenquadramento de telejornal sobre a fala do estúdio: plano médio fechado (rosto e tronco) na maior parte do vídeo e corpo inteiro
só nas cenas-chave. Serve para quem grava de corpo inteiro, longe da câmera: em plano aberto, a ida e volta até o celular e a mudança de
distância entre as tomadas ficam evidentes.

- Plano médio (rosto e tronco) em quase tudo, alternando a cada corte entre A (mais aberto) e B (mais fechado), como duas câmeras:
  esconde o jump cut. Trecho com menos de 0,6 s herda o plano do anterior (não pisca). O gancho (1º trecho) já começa no B.
- Corpo inteiro, como foi gravado, nas cenas-chave (no giro: abertura das notícias 2 em diante e o "segue o canal" do fim).
- O quadro acompanha o rosto (chin_raw.json, 5 q/s) com suavização dentro de cada trecho e compensa 60% da ida e volta dele até a câmera.
- Interpolação Lanczos + realce leve proporcional ao zoom. Saída: ../assets/footage/fala_estudio_zoom.mp4 (áudio copiado) e chin.json
  já nas coordenadas do quadro novo (o make.py põe os prints entre o queixo e a legenda a partir dele). No make.py: ZALT = 1.0 e DMAX = 0.
Roda na pasta .work depois do composite. Configuração em "planos" no estudio.json (tudo opcional; os padrões vêm de um vídeo 1080x1920
de corpo inteiro com o rosto em ~280 px de altura na caixa do chin.py, o que dá zoom de ~1,6× a 1,9×):
  "aberto": [24.93, 69.3, ...]        início na fonte (campo "a" do segs.json) de cada trecho em corpo inteiro; sem isso, tudo fechado
  "A": [450, 350], "B": [520, 320]    altura da caixa do rosto e topo do rosto no quadro novo (px), por plano
  "zmax": 2.0                         zoom máximo
  "segue": 0.6                        quanto da ida e volta do rosto o zoom compensa (0 = zoom fixo no trecho, 1 = rosto sempre do mesmo tamanho)
O chin_raw.json é o chin.json do chin.py na fala.mp4, no quadro original. Se faltar ou estiver velho, o chin.py roda sozinho (~1 min).
Uso: uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/reframe.py [t1,t2,...]
  com tempos: só quadros de teste em qc/rf_<t>.jpg. SRC=... troca a entrada (padrão ../assets/footage/fala_estudio.mp4).
  ~5,5 min para 67 s num notebook de 4 núcleos (CPU); teste ~1 s por quadro.
"""
import json, os, subprocess, sys
import cv2
import numpy as np

VW, VH, FPS = 1080, 1920, 30
SRC = os.environ.get("SRC", "../assets/footage/fala_estudio.mp4")
OUT = "../assets/footage/fala_estudio_zoom.mp4"
FALA = "../assets/footage/fala.mp4"                       # onde o chin.py mede o rosto (mesmo quadro do fala_estudio.mp4)
CFG = (json.load(open("estudio.json")) if os.path.exists("estudio.json") else {}).get("planos", {})
WIDE_SRC = [float(a) for a in CFG.get("aberto", [])]       # início na fonte dos trechos em corpo inteiro
SHOT = {k: tuple(CFG.get(k, d)) for k, d in (("A", (450, 350)), ("B", (520, 320)))}   # altura do rosto e topo do rosto no quadro novo
ZMIN, ZMAX, K = 1.0, float(CFG.get("zmax", 2.0)), float(CFG.get("segue", 0.6))

if not os.path.exists(SRC):
    sys.exit(f"falta {SRC}: rode o composite antes (ou passe SRC=...)")
S = json.load(open("segs.json"))
segs = S["segments"]


def chin_velho():
    if not os.path.exists("chin_raw.json"):
        return "falta o chin_raw.json"
    if os.path.exists(FALA) and os.path.getmtime("chin_raw.json") < os.path.getmtime(FALA):
        return "o chin_raw.json é mais velho que a fala.mp4"
    c = json.load(open("chin_raw.json"))
    if abs(len(c["box"]) / c["fps"] - S["duration"]) > 1:
        return f"o chin_raw.json cobre {len(c['box']) / c['fps']:.1f} s e a fala tem {S['duration']:.1f} s"


why = chin_velho()
if why:
    if not os.path.exists(FALA):
        sys.exit(f"{why} e não há {FALA} para medir o rosto: rode o build.py e depois o chin.py (saída chin_raw.json)")
    print(f"{why}: rodando o chin.py (~1 min)")
    subprocess.run([sys.executable, "-X", "utf8", "-I", os.path.join(os.path.dirname(os.path.abspath(__file__)), "chin.py"), "chin_raw.json"],
                   check=True)
C = json.load(open("chin_raw.json"))
CF, BOX = C["fps"], C["box"]
if all(b is None for b in BOX):
    sys.exit("o chin.py não achou rosto em nenhum quadro da fala.mp4")
BOX = [b if b is not None else next(BOX[j] for d in range(1, len(BOX)) for j in (i - d, i + d) if 0 <= j < len(BOX) and BOX[j] is not None)
       for i, b in enumerate(BOX)]                        # quadro sem detecção: vizinho mais próximo

plan, prev, alt, used = [], None, False, set()
for i, s in enumerate(segs):
    hit = [w for w in WIDE_SRC if abs(s["a"] - w) < 0.05]
    if hit:
        kind = "W"
        alt = False                                    # depois do aberto, volta sempre no A
        used.update(hit)
    elif s["dur"] < 0.6 and prev in ("A", "B"):
        kind = prev
    elif i == 0:
        kind = "B"                                     # gancho já fechado
    else:
        kind = "B" if alt else "A"
        alt = not alt
    plan.append(kind)
    prev = kind


def smooth(v):
    v = np.array(v, float)
    if len(v) < 3:
        return v
    med = np.array([np.median(v[max(0, i - 2):i + 3]) for i in range(len(v))])
    k = np.ones(5) / 5
    pad = np.pad(med, 2, mode="edge")
    return np.convolve(pad, k, mode="valid")


tracks = []
for s, kind in zip(segs, plan):
    i0 = int(round(s["out"] * CF)); i1 = max(i0 + 1, int(round((s["out"] + s["dur"]) * CF)))
    bs = [BOX[min(i, len(BOX) - 1)] for i in range(i0, i1)]
    t = np.array([(i + 0.5) / CF for i in range(i0, i1)])
    h = smooth([b[3] for b in bs]); cx = smooth([b[0] + b[2] / 2 for b in bs]); top = smooth([b[1] for b in bs])
    tracks.append((t, h, cx, top, float(np.median([b[3] for b in bs]))))


def xform(t):
    """(z, tx, ty) do quadro no instante t: x' = z*x + tx"""
    k = max(i for i, s in enumerate(segs) if s["out"] <= t + 1e-6)
    kind = plan[k]
    if kind == "W":
        return 1.0, 0.0, 0.0
    H, T = SHOT[kind]
    ts, h, cx, top, hmed = tracks[k]
    hi, cxi, topi = (float(np.interp(t, ts, v)) for v in (h, cx, top))
    z = (H / hmed) ** (1 - K) * (H / hi) ** K
    z = min(ZMAX, max(ZMIN, z))
    tx = min(0.0, max(VW - VW * z, VW / 2 - cxi * z))
    ty = min(0.0, max(VH - VH * z, T - topi * z))
    return z, tx, ty


def warp(fr, z, tx, ty):
    if z == 1.0 and tx == 0 and ty == 0:
        return fr
    M = np.float32([[z, 0, tx], [0, z, ty]])
    out = cv2.warpAffine(fr, M, (VW, VH), flags=cv2.INTER_LANCZOS4, borderMode=cv2.BORDER_REPLICATE)
    amt = 0.5 * (z - 1) / (ZMAX - 1) if ZMAX > 1 else 0.0   # realce só na medida do zoom
    if amt > 0.02:
        bl = cv2.GaussianBlur(out, (0, 0), 1.3)
        out = cv2.addWeighted(out, 1 + amt, bl, -amt, 0)
    return out


def frames(path):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], stdout=subprocess.PIPE, bufsize=1 << 24)
    n = VW * VH * 3
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            p.kill(); return
        yield np.frombuffer(b, np.uint8).reshape(VH, VW, 3)


print("planos:", " ".join(f'{s["out"]:.2f}{k}' for s, k in zip(segs, plan)))
if not WIDE_SRC:
    print('AVISO: sem "planos": {"aberto": [...]} no estudio.json, tudo em plano fechado. Início na fonte ("a") de cada trecho:')
    for s in segs:
        print(f'  saída {s["out"]:6.2f}  a {s["a"]:7.2f}  {s["label"][:60]}')
miss = [w for w in WIDE_SRC if w not in used]
if miss:
    print("AVISO: no \"aberto\" sem trecho que comece ali (a EDL mudou?):", miss)

if len(sys.argv) > 1:                                  # quadros de teste
    os.makedirs("qc", exist_ok=True)
    for t in map(float, sys.argv[1].split(",")):
        fr = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", SRC, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                            capture_output=True, check=True).stdout
        fr = np.frombuffer(fr, np.uint8).reshape(VH, VW, 3)
        z, tx, ty = xform(t)
        cv2.imwrite(f"qc/rf_{t:06.2f}.jpg", warp(fr, z, tx, ty), [cv2.IMWRITE_JPEG_QUALITY, 88])
        print(f"{t:6.2f} z {z:.2f} tx {tx:6.0f} ty {ty:6.0f}")
    sys.exit()

# chin.json no quadro novo
nb = []
for i, b in enumerate(BOX):
    z, tx, ty = xform((i + 0.5) / CF)
    nb.append([int(b[0] * z + tx), int(b[1] * z + ty), int(b[2] * z), int(b[3] * z)])
with open("chin.json", "w") as f:
    json.dump({"fps": CF, "y": [b[1] + int(b[3] * 1.12) for b in nb], "box": nb}, f)

enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                        "-i", SRC, "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "15", "-pix_fmt", "yuv420p",
                        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-c:a", "copy", "-movflags", "+faststart", OUT],
                       stdin=subprocess.PIPE)
n = 0
for fr in frames(SRC):
    z, tx, ty = xform(n / FPS)
    enc.stdin.write(warp(fr, z, tx, ty).tobytes())
    n += 1
enc.stdin.close(); enc.wait()
print("quadros", n, "->", OUT)
