"""Cliente do servidor de transcrição na GPU (whisperd.py). Use pelo wrapper `wh` (precisa do uv), que acerta as libs CUDA.

  wh file  ARQUIVO [SAIDA.json] [--prompt P]   transcrição completa palavra a palavra (áudio ou vídeo)
  wh snip  ARQUIVO a-b [a-b ...] [--prompt P]  janelas curtas com prompt de hesitações (tempos absolutos)
  wh try   ARQUIVO a-b+c-d [...] [--prompt P]  testa variantes de emenda (micro-fades) antes de mexer na EDL
  wh edit  FALA.wav SEGS.json [SAIDA.json]     fala montada: hesitações + tempo da fonte de cada palavra
  wh status | stop

Marcas na saída: ?=palavra incerta (p<0,5)  !=palavra esticada (>0,7 s: hesitação ou repetição escondida).
O servidor sobe no primeiro uso (~10 s) e sai sozinho depois de 20 min parado.
"""
import json, os, socket, subprocess, sys, time

D = os.path.dirname(os.path.abspath(__file__))
# Linux/macOS: socket Unix. Windows (o Python de lá não tem socket Unix) ou WHISPERD_PORT definido: TCP só no 127.0.0.1
if os.name == "nt" or os.environ.get("WHISPERD_PORT"):
    FAMILY, ADDR = socket.AF_INET, ("127.0.0.1", int(os.environ.get("WHISPERD_PORT", "47615")))
else:
    FAMILY, ADDR = socket.AF_UNIX, os.environ.get("WHISPERD_SOCK", f"/tmp/whisperd-{os.getuid()}.sock")
LOG = os.path.join(os.environ.get("XDG_CACHE_HOME", os.path.expanduser("~/.cache")), "whisperd", "server.log")
FILLERS = "Éé... ããã, hum, ahn, é, eh, tipo... a a gente, de de, né, então, hã."


def call(req, timeout=3600):
    s = socket.socket(FAMILY, socket.SOCK_STREAM)
    s.settimeout(timeout)
    s.connect(ADDR)
    s.sendall((json.dumps(req) + "\n").encode())
    buf = b""
    while not buf.endswith(b"\n"):
        chunk = s.recv(1 << 20)
        if not chunk:
            break
        buf += chunk
    s.close()
    return json.loads(buf)


def ensure():
    try:
        return call({"cmd": "ping"}, timeout=5)
    except OSError:
        pass
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    # o servidor sobrevive ao fim deste comando: sessão própria no Unix, processo destacado no Windows
    solto = ({"creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == "nt"
             else {"start_new_session": True})
    subprocess.Popen([sys.executable, "-X", "utf8", "-I", os.path.join(D, "whisperd.py")], stdout=open(LOG, "a"),
                     stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, env=os.environ.copy(), **solto)
    t0 = time.time()
    while time.time() - t0 < 180:
        time.sleep(0.5)
        try:
            r = call({"cmd": "ping"}, timeout=5)
            print(f"[whisperd] modelo {r['model']} em {r['device']} ({time.time() - t0:.0f} s para subir)", file=sys.stderr)
            return r
        except OSError:
            pass
    sys.exit(f"whisperd não subiu; veja {LOG}")


def ask(req):
    ensure()
    r = call(req)
    if not r.get("ok"):
        sys.exit(f"erro no whisperd: {r.get('error')}\n{r.get('trace', '')}")
    return r["result"]


def rng(arg):
    a, b = arg.split("-")
    return [float(a), float(b)]


def mark(w):
    return ("?" if w["p"] < 0.5 else "") + ("!" if w["e"] - w["s"] > 0.7 else "")


def opt(args, name, default=None):
    if name in args:
        i = args.index(name)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = args.pop(0)
    prompt = opt(args, "--prompt")
    if cmd == "status":
        try:
            print(call({"cmd": "ping"}, timeout=5))
        except OSError:
            print("whisperd parado")
        return
    if cmd == "stop":
        try:
            call({"cmd": "stop"}, timeout=10)
            print("whisperd parado")
        except OSError:
            print("whisperd já estava parado")
        return
    t0 = time.time()
    if cmd == "file":
        src = args[0]
        res = ask({"cmd": "transcribe", "audio": os.path.abspath(src), "prompt": prompt})[0]
        for s in res:
            print(f"[{s['start']:7.2f}-{s['end']:7.2f}] {s['text']}")
        out = args[1] if len(args) > 1 else None
        if out:
            json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    elif cmd == "snip":
        src, ranges = args[0], [rng(a) for a in args[1:]]
        res = ask({"cmd": "transcribe", "audio": os.path.abspath(src), "ranges": ranges,
                   "prompt": FILLERS + (" " + prompt if prompt else "")})
        for (a, b), segs in zip(ranges, res):
            print(f"{a}-{b} " + " ".join(f"{w['w']}@{w['s']:.2f}-{w['e']:.2f}{mark(w)}" for s in segs for w in s["words"]))
    elif cmd == "try":
        src = args[0]
        for arg in args[1:]:
            ranges = [rng(p) for p in arg.split("+")]
            segs = ask({"cmd": "transcribe", "audio": os.path.abspath(src), "ranges": ranges, "join": True,
                        "prompt": FILLERS + (" " + prompt if prompt else "")})[0]
            print(arg, "→", " ".join(f"{w['w']}@{w['s']:.2f}{mark(w)}" for s in segs for w in s["words"]))
    elif cmd == "edit":
        src, segs_path = args[0], args[1]
        segs = json.load(open(segs_path))["segments"]

        def where(t):
            s = max((s for s in segs if s["out"] <= t + 1e-6), key=lambda s: s["out"])
            return f"{s.get('src', '')[:1]}{s['a'] + (t - s['out']):.2f}"
        res = ask({"cmd": "transcribe", "audio": os.path.abspath(src), "prompt": FILLERS + (" " + prompt if prompt else "")})[0]
        words = []
        for s in res:
            print(" ".join(f"{w['w']}@{w['s']:.2f}-{w['e']:.2f}[{where(w['s'])}]{mark(w)}" for w in s["words"]))
            words += s["words"]
        if len(args) > 2:
            json.dump(words, open(args[2], "w"), ensure_ascii=False, indent=0)
    else:
        sys.exit(__doc__)
    print(f"[wh] {cmd} em {time.time() - t0:.1f} s", file=sys.stderr)


if __name__ == "__main__":
    main()
