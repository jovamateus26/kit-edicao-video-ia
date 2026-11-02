"""Decodifica o vídeo e diz em que instantes o decodificador HEVC reclamou (cópia corrompida do iPhone): errmap.py ARQUIVO
Cada pedaço do arquivo é decodificado em ordem (1 thread, para o erro cair no quadro certo), vários pedaços em
paralelo, com -copyts para manter o tempo original e 2 s de folga antes de cada pedaço. O dano vai até o próximo quadro-chave (~1 s no iPhone).
"""
import os, re, subprocess, sys
from concurrent.futures import ThreadPoolExecutor

path = sys.argv[1]
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", path],
                           capture_output=True, text=True).stdout)
jobs = max(1, min(os.cpu_count() or 4, int(dur // 10) or 1))
step = dur / jobs


def scan(k):
    a = k * step
    s0 = max(0.0, a - 2.0)            # começa 2 s antes: os erros falsos de entrar no meio do GOP ficam fora da conta
    p = subprocess.run(["ffmpeg", "-hide_banner", "-threads", "1", "-v", "info", "-ss", f"{s0:.3f}", "-t", f"{a - s0 + step + 0.1:.3f}",
                        "-copyts", "-i", path, "-map", "0:v:0", "-an", "-vf", "showinfo=checksum=0", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace")
    pending, bad, msgs = [], [], {}
    for line in p.stderr.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
            if pending:
                if a <= t < a + step or (k == jobs - 1 and t >= a):   # cada instante conta num pedaço só
                    bad.append(t)
                    for x in pending:
                        msgs[x] = msgs.get(x, 0) + 1
                pending = []
            continue
        if re.search(r"\[hevc @|Invalid|Could not find ref|Error submitting|corrupt", line):
            pending.append(re.sub(r"0x[0-9a-f]+|\d+", "#", line.strip())[:90])
    return bad, msgs


with ThreadPoolExecutor(jobs) as ex:
    res = list(ex.map(scan, range(jobs)))
bad = sorted(t for b, _ in res for t in b)
msgs = {}
for _, m in res:
    for k, v in m.items():
        msgs[k] = msgs.get(k, 0) + v
print("quadros com erro:", len(bad))
groups = []
for t in bad:
    if groups and t - groups[-1][1] < 1.0:
        groups[-1][1] = t
    else:
        groups.append([t, t])
for a, b in groups:
    print(f"  {a:8.2f} -> {b:8.2f} s")
for k, v in sorted(msgs.items(), key=lambda x: -x[1])[:6]:
    print(f"  {v:4d}x {k}")
