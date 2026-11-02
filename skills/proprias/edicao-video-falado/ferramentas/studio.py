"""Estúdio escuro com LED animado (fundo padrão do giro desde 27/10/2026), montado em camadas de luz: cada segmento de fita, a
sanca, o neon, a luz da parede atrás da cabeça, o abajur e as luzinhas são uma camada de luz branca já desfocada (profundidade de
campo, bokeh maior no fundo de trás). Por quadro a cor de cada camada muda e elas somam em luz linear, como num estúdio de verdade:
as ripas de nogueira pegam a luz rasante do lado de cada fita, a neblina sobe pelos fachos e as luzinhas piscam.
Cor por notícia: cada tag do giro (tag-<id>-w no ../index.html, ou "topicos" no estudio.json) troca o clima em 1,2 s, e uma onda de
cor corre ao longo das fitas. O composite.py usa Studio().frame(t); a luz colorida que cai na pessoa sai das mesmas cores.

Roda na pasta .work do projeto (lê ./estudio.json e ../index.html). Teste só do fundo:
  uv run --with numpy --with opencv-python-headless python -I $PIPE/studio.py t1,t2,... -> studio/bg_<t>.jpg

estudio.json (opcional): {"climas": {"abertura": "marca", "n1": "alerta", "cta": "apocalipse", ...}} com nomes de CLIMAS ou
[matiz esq., matiz dir., matiz sanca]; "topicos": [[0, "abertura"], [3.2, "n1"], ...] substitui as tags do index.html.
Sem clima definido: abertura e cta em "marca", as notícias em rodízio de RODIZIO."""
import colorsys, json, os, re, sys
import numpy as np
import cv2

W = os.getcwd()
H2, W2 = 960, 540            # o fundo é calculado em meia resolução (ele é desfocado) e ampliado no composite
HQ, WQ = 240, 135            # neblina em 1/8
S = 0.5                      # coordenadas escritas em 1080x1920
R_WALL, R_DEEP = 5.0, 19.0   # raio do bokeh (px na meia resolução): painel de ripas e o fundo escuro atrás das fitas

# climas de cor: matiz da fita esquerda, da direita e da sanca (graus)
CLIMAS = {"marca": (190, 272, 235),       # ciano x violeta
          "alerta": (352, 224, 300),      # vermelho x azul: segurança, ataque, risco
          "violeta": (280, 320, 300),     # violeta x rosa: big techs, redes sociais, varejo
          "energia": (186, 214, 200),     # ciano x azul elétrico: data centers, chips, energia, infraestrutura
          "ambar": (24, 262, 285),        # âmbar x violeta: Anthropic/Claude, dinheiro, IPO
          "verde": (158, 205, 185),       # verde-água x azul: saúde, ciência, clima
          "apocalipse": (356, 286, 320)}  # vermelho x violeta: pergunta final dramática
RODIZIO = ["energia", "violeta", "ambar", "verde"]
CFG = json.load(open(os.path.join(W, "estudio.json"))) if os.path.exists(os.path.join(W, "estudio.json")) else {}
if "topicos" in CFG:
    TOPICS = [(float(t), n) for t, n in CFG["topicos"]]
else:
    html = open(os.path.join(W, "..", "index.html")).read() if os.path.exists(os.path.join(W, "..", "index.html")) else ""
    TOPICS = [(0.0, "abertura")] + sorted((float(t), n) for n, t in re.findall(r'id="tag-([\w-]+?)-w"[^>]*?data-start="([\d.]+)"', html))
MOOD, rod = {}, 0
for _, name in TOPICS:
    c = CFG.get("climas", {}).get(name)
    if c is None:
        c = "marca" if name in ("abertura", "cta") else RODIZIO[rod % len(RODIZIO)]
        rod += name not in ("abertura", "cta")
    MOOD[name] = tuple(CLIMAS[c]) if isinstance(c, str) else tuple(c)
FADE = 1.2
GAIN = {"strip": 1.0, "cove": 0.55, "neon": 0.9, "wash": 0.6, "lamp": 1.0, "fairy": 1.0, "rgb": 0.9}
EXPOSURE = 1.0

yy, xx = np.mgrid[0:H2, 0:W2].astype(np.float32)
rng = np.random.default_rng(11)


def X(v):
    return v * S


def disc(r):
    k = int(np.ceil(r)) + 1
    y, x = np.mgrid[-k:k + 1, -k:k + 1].astype(np.float32)
    d = np.sqrt(x * x + y * y)
    m = np.clip(r + 0.5 - d, 0, 1) * (0.85 + 0.15 * np.clip(d / r, 0, 1) ** 4)   # borda do bokeh um pouco mais clara, como lente
    return m / m.sum()


def defocus(img, r):
    return cv2.filter2D(img, -1, disc(r), borderType=cv2.BORDER_REPLICATE)


def bloom(m, k=1.0):
    return (cv2.GaussianBlur(m, (0, 0), 5) * 0.30 + cv2.GaussianBlur(m, (0, 0), 18) * 0.10 + cv2.GaussianBlur(m, (0, 0), 55) * 0.04) * k


def quarter(m):
    """luz espalhada na neblina em volta do emissor (duas escalas)"""
    return cv2.resize(cv2.GaussianBlur(m, (0, 0), 22) + cv2.GaussianBlur(m, (0, 0), 70) * 0.8, (WQ, HQ), interpolation=cv2.INTER_AREA)


def line_v(xl, y0, y1, h):
    """irradiância de uma fita vertical (fonte linear finita) num ponto da parede"""
    r = np.sqrt((xx - xl) ** 2 + h * h)
    a = (y1 - yy) / np.sqrt(r * r + (y1 - yy) ** 2)
    b = (y0 - yy) / np.sqrt(r * r + (y0 - yy) ** 2)
    return (a - b) * h / r


def line_h(yl, x0, x1, h):
    r = np.sqrt((yy - yl) ** 2 + h * h)
    a = (x1 - xx) / np.sqrt(r * r + (x1 - xx) ** 2)
    b = (x0 - xx) / np.sqrt(r * r + (x0 - xx) ** 2)
    return (a - b) * h / r


def rect(x0, x1, y0, y1):
    return (np.clip(np.minimum(xx - x0, x1 - xx) + 0.5, 0, 1) * np.clip(np.minimum(yy - y0, y1 - yy) + 0.5, 0, 1)).astype(np.float32)


# ---------- cenário: parede de ripas (nogueira sobre feltro preto) entre as fitas; fundo escuro e fundo atrás ----------
PX0, PX1, PY0, PY1 = X(178), X(892), X(96), X(1720)
LX, RX = X(145), X(925)
panel = (xx >= PX0) & (xx < PX1) & (yy > PY0) & (yy < PY1)
deep = (xx < X(126)) | (xx > X(944))
PER, SLAT = 16, 12
xs = (xx - PX0) % PER
is_slat = panel & (xs < SLAT)
u = (xs - (SLAT - 1) / 2) / (SLAT / 2)
tone = rng.uniform(0.80, 1.20, int(W2 / PER) + 3)
idx = np.clip(((xx - PX0) // PER).astype(int), 0, len(tone) - 1)
grain = cv2.resize(rng.normal(0, 1, (H2 // 10, W2)).astype(np.float32), (W2, H2), interpolation=cv2.INTER_CUBIC)
grain = 1 + 0.12 * cv2.GaussianBlur(grain, (0, 0), 0.6)
alb = np.empty((H2, W2, 3), np.float32)
alb[:] = (0.020, 0.020, 0.024)
wood = np.array([0.15, 0.085, 0.048], np.float32)
alb[is_slat] = wood * (tone[idx] * grain)[is_slat][:, None]
alb[panel & ~is_slat] = (0.008, 0.008, 0.010)
alb[deep] = (0.010, 0.010, 0.012)
depth_k = np.where(deep, 0.18, 1.0).astype(np.float32)


def facing(xl):
    f = np.clip(u * np.sign(xl - xx), 0, 1) ** 0.8
    return np.where(is_slat, 0.20 + 0.80 * f, np.where(panel, 0.25, 0.45)).astype(np.float32)


L = []   # camadas: (tipo, chave, parede iluminada 3ch, emissor 1ch, núcleo 1ch, neblina 1ch)


def add(kind, key, E, G=None, C=None, haze=None, r=R_WALL):
    Wl = defocus(alb * (E * depth_k)[..., None], r)
    z = np.zeros((H2, W2), np.float32)
    L.append((kind, key, Wl, z if G is None else G, z if C is None else C, np.zeros((HQ, WQ), np.float32) if haze is None else haze))


# fitas verticais em 8 segmentos cada (a cor corre ao longo da fita); no emissor cada segmento entra com peso triangular,
# então a cor desliza contínua de um segmento pro outro (sem degrau)
NSEG, SY0, SY1 = 8, X(30), X(1740)
SEGL = (SY1 - SY0) / NSEG
for side, xl in (("L", LX), ("R", RX)):
    full = rect(xl - X(7), xl + X(7), SY0, SY1)
    fcore = rect(xl - X(2.5), xl + X(2.5), SY0, SY1)
    for k in range(NSEG):
        y0, y1 = SY0 + SEGL * k, SY0 + SEGL * (k + 1)
        cy = (y0 + y1) / 2
        hat = np.clip(1 - np.abs(yy - cy) / SEGL, 0, 1)
        if k == 0:
            hat = np.where(yy < cy, 1.0, hat)
        if k == NSEG - 1:
            hat = np.where(yy > cy, 1.0, hat)
        m, core = full * hat, fcore * hat
        add("strip", (side, k), line_v(xl, y0, y1, X(34)) * facing(xl) * 2.0,
            G=(defocus(m, R_WALL) + bloom(m, 1.3)) * 1.4, C=defocus(core, R_WALL) * 2.2, haze=quarter(m) * 3.0)
# sanca no teto em 4 segmentos
for j in range(4):
    x0, x1 = X(1080) * j / 4, X(1080) * (j + 1) / 4
    m = rect(x0, x1, X(84), X(92))
    E = line_h(X(88), x0, x1, X(30)) * np.where(is_slat, 0.65, 0.35)
    add("cove", j, E * 0.55, G=(defocus(m, R_WALL) + bloom(m)) * 1.2, C=defocus(rect(x0, x1, X(86), X(90)), R_WALL) * 1.6, haze=quarter(m) * 2.0)
# neon "</>" na parede
neon = np.zeros((H2, W2), np.float32)
for pts in ([(742, 410), (712, 442), (742, 474)], [(775, 480), (805, 404)], [(838, 410), (868, 442), (838, 474)]):
    cv2.polylines(neon, [np.array([[X(a) * 4, X(b) * 4] for a, b in pts], np.int32)], False, 1.0, 4 * 4, cv2.LINE_AA, shift=2)
add("neon", 0, cv2.GaussianBlur(neon, (0, 0), 28) * 9 * facing(X(790)),
    G=(defocus(neon, R_WALL) + bloom(neon, 1.4)) * 1.1, C=defocus(cv2.erode(neon, np.ones((2, 2), np.uint8)), R_WALL) * 1.6, haze=quarter(neon) * 2.0)
# luz de parede atrás da cabeça (separa o cabelo escuro do fundo)
wash = np.exp(-(((xx - X(515)) / X(330)) ** 2 + ((yy - X(780)) / X(440)) ** 2)) * np.where(is_slat, 0.9, 0.35)
add("wash", 0, wash.astype(np.float32) * 1.7)
# abajur quente no fundo à esquerda (bola de bokeh grande) e luzinhas
lamp = np.zeros((H2, W2), np.float32); cv2.circle(lamp, (int(X(58)), int(X(880))), int(X(7)), 1.0, -1, cv2.LINE_AA)
add("lamp", 0, cv2.GaussianBlur(lamp, (0, 0), 70) * 60 * (deep | (xx < X(200))), G=defocus(lamp, R_DEEP * 1.5) * 8 + bloom(defocus(lamp, R_DEEP * 1.5), 6), haze=quarter(lamp) * 4)
# luzinhas penduradas lá no fundo (bokeh grande, tamanhos diferentes = profundidades diferentes), espalhadas dos dois lados
groups = {("fairy", 0): [], ("fairy", 1): [], ("rgb", 0): []}
pts_r = [(990, 250), (1050, 330), (965, 470), (1035, 560), (985, 700), (1060, 790), (1000, 930), (960, 1080), (1045, 1150)]
pts_l = [(40, 300), (95, 420), (25, 560), (80, 700), (35, 1010), (100, 1130)]
for i, (x, y) in enumerate(pts_r + pts_l):
    groups[("rgb", 0) if i % 3 == 2 else ("fairy", i % 2)].append((x + rng.uniform(-12, 12), y + rng.uniform(-25, 25), rng.uniform(0.6, 1.35), rng.uniform(0.45, 1.1)))
for (kind, key), pts in groups.items():
    G = np.zeros((H2, W2), np.float32)
    for x, y, d, e in pts:
        p = np.zeros((H2, W2), np.float32); cv2.circle(p, (int(X(x)), int(X(y))), 2, 1.0, -1, cv2.LINE_AA)
        G += defocus(p, R_DEEP * d) * 11 * d * e
    add(kind, key, np.zeros((H2, W2), np.float32), G=G + bloom(G, 0.9), haze=quarter(G) * 0.6)

N = len(L)
KIND = [l[0] for l in L]
KEY = [l[1] for l in L]
WST = [np.ascontiguousarray(np.stack([l[2][..., c].ravel() for l in L])) for c in range(3)]
GST = np.ascontiguousarray(np.stack([l[3].ravel() for l in L]))
CST = np.ascontiguousarray(np.stack([l[4].ravel() for l in L]))
HST = np.ascontiguousarray(np.stack([l[5].ravel() for l in L]))
del L

# neblina: ruído suave que sobe devagar (tileável), em 1/8
fy, fx = np.meshgrid(np.fft.fftfreq(HQ), np.fft.fftfreq(WQ), indexing="ij")
noise = np.zeros((HQ, WQ), np.float32)
for sg, a in ((18, 1.0), (8, 0.5), (4, 0.25)):                # desfoque no domínio da frequência = ruído que emenda nas bordas
    g = np.exp(-2 * (np.pi * sg) ** 2 * (fx ** 2 + fy ** 2))
    noise += np.real(np.fft.ifft2(np.fft.fft2(rng.normal(0, 1, (HQ, WQ))) * g)).astype(np.float32) * a * sg
noise = (noise - noise.min()) / (noise.max() - noise.min())
vig = (1 - 0.45 * np.clip(((xx - W2 / 2) / (W2 * 0.62)) ** 2 + ((yy - H2 * 0.42) / (H2 * 0.62)) ** 2, 0, 1)).astype(np.float32)


def hsv(h, s, v=1.0):
    return np.array(colorsys.hsv_to_rgb((h % 360) / 360, s, v), np.float32) ** 2.2


def lerp_hue(a, b, m):
    d = ((b - a + 180) % 360) - 180
    return a + d * m


def mood(t):
    cur = MOOD[TOPICS[0][1]]
    for t0, name in TOPICS[1:]:
        if t >= t0:
            m = min(1.0, (t - t0) / FADE)
            m = m * m * (3 - 2 * m)
            cur = tuple(lerp_hue(a, b, m) for a, b in zip(cur, MOOD[name]))
    return cur


def colors(t):
    hl, hr, hc = mood(t)
    c = np.zeros((N, 3), np.float32)
    strip = {"L": [], "R": []}
    for i, (kind, key) in enumerate(zip(KIND, KEY)):
        if kind == "strip":
            side, k = key
            ph = 0.0 if side == "L" else np.pi / 2
            h = (hl if side == "L" else hr) + 14 * np.sin(2 * np.pi * (t / 6.5 + k / NSEG) + ph)
            col = hsv(h, 0.92) * (1 + 0.07 * np.sin(2 * np.pi * t / 4.7 + ph))
            strip[side].append(col)
        elif kind == "cove":
            col = hsv(hc + 10 * np.sin(2 * np.pi * (t / 9 + key / 4)), 0.55)
        elif kind == "neon":
            col = hsv(325, 0.85)
        elif kind == "wash":
            col = 0.7 * hsv(228, 0.35) + 0.3 * (hsv(hl, 0.9) + hsv(hr, 0.9)) / 2
        elif kind == "lamp":
            col = np.array([1.0, 0.55, 0.24], np.float32) * (1 + 0.015 * np.sin(2 * np.pi * t * 7.3))
        elif kind == "fairy":
            col = np.array([1.0, 0.52, 0.20], np.float32) * 1.25 * (0.7 + 0.3 * np.sin(2 * np.pi * t / (3.1 + key) + 1.7 * key))
        elif kind == "rgb":
            col = hsv(hr + 30, 0.85) * (0.75 + 0.25 * np.sin(2 * np.pi * t / 2.6))
        c[i] = col * GAIN[kind] * EXPOSURE
    spill = {"L": np.mean(strip["L"][1:5], 0), "R": np.mean(strip["R"][1:5], 0), "T": hsv(hc, 0.55), "A": (hsv(hl, 0.9) + hsv(hr, 0.9)) / 2}
    return c, spill


def tonemap(x):
    x = np.maximum(x, 0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return np.clip(y, 0, 1) ** (1 / 2.2)


class Studio:
    def frame(self, t):
        """-> (fundo sRGB 0..1 em meia resolução HxWx3, spill em luz linear {L, R, T, A})"""
        c, spill = colors(t)
        lum = c @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        cw = 0.35 * c + 0.65 * lum[:, None]                       # núcleo do LED estoura quase branco, como na câmera
        out = np.empty((3, H2 * W2), np.float32)
        for ch in range(3):
            out[ch] = c[:, ch] @ WST[ch] + c[:, ch] @ GST + cw[:, ch] @ CST
        dy = (t * 3.0) % HQ                                        # neblina subindo ~12 px/s na resolução cheia
        d1 = cv2.warpAffine(noise, np.float32([[1, 0, 0.7 * t], [0, 1, dy]]), (WQ, HQ), borderMode=cv2.BORDER_WRAP)
        d2 = cv2.warpAffine(noise, np.float32([[1, 0, -1.3 * t], [0, 1, 0.55 * dy]]), (WQ, HQ), borderMode=cv2.BORDER_WRAP)
        dens = (0.25 + 0.75 * (0.6 * d1 + 0.4 * d2) ** 1.5).ravel()
        hz = (c.T @ HST) * dens[None] * 0.20
        hz = cv2.resize(hz.reshape(3, HQ, WQ).transpose(1, 2, 0), (W2, H2), interpolation=cv2.INTER_CUBIC)
        img = out.reshape(3, H2, W2).transpose(1, 2, 0) + hz + 0.002
        return tonemap(img * vig[..., None]), spill


if __name__ == "__main__":
    st = Studio()
    print("climas:", [(t, n, MOOD[n]) for t, n in TOPICS])
    os.makedirs(os.path.join(W, "studio"), exist_ok=True)
    for t in [float(v) for v in sys.argv[1].split(",")]:
        im, sp = st.frame(t)
        cv2.imwrite(os.path.join(W, "studio", f"bg_{t:05.1f}.jpg"), cv2.cvtColor((im * 255).astype(np.uint8), cv2.COLOR_RGB2BGR), [cv2.IMWRITE_JPEG_QUALITY, 92])
        print(t, {k: np.round(v, 2).tolist() for k, v in sp.items()})
