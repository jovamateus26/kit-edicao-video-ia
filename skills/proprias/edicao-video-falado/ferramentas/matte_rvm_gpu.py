"""Versão GPU do matte_rvm.py (qualquer GPU NVIDIA com CUDA 12; testado numa L4): mesmo modelo ONNX do RVM, mesma memória entre quadros e mesmos arquivos de
saída, mas a imagem sobe para a placa em uint8 e tudo o que era numpy (float, transposição, memória do RVM, volta para uint8) fica na GPU
(IOBinding do onnxruntime + PyTorch). Leitura e gravação rodam em threads. No matte_rvm.py a rede fazia 57 q/s e a conversão em numpy
segurava tudo em ~6 q/s (12 min para 143 s). Roda na pasta .work, com a EDL fechada:

  $VENV_TORCH/bin/python -I $PIPE/matte_rvm_gpu.py [fala.mp4] [n_quadros]      -> matte/pha.mkv + matte/fgr.mp4
  MATTE=matte_gpu ... grava em outra pasta;  ... matte_rvm_gpu.py --comparar matte matte_gpu  compara dois recortes

O ambiente $VENV_TORCH (venv com torch + onnxruntime-gpu) tem torch 2.6.0+cu124 e onnxruntime-gpu 1.22.0 (os dois em CUDA 12: com driver NVIDIA 550 o CUDA vai até 12.4).
O modelo (15 MB) é o mesmo do matte_rvm.py, em ~/.cache/rvm/."""
import json, os, queue, subprocess, sys, threading, time
import numpy as np

VW, VH, FPS = 1080, 1920, 30


def frames(path, pix, ch):
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-f", "rawvideo", "-pix_fmt", pix, "-"], stdout=subprocess.PIPE, bufsize=1 << 24)
    n = VW * VH * ch
    while True:
        b = p.stdout.read(n)
        if len(b) < n:
            p.kill()
            return
        yield np.frombuffer(b, np.uint8).reshape(VH, VW, ch)


if "--comparar" in sys.argv:
    # pha quadro a quadro (ffv1 é sem perda: só sobra a diferença da conta); fgr (x264) por PSNR a cada 10 quadros
    a_dir, b_dir = sys.argv[sys.argv.index("--comparar") + 1:][:2]
    n, dmax, over2, sse = 0, 0, 0, 0.0
    for a, b in zip(frames(os.path.join(a_dir, "pha.mkv"), "gray", 1), frames(os.path.join(b_dir, "pha.mkv"), "gray", 1)):
        d = np.abs(a.astype(np.int16) - b.astype(np.int16))
        dmax, over2, sse, n = max(dmax, int(d.max())), over2 + int((d > 2).sum()), sse + float((d.astype(np.float32) ** 2).sum()), n + 1
    mse = sse / (n * VW * VH)
    print(f"pha: {n} quadros, dif. máx {dmax}, >2 em {100 * over2 / (n * VW * VH):.4f}% dos pixels, PSNR "
          f"{99.0 if mse == 0 else 10 * np.log10(255 ** 2 / mse):.1f} dB")
    k, ps = 0, []
    for a, b in zip(frames(os.path.join(a_dir, "fgr.mp4"), "rgb24", 3), frames(os.path.join(b_dir, "fgr.mp4"), "rgb24", 3)):
        if k % 10 == 0:
            m = float(((a.astype(np.float32) - b) ** 2).mean())
            ps.append(99.0 if m == 0 else 10 * np.log10(255 ** 2 / m))
        k += 1
    print(f"fgr: {k} quadros, PSNR mín {min(ps):.1f} dB, médio {np.mean(ps):.1f} dB ({len(ps)} quadros medidos)")
    sys.exit()

import torch                 # noqa: E402  (antes do onnxruntime: as libs CUDA do pip ficam carregadas)
import onnxruntime as ort    # noqa: E402

MODEL = os.path.expanduser("~/.cache/rvm/rvm_mobilenetv3_fp32.onnx")
if not os.path.exists(MODEL):
    sys.exit("modelo do RVM ausente: rode o matte_rvm.py uma vez (ele baixa e confere o hash)")
args = sys.argv[1:]
SRC = next((a for a in args if not a.isdigit()), os.path.join("..", "assets", "footage", "fala.mp4"))
LIMIT = next((int(a) for a in args if a.isdigit()), None)
OUT = os.environ.get("MATTE", "matte")

segs = json.load(open("segs.json"))["segments"]
resets, n, prev = set(), 0, None
for s in segs:
    if s["src"] != prev:
        resets.add(n)
    prev, n = s["src"], n + s["nf"]

ort.preload_dlls()
sess = ort.InferenceSession(MODEL, providers=["CUDAExecutionProvider"])
dev = torch.device("cuda")
DR = 0.25                                                   # backbone a 270x480: recomendado pelo RVM para HD
# formato da memória do RVM nessa resolução: uma passada de teste no próprio onnxruntime
SH = [r.shape for r in sess.run(None, {"src": np.zeros((1, 3, VH, VW), np.float32), **{f"r{k}i": np.zeros((1, 1, 1, 1), np.float32) for k in range(1, 5)},
                                      "downsample_ratio": np.array([DR], np.float32)})[2:]]
# Tudo ligado por ponteiro a tensores do PyTorch. Religar OrtValue (a memória que o próprio onnxruntime devolve, ou um valor no CPU)
# trava o onnxruntime 1.22 no 2º quadro; com ponteiros fixos e dois conjuntos de memória alternados não trava.
io = sess.io_binding()
src_t = torch.empty((1, 3, VH, VW), dtype=torch.float32, device=dev)
fgr_t = torch.empty((1, 3, VH, VW), dtype=torch.float32, device=dev)
pha_t = torch.empty((1, 1, VH, VW), dtype=torch.float32, device=dev)
dr_t = torch.tensor([DR], dtype=torch.float32, device=dev)
zero = torch.zeros((1, 1, 1, 1), dtype=torch.float32, device=dev)
mem = [[torch.zeros(sh, dtype=torch.float32, device=dev) for sh in SH] for _ in range(2)]


def bind(name, t, out=False):
    (io.bind_output if out else io.bind_input)(name, "cuda", 0, np.float32, list(t.shape), t.data_ptr())


bind("src", src_t); bind("downsample_ratio", dr_t); bind("fgr", fgr_t, True); bind("pha", pha_t, True)

os.makedirs(OUT, exist_ok=True)
enc_a = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "ffv1", "-pix_fmt", "gray", os.path.join(OUT, "pha.mkv")], stdin=subprocess.PIPE)
enc_f = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv444p", os.path.join(OUT, "fgr.mp4")], stdin=subprocess.PIPE)
qin, qa, qf = queue.Queue(8), queue.Queue(8), queue.Queue(8)


def read_all():
    for k, x in enumerate(frames(SRC, "rgb24", 3)):
        if LIMIT is not None and k >= LIMIT:
            break
        qin.put(x)
    qin.put(None)


def write_all(q, enc):
    while (b := q.get()) is not None:
        enc.stdin.write(b)


th = [threading.Thread(target=read_all, daemon=True), threading.Thread(target=write_all, args=(qa, enc_a), daemon=True),
      threading.Thread(target=write_all, args=(qf, enc_f), daemon=True)]
for t in th:
    t.start()
print("RVM em", sess.get_providers()[0], "com IOBinding; memória", SH, flush=True)
i, t0 = 0, time.time()
while (x := qin.get()) is not None:
    src_t.copy_(torch.from_numpy(x.copy()).to(dev).permute(2, 0, 1)[None].float() / 255)
    rin, rout = mem[i % 2], mem[(i + 1) % 2]
    for k in range(4):
        bind(f"r{k + 1}i", zero if i in resets else rin[k])   # fonte nova (ou 1º quadro): memória zerada, igual ao matte_rvm.py
        bind(f"r{k + 1}o", rout[k], True)
    torch.cuda.synchronize()                                 # o onnxruntime usa outro stream da placa
    sess.run_with_iobinding(io)
    io.synchronize_outputs()
    qa.put((pha_t[0, 0] * 255 + 0.5).clamp(0, 255).to(torch.uint8).cpu().numpy().tobytes())
    qf.put((fgr_t[0].permute(1, 2, 0) * 255 + 0.5).clamp(0, 255).to(torch.uint8).contiguous().cpu().numpy().tobytes())
    i += 1
    if i % 300 == 0:
        print(f"{i} quadros, {i / (time.time() - t0):.1f} q/s", flush=True)
for q in (qa, qf):
    q.put(None)
for t in th[1:]:
    t.join()
for e in (enc_a, enc_f):
    e.stdin.close(); e.wait()
print(f"ok {i} quadros em {time.time() - t0:.0f} s")
