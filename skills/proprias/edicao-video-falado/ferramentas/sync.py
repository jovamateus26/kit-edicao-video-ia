"""Sincroniza duas gravações pela palma: picos de energia nos primeiros 30 s + correlação cruzada + drift ao longo do arquivo.
Uso: uv run --with numpy python -I sync.py A.(MOV|mp4|wav) B.(MOV|mp4|wav)
Resultado: OFF = tB − tA (o mesmo som está em tA no arquivo A e em tA + OFF no arquivo B).
"""
import subprocess, sys
import numpy as np

SR = 16000


def load(p):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", p, "-map", "0:a:0", "-af", "aresample=async=1:first_pts=0",
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)


def lag(a, b):
    """deslocamento L (s) que melhor alinha: a[n] ≈ b[n + L]"""
    n = len(a)
    A, B = a - a.mean(), b - b.mean()
    c = np.fft.irfft(np.fft.rfft(B, 2 * n) * np.conj(np.fft.rfft(A, 2 * n)))
    k = int(np.argmax(c))
    if k > n:
        k -= 2 * n
    return k / SR


a, b = load(sys.argv[1]), load(sys.argv[2])
for name, x in (("A", a), ("B", b)):
    e = np.convolve(np.abs(x[:30 * SR]), np.ones(160) / 160, "same")
    peaks = []
    for i in np.argsort(e)[::-1]:
        if all(abs(i - p) > SR * 0.3 for p in peaks):
            peaks.append(i)
        if len(peaks) == 4:
            break
    print(f"{name} picos (palma = o mais forte): " + ", ".join(f"{p / SR:.3f} s ({e[p]:.2f})" for p in sorted(peaks)))
n = min(60 * SR, len(a), len(b))
off = lag(a[:n], b[:n])
print(f"OFF = tB − tA = {off:+.4f} s (correlação nos primeiros 60 s)")
# drift: janelas de 20 s ao longo do arquivo A
dur = len(a) / SR
for t in np.linspace(10, max(10, dur - 25), 6):
    ia, ib = int(t * SR), int((t + off) * SR)
    if ib - SR < 0 or ib + 21 * SR > len(b):
        continue
    wa, wb = a[ia:ia + 20 * SR], b[ib - SR:ib + 21 * SR]
    c = np.correlate(wb - wb.mean(), wa - wa.mean(), "valid")
    k = int(np.argmax(c))
    print(f"  em A {t:6.1f} s: OFF local {off + (k - SR) / SR:+.4f} s")
