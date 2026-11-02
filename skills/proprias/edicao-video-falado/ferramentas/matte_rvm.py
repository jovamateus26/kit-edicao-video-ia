"""Recorte da pessoa na fala montada com RVM (Robust Video Matting, ONNX no CPU): borda estável entre quadros e fio de cabelo.
Primeiro passo do fundo de estúdio do giro (depois vem o composite.py). Roda na pasta .work, com a EDL fechada (audit.py limpo):

  uv run --with numpy --with onnxruntime python -I $PIPE/matte_rvm.py [fala.mp4] [n_quadros]

Lê ../assets/footage/fala.mp4 (ou o arquivo dado) e segs.json (zera a memória do RVM quando a fonte troca).
Grava matte/pha.mkv (alfa em cinza, ffv1 sem perda) e matte/fgr.mp4 (cor do primeiro plano já sem a cor da parede antiga).
~3,3 q/s nos 4 núcleos: ~12 min para 80 s. Rode em segundo plano (pode ir junto com o wh na GPU). Mexeu na EDL, refaça.
O modelo (15 MB, GitHub oficial do RVM) é baixado uma vez para ~/.cache/rvm/. O `hyperframes remove-background` (u2net 320 px,
sem coerência entre quadros) não serve para trocar fundo: a borda treme e o cabelo vira bloco."""
import hashlib, json, os, subprocess, sys, time, urllib.request
import numpy as np
import onnxruntime as ort

MODEL = os.path.expanduser("~/.cache/rvm/rvm_mobilenetv3_fp32.onnx")
URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp32.onnx"
SHA = "88d4531297118f595bf2fd60f6f566aec2e559393802d1f436c380f0cbbd2828"
VW, VH, FPS = 1080, 1920, 30
args = [a for a in sys.argv[1:]]
SRC = next((a for a in args if not a.isdigit()), os.path.join("..", "assets", "footage", "fala.mp4"))
LIMIT = next((int(a) for a in args if a.isdigit()), None)

if not os.path.exists(MODEL):
    os.makedirs(os.path.dirname(MODEL), exist_ok=True)
    urllib.request.urlretrieve(URL, MODEL + ".part")
    if hashlib.sha256(open(MODEL + ".part", "rb").read()).hexdigest() != SHA:
        os.remove(MODEL + ".part")
        sys.exit("modelo do RVM com hash errado: download apagado")
    os.rename(MODEL + ".part", MODEL)

segs = json.load(open("segs.json"))["segments"]
resets, n, prev = set(), 0, None
for s in segs:
    if s["src"] != prev:
        resets.add(n)
    prev, n = s["src"], n + s["nf"]

os.makedirs("matte", exist_ok=True)
so = ort.SessionOptions()
so.intra_op_num_threads = 6
if "CUDAExecutionProvider" in ort.get_available_providers():      # com onnxruntime-gpu e placa NVIDIA: ~10x mais rápido que o CPU
    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
    sess = ort.InferenceSession(MODEL, so, providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
else:
    sess = ort.InferenceSession(MODEL, so, providers=["CPUExecutionProvider"])
print("RVM em", sess.get_providers()[0], flush=True)
dr = np.array([0.25], dtype=np.float32)   # backbone a 270x480: recomendado pelo RVM para HD

dec = subprocess.Popen(["ffmpeg", "-v", "error", "-i", SRC, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
enc_a = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "ffv1", "-pix_fmt", "gray", os.path.join("matte", "pha.mkv")], stdin=subprocess.PIPE)
enc_f = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{VW}x{VH}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv444p", os.path.join("matte", "fgr.mp4")], stdin=subprocess.PIPE)

fs, i, t0 = VW * VH * 3, 0, time.time()
rec = None
while LIMIT is None or i < LIMIT:
    buf = dec.stdout.read(fs)
    if len(buf) < fs:
        break
    if i in resets or rec is None:
        rec = [np.zeros((1, 1, 1, 1), np.float32)] * 4
    src = np.frombuffer(buf, np.uint8).reshape(VH, VW, 3).transpose(2, 0, 1)[None].astype(np.float32) / 255
    fgr, pha, *rec = sess.run(None, {"src": src, "r1i": rec[0], "r2i": rec[1], "r3i": rec[2], "r4i": rec[3], "downsample_ratio": dr})
    enc_a.stdin.write((pha[0, 0] * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
    enc_f.stdin.write((fgr[0].transpose(1, 2, 0) * 255 + 0.5).clip(0, 255).astype(np.uint8).tobytes())
    i += 1
    if i % 150 == 0:
        print(f"{i} quadros, {i / (time.time() - t0):.1f} q/s", flush=True)
dec.kill()
for e in (enc_a, enc_f):
    e.stdin.close(); e.wait()
print(f"ok {i} quadros em {time.time() - t0:.0f} s")
