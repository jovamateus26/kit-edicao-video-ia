"""Troca o fundo da fala montada pelo estúdio escuro com LED animado (studio.py): fundo padrão do giro desde 27/10/2026.
Roda na pasta .work depois do matte_rvm.py e do make.py (as tags do ../index.html marcam a troca de cor de cada notícia):

  uv run --with numpy --with opencv-python-headless python -I $PIPE/composite.py [t1,t2,...]

Com t1,t2,... só grava quadros de teste em matte/qc_<t>.jpg (~15 s cada); sem argumento grava ../assets/footage/fala_estudio.mp4
(~10 min para 80 s, áudio copiado). Depois: FALA=fala_estudio.mp4 python3 make.py, check/snapshot e render.

Luz na pessoa: grade de estúdio (exposição, contraste, saturação, sombras frias) e luz principal no rosto caindo pras bordas; a cor
das fitas entra LARGA e multiplicada pela cor da pele/roupa, e a borda se mistura com o fundo desfocado de trás. Nunca somar luz
por cima da borda: vira um contorno aceso em volta da pessoa, e isso foi reprovado nos testes (denuncia o recorte).

estudio.json (opcional, na .work), por fonte do segs.json:
  "mesa":   {"q": [a, b]}            mesa de verdade na frente: tudo abaixo de y = a + b*x vira primeiro plano, escurecido
  "limpar": {"q": [[x0, x1, y0, y1]]} canto onde o RVM às vezes puxa um pedaço do cenário (almofada, quadro): ali some o que é rosa/vermelho,
                                       esverdeado ou quase branco. Só use se a roupa não tiver essas cores
  "rosto":  {"q": [x, y]}            centro da luz principal; sem isso sai da mediana do alto do recorte de cada fonte
Os climas de cor ficam no mesmo arquivo (veja o studio.py)."""
import json, os, subprocess, sys
import numpy as np
import cv2

sys.dont_write_bytecode = True                     # não suja a pasta de ferramentas com __pycache__
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from studio import Studio   # noqa: E402

FOOT = os.path.join("..", "assets", "footage")
VW, VH, FPS = 1080, 1920, 30
TEST = [float(x) for x in sys.argv[1].split(",")] if len(sys.argv) > 1 else None
# pedaço da fala (vários processos em paralelo, cada quadro é independente): Q0=1800 Q1=2400 PART=matte/part_1800.mp4 -> só vídeo
Q0, Q1, PART = int(os.environ.get("Q0", 0)), int(os.environ.get("Q1", 10 ** 9)), os.environ.get("PART")
CFG = json.load(open("estudio.json")) if os.path.exists("estudio.json") else {}

# ---------- parâmetros do visual (aprovados no giro de 27/10/2026) ----------
EXPO = 0.88                               # exposição da pessoa (estúdio escuro: o rosto não pode ficar estourado contra o fundo)
KEY_SIG, KEY_LO = 650, 0.58               # luz principal: alcance (px) e o que sobra nas bordas
CONTRAST, SAT = 1.12, 0.90                # tira o ar de luz do dia (chapado e quente)
SPILL = {"L": ((-1, 0), 0.62), "R": ((1, 0), 0.66), "T": ((0, -1), 0.14)}   # luz das fitas (esq./dir.) e da sanca: direção e força
SPILL_SIG, SPILL_SHIFT = 26, 16           # largura da luz colorida (px na meia resolução): larga, sem virar linha
AMBIENT = 0.05                             # o clima de cor do estúdio em tudo (bem pouco)
WRAP = 0.55                                # borda misturada com o fundo desfocado de trás (escurece contra fundo escuro)
CHOKE = 0.03                               # aperta 3% do alfa (some o halo fino da borda)
TABLE_DARK = 0.55                          # mesa de verdade escurecida (bancada no escuro)
GRAIN = 2.2                                # grão no fundo (o fundo gerado é limpo demais perto do ruído do iPhone)

segs = json.load(open("segs.json"))["segments"]
SRC_OF = []
for s in segs:
    SRC_OF += [s["src"]] * s["nf"]


def face_centers():
    """centro do rosto por fonte: mediana (a cada 10 quadros) do topo do recorte + centro do alfa nos 20% de altura abaixo dele"""
    qw, qh = VW // 4, VH // 4
    p = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join("matte", "pha.mkv"), "-vf", f"select=not(mod(n\\,10)),scale={qw}:{qh}",
                        "-fps_mode", "vfr", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
    fr = np.frombuffer(p, np.uint8).reshape(-1, qh, qw).astype(np.float32) / 255
    pts = {}
    for j, a in enumerate(fr):
        rows = np.where((a > 0.5).sum(1) > 8)[0]
        if not len(rows):
            continue
        top = rows[0]
        band = a[top:top + int(qh * 0.2)]
        cx = (band.sum(0) * np.arange(qw)).sum() / max(band.sum(), 1)
        pts.setdefault(SRC_OF[min(j * 10, len(SRC_OF) - 1)], []).append((cx * 4, (top + qh * 0.145) * 4))
    return {k: tuple(np.median(np.array(v), 0)) for k, v in pts.items()}


studio = Studio()
yy, xx = np.mgrid[0:VH, 0:VW].astype(np.float32)
centers = face_centers()
centers.update({k: tuple(v) for k, v in CFG.get("rosto", {}).items()})
print("luz principal (centro do rosto por fonte):", {k: (round(x), round(y)) for k, (x, y) in centers.items()}, flush=True)
key = {k: (KEY_LO + (1 - KEY_LO) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * KEY_SIG ** 2)))[..., None] for k, (cx, cy) in centers.items()}
table = {k: np.clip((yy - (a + b * xx)) / 3 + 0.5, 0, 1) for k, (a, b) in CFG.get("mesa", {}).items()}
OPEN = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
zones = {}
for k, zs in CFG.get("limpar", {}).items():
    for x0, x1, y0, y1 in zs:
        w = np.ones((y1 - y0, x1 - x0), np.float32)         # borda suave da zona (sem degrau no alfa)
        fx = min(26, (x1 - x0) // 3); fy = min(12, (y1 - y0) // 4)
        if x1 < VW:
            w[:, -fx:] *= np.linspace(1, 0, fx)[None]
        if x0 > 0:
            w[:, :fx] *= np.linspace(0, 1, fx)[None]
        if y0 > 0:
            w[:fy] *= np.linspace(0, 1, fy)[:, None]
        if y1 < VH:
            w[-fy:] *= np.linspace(1, 0, fy)[:, None]
        zones.setdefault(k, []).append(((slice(y0, y1), slice(x0, x1)), w))
rng = np.random.default_rng(3)
noise = [rng.normal(0, GRAIN / 255, (VH, VW, 1)).astype(np.float32) for _ in range(6)]


def shift(m, dx, dy):
    """desloca repetindo a borda (np.roll daria a volta e acenderia a borda oposta do quadro)"""
    h, w = m.shape
    p = np.pad(m, ((abs(dy), abs(dy)), (abs(dx), abs(dx))), mode="edge")
    return p[abs(dy) - dy:abs(dy) - dy + h, abs(dx) - dx:abs(dx) - dx + w]


def frame(orig, fgr, pha, i):
    src = SRC_OF[min(i, len(SRC_OF) - 1)]
    A = pha
    F = fgr
    for PZ, zw in zones.get(src, []):
        o = orig[PZ]
        bad = ((o[..., 0] - o[..., 2] > 0.08) | ((o[..., 1] > o[..., 2] + 0.03) & (o[..., 1] > o[..., 0])) | (o.mean(-1) > 0.80)).astype(np.float32)
        if bad.any():
            rm = cv2.GaussianBlur(cv2.dilate(bad, np.ones((5, 5), np.uint8)), (0, 0), 2) * zw
            z = A[PZ] * (1 - rm)
            near = cv2.GaussianBlur(cv2.dilate(bad, np.ones((21, 21), np.uint8)), (0, 0), 3) * zw
            z = cv2.morphologyEx(z, cv2.MORPH_OPEN, OPEN) * near + z * (1 - near)   # limpa os pontinhos só perto do que saiu
            A = A.copy(); A[PZ] = z
    if src in table:
        T = table[src]
        A = np.maximum(A, T)
        F = F * (1 - T[..., None]) + orig * TABLE_DARK * T[..., None]
    g = F.mean(2, keepdims=True)
    F = g + (F - g) * SAT
    F = np.clip((F - 0.45) * CONTRAST + 0.45, 0, 1)
    F = np.clip(F + (1 - F) ** 3 * np.array([-0.012, 0.004, 0.028], np.float32), 0, 1)   # sombras um pouco frias; sem negativo (vira NaN no **2.2)
    A = np.clip((A - CHOKE) / (1 - CHOKE), 0, 1)
    bgh, sp = studio.frame(i / FPS)
    # luz colorida das fitas: o lado de fora (bem desfocado), empurrado pra dentro pelo lado de cada fita, vezes a cor da pessoa
    small = cv2.resize(1 - A, (VW // 2, VH // 2), interpolation=cv2.INTER_AREA)
    ob = cv2.GaussianBlur(small, (0, 0), SPILL_SIG)
    spill = np.zeros((VH // 2, VW // 2, 3), np.float32) + AMBIENT * sp["A"]
    for k, ((dx, dy), gain) in SPILL.items():
        spill += shift(ob, -dx * SPILL_SHIFT, -dy * SPILL_SHIFT)[..., None] * (sp[k] * gain)
    spill = cv2.resize(spill, (VW, VH), interpolation=cv2.INTER_LINEAR)
    lin = F ** 2.2
    F = np.clip(lin * ((EXPO * key[src]) ** 2.2 + spill), 0, 1) ** (1 / 2.2)
    bg = cv2.resize(bgh, (VW, VH), interpolation=cv2.INTER_LINEAR)
    wrap_bg = cv2.resize(cv2.GaussianBlur(bgh, (0, 0), 6), (VW, VH), interpolation=cv2.INTER_LINEAR)
    edge = (A * cv2.GaussianBlur(1 - A, (0, 0), 2.5))[..., None] * WRAP
    F = F * (1 - edge) + wrap_bg * edge
    B = bg + noise[i % len(noise)]
    out = F * A[..., None] + B * (1 - A[..., None])
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def reader(path, pix, ch):
    sel = ["-vf", f"select=gte(n\\,{Q0})", "-fps_mode", "passthrough"] if Q0 else []
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, *sel, "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE)
    n = VW * VH * ch

    def get():
        buf = p.stdout.read(n)
        if len(buf) < n:
            return None
        return np.frombuffer(buf, np.uint8).reshape(VH, VW, ch).astype(np.float32) / 255
    return p, get


if __name__ == "__main__":                        # composite_gpu.py importa a preparação daqui e troca só a conta por quadro
    INS = ((os.path.join(FOOT, "fala.mp4"), "rgb24", 3), (os.path.join("matte", "fgr.mp4"), "rgb24", 3), (os.path.join("matte", "pha.mkv"), "gray", 1))
    if TEST:
        for t in TEST:
            i = int(round(t * FPS))
            ims = []
            for path, pix, ch in INS:
                raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, (i - FPS) / FPS - 0.01):.3f}", "-i", path, "-vf", f"select=eq(n\\,{min(i, FPS)})",
                                      "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", pix, "-"], capture_output=True).stdout
                ims.append(np.frombuffer(raw, np.uint8).reshape(VH, VW, ch).astype(np.float32) / 255)
            o = frame(ims[0], ims[1], ims[2][..., 0], i)
            cv2.imwrite(os.path.join("matte", f"qc_{t:05.1f}.jpg"), cv2.cvtColor(o, cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
            print("qc", t, SRC_OF[min(i, len(SRC_OF) - 1)])
        sys.exit()

    rd = [reader(*a) for a in INS]
    X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
    if PART:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-", *X264, "-an", PART],
                               stdin=subprocess.PIPE)
    else:
        enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                            "-i", os.path.join(FOOT, "fala.mp4"), "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                            "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
                            "-c:a", "copy", os.path.join(FOOT, "fala_estudio.mp4")], stdin=subprocess.PIPE)   # sem -shortest: cortava 4 quadros
    i = Q0
    while i < Q1:
        o, f, a = (g() for _, g in rd)
        if o is None or f is None or a is None:
            break
        enc.stdin.write(frame(o, f, a[..., 0], i).tobytes())
        i += 1
        if i % 300 == 0:
            print(i, "quadros", flush=True)
    for p, _ in rd:
        p.kill()
    enc.stdin.close(); enc.wait()
    print("ok", i, "quadros")
