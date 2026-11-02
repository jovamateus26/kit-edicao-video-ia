"""Servidor de transcrição (faster-whisper) que carrega o modelo UMA vez e fica na GPU atendendo pedidos (testado numa NVIDIA de 2 GB).

Não chame direto: o cliente `wh` sobe este servidor sozinho quando precisa e ele sai sozinho depois de IDLE_MIN
minutos parado (libera a memória da placa). Protocolo: uma linha JSON por pedido no socket (Unix; TCP local no
Windows), uma linha JSON de resposta. Pedidos: {"cmd": "ping" | "stop" | "transcribe", ...} — ver wh.py.
"""
import json, os, socket, subprocess, sys, time, traceback

import numpy as np

# Linux/macOS: socket Unix. Windows (o Python de lá não tem socket Unix) ou WHISPERD_PORT definido: TCP só no 127.0.0.1
if os.name == "nt" or os.environ.get("WHISPERD_PORT"):
    FAMILY, ADDR = socket.AF_INET, ("127.0.0.1", int(os.environ.get("WHISPERD_PORT", "47615")))
else:
    FAMILY, ADDR = socket.AF_UNIX, os.environ.get("WHISPERD_SOCK", f"/tmp/whisperd-{os.getuid()}.sock")
MODEL = os.environ.get("WHISPERD_MODEL", "medium")
IDLE_MIN = float(os.environ.get("WHISPERD_IDLE_MIN", "20"))
SR = 16000
# placa de 2 GB: o alocador do CTranslate2 devolve a memória em vez de guardar até 3/4 da placa em cache
os.environ.setdefault("CT2_CUDA_CACHING_ALLOCATOR_CONFIG", "4,3,12,104857600")
if os.name == "nt":
    # Windows: as DLLs do cuBLAS/cuDNN instaladas pelo pip (nvidia-*-cu12) ficam em site-packages\nvidia\*\bin
    import sysconfig
    for _sub in ("cublas", "cudnn"):
        _d = os.path.join(sysconfig.get_paths()["purelib"], "nvidia", _sub, "bin")
        if os.path.isdir(_d):
            os.add_dll_directory(_d)
            os.environ["PATH"] = _d + os.pathsep + os.environ.get("PATH", "")


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def load_model():
    from faster_whisper import WhisperModel
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            m = WhisperModel(MODEL, device="cuda", compute_type="int8_float32")
            m.transcribe(np.zeros(SR, np.float32), language="pt")      # força carregar cuBLAS/cuDNN já aqui
            return m, "cuda/int8_float32"
    except Exception as e:                                             # sem GPU utilizável: cai para o CPU
        log("GPU indisponível, usando CPU:", repr(e)[:200])
    return cpu_model(), "cpu/int8"


_cpu = []


def cpu_model():
    if not _cpu:
        from faster_whisper import WhisperModel
        _cpu.append(WhisperModel(MODEL, device="cpu", compute_type="int8"))
    return _cpu[0]


_audio = {}


def audio(path):
    """áudio mono 16 kHz em float32, com cache por (caminho, mtime)"""
    key = (os.path.abspath(path), os.path.getmtime(path))
    if key not in _audio:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-map", "0:a:0", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"],
                             capture_output=True, check=True).stdout
        if len(_audio) >= 6:
            _audio.pop(next(iter(_audio)))
        _audio[key] = np.frombuffer(raw, np.float32)
    return _audio[key]


def fade(y, a=0.02, b=0.025):
    y = y.copy()
    na, nb = min(len(y), int(a * SR)), min(len(y), int(b * SR))
    if na:
        y[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    if nb:
        y[-nb:] *= np.sin(np.linspace(np.pi / 2, 0, nb)) ** 2
    return y


def transcribe(model, req):
    """ranges=None: arquivo inteiro. ranges=[[a,b],...] com join=False: cada janela separada (tempos absolutos).
    join=True: emenda as janelas com micro-fades e transcreve como um trecho só (testar variantes de corte)."""
    x = audio(req["audio"])
    # best_of=1: o fallback por temperatura com 5 candidatos estoura uma placa de 2 GB em trechos de ruído
    opts = dict(language="pt", word_timestamps=True, vad_filter=False, beam_size=req.get("beam", 5), best_of=req.get("best_of", 1),
                condition_on_previous_text=False, initial_prompt=req.get("prompt") or None)
    jobs = []
    if not req.get("ranges"):
        jobs.append((0.0, x))
    elif req.get("join"):
        pad = np.zeros(int(0.3 * SR), np.float32)
        parts = [pad] + [fade(x[int(a * SR):int(b * SR)]) for a, b in req["ranges"]] + [pad]
        jobs.append((-0.3, np.concatenate(parts)))
    else:
        jobs += [(a, x[int(a * SR):int(b * SR)]) for a, b in req["ranges"]]
    out = []
    for off, y in jobs:
        segs, _ = model.transcribe(y, **opts)
        res = []
        for s in segs:
            res.append({"start": round(off + s.start, 2), "end": round(off + s.end, 2), "text": s.text.strip(),
                        "words": [{"w": w.word.strip(), "s": round(off + w.start, 2), "e": round(off + w.end, 2),
                                   "p": round(w.probability, 2)} for w in s.words]})
        out.append(res)
    return out


def main():
    t0 = time.time()
    model, dev = load_model()
    log(f"modelo {MODEL} em {dev} ({time.time() - t0:.1f} s)")
    if FAMILY == socket.AF_UNIX and os.path.exists(ADDR):
        os.remove(ADDR)
    srv = socket.socket(FAMILY, socket.SOCK_STREAM)
    srv.bind(ADDR)
    srv.listen(4)
    srv.settimeout(60)
    last = time.time()
    try:
        while True:
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                if time.time() - last > IDLE_MIN * 60:
                    log("parado há muito tempo, saindo")
                    break
                continue
            last, restart = time.time(), False
            with conn:
                buf = b""
                while not buf.endswith(b"\n"):
                    chunk = conn.recv(65536)
                    if not chunk:
                        break
                    buf += chunk
                try:
                    req = json.loads(buf)
                    if req["cmd"] == "ping":
                        resp = {"ok": True, "device": dev, "model": MODEL, "pid": os.getpid()}
                    elif req["cmd"] == "stop":
                        conn.sendall(b'{"ok": true}\n')
                        break
                    else:
                        t1 = time.time()
                        used = dev
                        try:
                            result = transcribe(model, req)
                        except RuntimeError as e:
                            if not dev.startswith("cuda"):
                                raise
                            # faltou memória na placa (ou o contexto CUDA quebrou): refaz no CPU e reinicia limpo depois
                            log("erro na GPU, refazendo no CPU:", repr(e)[:160])
                            result, used, restart = transcribe(cpu_model(), req), "cpu/int8 (fallback)", True
                        resp = {"ok": True, "device": used, "result": result}
                        log(f"{req['cmd']} {os.path.basename(req['audio'])} {len(req.get('ranges') or [])} janela(s) "
                            f"em {time.time() - t1:.1f} s [{used}]")
                except Exception as e:
                    resp = {"ok": False, "error": repr(e), "trace": traceback.format_exc()[-1500:]}
                conn.sendall((json.dumps(resp, ensure_ascii=False) + "\n").encode())
            last = time.time()
            if restart:
                log("reiniciando para limpar a GPU")
                break
    finally:
        srv.close()
        if FAMILY == socket.AF_UNIX and os.path.exists(ADDR):
            os.remove(ADDR)


if __name__ == "__main__":
    main()
