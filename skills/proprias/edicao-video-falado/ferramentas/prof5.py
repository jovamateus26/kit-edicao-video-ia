"""prof5.py AUDIO a-b : perfil de 5 ms (dB, vozeamento, centroide em Hz) para achar a fronteira exata entre fonemas"""
import subprocess, sys
import numpy as np
SR = 16000
x = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", sys.argv[1], "-map", "0:a:0", "-af", "aresample=async=1:first_pts=0",
                                  "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True, check=True).stdout, np.float32)
fr = np.fft.rfftfreq(400, 1 / SR)
for arg in sys.argv[2:]:
    a, b = map(float, arg.split("-"))
    print(arg)
    for t in np.arange(a, b, 0.005):
        i = int(t * SR); f = x[i:i + 400] - x[i:i + 400].mean()
        e = 20 * np.log10(np.sqrt(np.mean(f ** 2)) + 1e-9)
        ac = np.correlate(f, f, "full")[399:]
        v = ac[40:230].max() / (ac[0] + 1e-9)
        sp = np.abs(np.fft.rfft(f * np.hanning(400)))
        c = (sp * fr).sum() / (sp.sum() + 1e-9)
        print(f"  {t:8.3f} {e:6.1f} dB  v={v:.2f}  c={c:5.0f}  " + "#" * max(0, int((e + 60) / 2)))
