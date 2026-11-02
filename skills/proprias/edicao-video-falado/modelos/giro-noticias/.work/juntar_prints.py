"""Junta os shots-*.json do capture.mjs em prints.json (o formato que o make.py lê): {"<id>_<shot>": {file, w, h, hls, url}}.
Os arquivos mais novos ganham (rodar um job de novo substitui só os prints dele). Uso: python3 -I juntar_prints.py [../assets/img]"""
import glob, json, os, sys

W = os.path.dirname(os.path.abspath(__file__))
IMG = sys.argv[1] if len(sys.argv) > 1 else os.path.join(W, "..", "assets", "img")
out = {}
for f in sorted(glob.glob(os.path.join(IMG, "shots-*.json")), key=os.path.getmtime):
    for jid, job in json.load(open(f)).items():
        for name, shot in job["shots"].items():
            out[f"{jid}_{name}"] = {**shot, "url": job["url"]}
json.dump(out, open(os.path.join(W, "prints.json"), "w"), ensure_ascii=False, indent=1)
for k, v in out.items():
    print(f"{k:14s} {v['w']}x{v['h']}  grifos {len(v['hls'])}")
