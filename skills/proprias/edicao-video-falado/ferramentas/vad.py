"""Perfil fino (20 ms) de energia e vozeamento: vad.py AUDIO a-b [a-b ...]
Cada célula: V=vozeado ·=sem voz _=silêncio + dB negativo (V23 = vozeado a −23 dB). 25 células por linha (0,5 s).
Serve para achar o ponto exato de corte, vogal esticada ("nooo", "eee"), palavra repetida curta e respiração.
"""
import subprocess, sys
import numpy as np

SR = 16000
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)


def feat(t):
    i = int(t * SR)
    f = x[i:i + 640] - np.mean(x[i:i + 640])
    e = 20 * np.log10(np.sqrt(np.mean(f ** 2)) + 1e-9)
    ac = np.correlate(f, f, "full")[len(f) - 1:]
    return e, float(np.max(ac[40:230]) / (ac[0] + 1e-9))   # pico de autocorrelação entre 70 e 400 Hz


for arg in sys.argv[2:]:
    a, b = map(float, arg.split("-"))
    row = []
    for t in np.arange(a, b, 0.02):
        e, v = feat(t)
        c = "_" if e < -48 else ("V" if v > 0.45 and e > -40 else "·")
        row.append(f"{c}{min(99, int(-e)):02d}")
    print(arg)
    for i in range(0, len(row), 25):
        print(f"  {a + i * 0.02:7.2f} " + " ".join(row[i:i + 25]))
