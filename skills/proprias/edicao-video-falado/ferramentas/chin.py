"""Onde termina o rosto em cada quadro da fala montada (detector de rosto do OpenCV + 12% de margem para queixo e barba).
O print e as tags nunca sobem acima disso (regra de 28/10: nada cobre o rosto).
Roda na pasta .work depois do build.py (lê ../assets/footage/fala.mp4); o make.py do giro usa o chin.json para pôr os prints no espaço livre:
  uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/chin.py [saida.json]  -> chin.json {"fps": 5, "y": [...], "box": [x, y, w, h]}
O reframe.py chama com saída chin_raw.json (o chin.json dele já sai no quadro reenquadrado).
A versão do OpenCV vai fixa: a roda mais nova do cache veio sem CascadeClassifier. ~1 min para 85 s."""
import json, subprocess, sys
import cv2
import numpy as np
FPS, W, H, K = 5, 540, 960, 2
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", "../assets/footage/fala.mp4", "-vf", f"fps={FPS},scale={W}:{H}",
                      "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True).stdout
fr = np.frombuffer(raw, np.uint8).reshape(-1, H, W)
det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
ys, boxes, last = [], [], None
for f in fr:
    faces = det.detectMultiScale(f, 1.08, 5, minSize=(90, 90))
    if len(faces):
        x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
        last = [int(x * K), int(y * K), int(w * K), int(h * K)]
    boxes.append(last)
    ys.append(None if last is None else int(last[1] + last[3] * 1.12))
for i in range(len(ys)):                    # quadros sem detecção: vizinho mais próximo
    if ys[i] is None:
        ys[i] = next(ys[j] for d in range(1, len(ys)) for j in (i - d, i + d) if 0 <= j < len(ys) and ys[j] is not None)
json.dump({"fps": FPS, "y": ys, "box": boxes}, open(sys.argv[1] if len(sys.argv) > 1 else "chin.json", "w"))
y = np.array(ys)
for t0 in range(0, len(y), FPS * 5):
    print(f"{t0 / FPS:5.1f}s  queixo min {y[t0:t0 + FPS * 5].min():4d}  max {y[t0:t0 + FPS * 5].max():4d}")
print("sem rosto:", sum(b is None for b in boxes))
