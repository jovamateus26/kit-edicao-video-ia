"""Acha os trechos em que o som do sistema toca (ex.: voz gerada pelo app), comparando a gravação de tela com o microfone.
Uso: uv run --with numpy python -I playback.py MICROFONE TELA OFF      (OFF = t_tela − t_mic, do sync.py)
Lista trechos (tempo da tela e do microfone) em que a tela fica bem mais alta que o mic: é áudio do sistema.
"""
import subprocess, sys
import numpy as np

SR, H = 16000, 1600   # janelas de 100 ms


def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:a:0", "-af", "aresample=async=1:first_pts=0",
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def db(x):
    n = len(x) // H
    return 20 * np.log10(np.sqrt(np.mean(x[:n * H].reshape(n, H) ** 2, axis=1)) + 1e-9)


mic, tela, off = load(sys.argv[1]), load(sys.argv[2]), float(sys.argv[3])
A, B = db(mic), db(tela)
k = int(round(off * 10))
n = min(len(B), len(A) + k)
diff = np.full(n, np.nan)
for i in range(max(0, k), n):
    diff[i] = B[i] - A[i - k]
loud = B[:n] > -40
base = np.nanmedian(diff[loud & ~np.isnan(diff)])
print(f"diferença típica tela − mic na fala: {base:.1f} dB (trechos abaixo: tela > {base + 9:.1f} dB acima do mic)")
flag = loud & (diff > base + 9)
i = 0
while i < n:
    if flag[i]:
        j = i
        while j < n and (flag[j] or (j + 2 < n and (flag[j + 1] or flag[j + 2]))):
            j += 1
        if j - i >= 3:
            print(f"  tela {i / 10:7.1f}-{j / 10:7.1f} s  (mic {i / 10 - off:7.1f}-{j / 10 - off:7.1f} s)  +{np.nanmedian(diff[i:j]) - base:.0f} dB")
        i = j
    else:
        i += 1
