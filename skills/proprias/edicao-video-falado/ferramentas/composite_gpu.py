"""Versão GPU (PyTorch/CUDA) do composite.py: a preparação e os parâmetros aprovados vêm do próprio composite.py (importado), e só a conta
de cada quadro (estúdio de LED, luz colorida na pessoa, borda misturada, grão) roda na placa. Feito para uma máquina com GPU NVIDIA (testado numa L4)
no CPU de um servidor com vCPUs lentos a composição andava a ~0,8 quadro/s e num notebook de 4 núcleos a ~4.

  $VENV_TORCH/bin/python -I $PIPE/composite_gpu.py [t1,t2,...]

Mesmo uso do composite.py: sem argumento grava ../assets/footage/fala_estudio.mp4 (áudio copiado); Q0/Q1/PART fazem um pedaço.
Com t1,t2,... compara com a versão CPU nesses instantes (PSNR e diferença máxima) e grava matte/qcg_<t>.png (CPU | GPU | diferença x10).
Fonte com "mesa" ou "limpar" no estudio.json: esses quadros caem na conta do CPU (frame do composite.py), que é a referência.
Os desfoques, reduções e ampliações reproduzem os do OpenCV (núcleo gaussiano, borda refletida, meia célula, peso de 1/32 no warpAffine)."""
import os, queue, subprocess, sys, threading, time
import numpy as np
import torch
import torch.nn.functional as Fn

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import composite as C   # noqa: E402  roda a preparação: rosto, luz principal, mesa, zonas, grão e o estúdio (camadas de luz)
import studio as S      # noqa: E402

torch.backends.cuda.matmul.allow_tf32 = False
torch.backends.cudnn.allow_tf32 = False
dev = torch.device("cuda")
VW, VH, FPS = C.VW, C.VH, C.FPS


def T(a):
    return torch.from_numpy(np.ascontiguousarray(a, dtype=np.float32)).to(dev)


# ---------- operações iguais às do OpenCV ----------
_gk = {}


def gblur(x, sigma):
    """cv2.GaussianBlur(x, (0, 0), sigma) em float32: núcleo de cvRound(8*sigma+1)|1 amostras, borda refletida (REFLECT_101). x: (C,H,W)"""
    if sigma not in _gk:
        k = int(np.rint(sigma * 4 * 2 + 1)) | 1
        g = np.exp(-((np.arange(k) - (k - 1) / 2) ** 2) / (2 * sigma * sigma))
        _gk[sigma] = T(g / g.sum())
    k = _gk[sigma]
    p = (len(k) - 1) // 2
    y = x[:, None]
    y = Fn.conv2d(Fn.pad(y, (p, p, 0, 0), mode="reflect"), k.view(1, 1, 1, -1))
    y = Fn.conv2d(Fn.pad(y, (0, 0, p, p), mode="reflect"), k.view(1, 1, -1, 1))
    return y[:, 0]


def half(x):   # cv2.resize(..., INTER_AREA) para a metade exata. x: (C,H,W)
    return Fn.avg_pool2d(x[None], 2)[0]


def up(x, size, mode="bilinear"):   # cv2.resize INTER_LINEAR / INTER_CUBIC (meia célula, borda repetida). x: (C,H,W)
    return Fn.interpolate(x[None], size=size, mode=mode, align_corners=False)[0]


def shift(m, dx, dy):   # composite.shift: desloca repetindo a borda. m: (H,W)
    h, w = m.shape
    ax, ay = abs(dx), abs(dy)
    p = Fn.pad(m[None, None], (ax, ax, ay, ay), mode="replicate")[0, 0]
    return p[ay - dy:ay - dy + h, ax - dx:ax - dx + w]


def warp_wrap(img, tx, ty):
    """cv2.warpAffine(img, [[1,0,tx],[0,1,ty]], BORDER_WRAP): translação com interpolação linear e peso quantizado em 1/32"""
    out = 0
    xs, ys = [], []
    for t, acc in ((tx, xs), (ty, ys)):
        n = int(np.floor(t))
        f = round((t - n) * 32) / 32
        if f >= 1:
            n, f = n + 1, 0.0
        acc += [(n, 1 - f), (n + 1, f)]
    for ny, wy in ys:
        for nx, wx in xs:
            if wx * wy:
                out = out + torch.roll(img, shifts=(ny, nx), dims=(0, 1)) * (wx * wy)
    return out


def tonemap(x):
    x = torch.clamp(x, min=0)
    y = (x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14)
    return torch.clamp(y, 0, 1) ** (1 / 2.2)


# ---------- estúdio (mesmas camadas do studio.py, agora na placa) ----------
WST = [T(w) for w in S.WST]
GST, CST, HST = T(S.GST), T(S.CST), T(S.HST)
FOG, VIG = T(S.noise), T(S.vig)
LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)


def studio_frame(t):
    c, spill = S.colors(t)
    cw = 0.35 * c + 0.65 * (c @ LUMA)[:, None]
    cg, cwg = T(c), T(cw)
    out = torch.stack([cg[:, ch] @ WST[ch] + cg[:, ch] @ GST + cwg[:, ch] @ CST for ch in range(3)])
    dy = (t * 3.0) % S.HQ
    d1 = warp_wrap(FOG, 0.7 * t, dy)
    d2 = warp_wrap(FOG, -1.3 * t, 0.55 * dy)
    dens = (0.25 + 0.75 * (0.6 * d1 + 0.4 * d2) ** 1.5).reshape(-1)
    hz = (cg.T @ HST) * dens[None] * 0.20
    hz = up(hz.reshape(3, S.HQ, S.WQ), (S.H2, S.W2), "bicubic")
    img = out.reshape(3, S.H2, S.W2) + hz + 0.002
    return tonemap(img * VIG[None]), spill            # (3, H2, W2) sRGB


# ---------- pessoa ----------
KEYP = {k: T(((C.EXPO * v) ** 2.2)[..., 0]) for k, v in C.key.items()}   # (H,W)
GRAIN = [T(n[..., 0]) for n in C.noise]
TINT = T(np.array([-0.012, 0.004, 0.028], np.float32)).view(3, 1, 1)


def frame_gpu(orig, F, A, i):
    """orig, F: (3,H,W) float 0..1; A: (H,W). Mesma conta do composite.frame (sem mesa/limpar)."""
    src = C.SRC_OF[min(i, len(C.SRC_OF) - 1)]
    g = F.mean(0, keepdim=True)
    F = g + (F - g) * C.SAT
    F = torch.clamp((F - 0.45) * C.CONTRAST + 0.45, 0, 1)
    F = torch.clamp(F + (1 - F) ** 3 * TINT, 0, 1)
    A = torch.clamp((A - C.CHOKE) / (1 - C.CHOKE), 0, 1)
    bgh, sp = studio_frame(i / FPS)
    ob = gblur(half((1 - A)[None]), C.SPILL_SIG)[0]
    spill = torch.zeros((3, VH // 2, VW // 2), device=dev) + T(C.AMBIENT * sp["A"]).view(3, 1, 1)
    for k, ((dx, dy), gain) in C.SPILL.items():
        spill = spill + shift(ob, -dx * C.SPILL_SHIFT, -dy * C.SPILL_SHIFT)[None] * T(sp[k] * gain).view(3, 1, 1)
    spill = up(spill, (VH, VW))
    F = torch.clamp(F ** 2.2 * (KEYP[src][None] + spill), 0, 1) ** (1 / 2.2)
    bg = up(bgh, (VH, VW))
    wrap_bg = up(gblur(bgh, 6), (VH, VW))
    edge = (A * gblur((1 - A)[None], 2.5)[0])[None] * C.WRAP
    F = F * (1 - edge) + wrap_bg * edge
    B = bg + GRAIN[i % len(GRAIN)][None]
    out = F * A[None] + B * (1 - A[None])
    return (torch.clamp(out, 0, 1) * 255 + 0.5).to(torch.uint8).permute(1, 2, 0).contiguous()


def compose(o8, f8, a8, i):
    """entradas uint8 (numpy) -> quadro uint8 HxWx3 (numpy)"""
    src = C.SRC_OF[min(i, len(C.SRC_OF) - 1)]
    if src in C.zones or src in C.table:                  # mesa/limpar: referência do CPU
        return C.frame(o8.astype(np.float32) / 255, f8.astype(np.float32) / 255, a8.astype(np.float32) / 255, i)
    tg = [torch.from_numpy(x).to(dev, non_blocking=True) for x in (o8, f8, a8)]
    o, f = (x.permute(2, 0, 1).float() / 255 for x in tg[:2])
    return frame_gpu(o, f, tg[2].float() / 255, i).cpu().numpy()


INS = ((os.path.join(C.FOOT, "fala.mp4"), "rgb24", 3), (os.path.join("matte", "fgr.mp4"), "rgb24", 3), (os.path.join("matte", "pha.mkv"), "gray", 1))

if C.TEST:
    for t in C.TEST:
        i = int(round(t * FPS))
        ims = []
        for path, pix, ch in INS:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, (i - FPS) / FPS - 0.01):.3f}", "-i", path, "-vf", f"select=eq(n\\,{min(i, FPS)})",
                                  "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", pix, "-"], capture_output=True).stdout
            ims.append(np.frombuffer(raw, np.uint8).reshape(VH, VW, ch))
        t0 = time.time()
        ref = C.frame(*(x.astype(np.float32) / 255 for x in (ims[0], ims[1], ims[2][..., 0])), i)
        t1 = time.time()
        gpu = compose(ims[0], ims[1], ims[2][..., 0].copy(), i)
        torch.cuda.synchronize()
        t2 = time.time()
        d = np.abs(ref.astype(np.int16) - gpu.astype(np.int16))
        mse = float((d.astype(np.float32) ** 2).mean())
        psnr = 99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse)
        print(f"t={t}: PSNR {psnr:.1f} dB, dif. máx {d.max()}, >2 em {100 * (d > 2).mean():.3f}% dos pixels | CPU {t1 - t0:.2f} s, GPU {t2 - t1:.3f} s", flush=True)
        side = np.concatenate([ref, gpu, np.clip(d * 10, 0, 255).astype(np.uint8)], 1)
        import cv2
        cv2.imwrite(os.path.join("matte", f"qcg_{t:05.1f}.png"), cv2.cvtColor(side[::2, ::2], cv2.COLOR_RGB2BGR))
    sys.exit()

# ---------- vídeo: leitura e gravação em threads, conta na placa ----------
SEL = ["-vf", f"select=gte(n\\,{C.Q0})", "-fps_mode", "passthrough"] if C.Q0 else []
procs = [subprocess.Popen(["ffmpeg", "-v", "error", "-i", p, *SEL, "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE, bufsize=1 << 24)
         for p, pix, _ in INS]
qin, qout = queue.Queue(8), queue.Queue(8)


def read_all():
    sizes = [VW * VH * ch for _, _, ch in INS]
    while True:
        bufs = [p.stdout.read(n) for p, n in zip(procs, sizes)]
        if any(len(b) < n for b, n in zip(bufs, sizes)):
            qin.put(None)
            return
        qin.put([np.frombuffer(b, np.uint8).reshape(VH, VW, ch) for b, (_, _, ch) in zip(bufs, INS)])


X264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p", "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
if C.PART:
    cmd = ["-i", "-", *X264, "-an", C.PART]
else:
    cmd = ["-i", "-", "-i", os.path.join(C.FOOT, "fala.mp4"), "-map", "0:v", "-map", "1:a", *X264, "-c:a", "copy", os.path.join(C.FOOT, "fala_estudio.mp4")]
enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), *cmd], stdin=subprocess.PIPE)


def write_all():
    while True:
        b = qout.get()
        if b is None:
            return
        enc.stdin.write(b)


th = [threading.Thread(target=read_all, daemon=True), threading.Thread(target=write_all, daemon=True)]
for x in th:
    x.start()
i, t0 = C.Q0, time.time()
while i < C.Q1:
    ims = qin.get()
    if ims is None:
        break
    qout.put(compose(ims[0], ims[1], ims[2][..., 0], i).tobytes())
    i += 1
    if i % 300 == 0:
        print(i, "quadros", f"{(i - C.Q0) / (time.time() - t0):.1f} q/s", flush=True)
qout.put(None)
th[1].join()
for p in procs:
    p.kill()
enc.stdin.close(); enc.wait()
print("ok", i, "quadros em", round(time.time() - t0), "s")
