#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "opencv-python-headless>=4.8,<5",
#     "numpy",
# ]
# ///
"""
Zonas Proibidas para Overlays (badges, cards, motion graphics).

Garante que nenhum overlay cubra o ROSTO, INFORMAÇÃO IMPORTANTE da cena
(terminal, tela do celular, produto, mãos executando a ação) ou a LEGENDA.

Subcomandos
-----------
grid   Gera quadros anotados (grade de 120px + rostos detectados + faixa da legenda)
       para o agente enxergar a cena e escrever o keepout.json com coordenadas exatas.

         uv run overlay_safe_zones.py grid VIDEO --at 3,10.5,24 --out DIR

place  Escolhe, para cada card, a posição/escala/variante que NÃO cobre nada importante.

         uv run overlay_safe_zones.py place VIDEO --cards cards.json \
             --keepout keepout.json --out placements.json --debug DIR

Formatos
--------
cards.json:
  [{"id": "c01", "start": 0.25, "end": 6.7,
    "variants": [{"name": "full", "w": 992, "h": 430},
                 {"name": "compact", "w": 420, "h": 300}],
    "scales": [1.0, 0.85, 0.72],          # opcional
    "xs": ["center", "left", "right"]}]   # opcional

keepout.json (coordenadas do quadro final, ex.: 1080x1920):
  [{"start": 24.0, "end": 51.0, "x": 0, "y": 0, "w": 1080, "h": 980,
    "label": "texto do terminal", "weight": 1.0}]
  "weight" opcional: 1.0 = informação importante (padrão); use 2.0 para algo
  crítico (ex.: LED/indicador citado na fala) e "ignore_faces": true no card
  quando o detector acusar falso positivo (mãos, objetos).

Saída placements.json:
  {"c01": {"variant": "full", "x": 44, "y": 1180, "scale": 1.0,
           "clean": true, "overlap_face_pct": 0, "overlap_keepout_pct": 0}}

Regras embutidas
----------------
- Faixa da legenda (y >= --caption-top, padrão 1500 em 1080x1920) é PROIBIDA.
- Topo da interface do app (y < --top-safe, padrão 150) é PROIBIDO.
- Coluna de botões do Reels/TikTok (x >= 980 e y >= 1180) recebe penalidade.
- Rosto detectado (Haar frontal + perfil, com margem para cabelo e queixo) e
  keepouts manuais são custo altíssimo; "clean=false" significa que não há
  espaço livre: use variante compacta, troque o momento ou NÃO mostre o card.
"""

import argparse
import json
import os
import subprocess
import sys

import cv2
import numpy as np

FACE_PAD = dict(x=0.15, top=0.30, bottom=0.40)  # testa/cabelo e queixo/barba


def probe(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
         "stream=width,height:format=duration", "-of", "json", video],
        capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    return d["streams"][0]["width"], d["streams"][0]["height"], float(d["format"]["duration"])


class Frames:
    def __init__(self, video):
        self.cap = cv2.VideoCapture(video)
        if not self.cap.isOpened():
            sys.exit(f"[!] Não consegui abrir {video}")

    def at(self, t):
        self.cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, t) * 1000.0)
        ok, frame = self.cap.read()
        return frame if ok else None


class FaceDetector:
    def __init__(self):
        base = cv2.data.haarcascades
        self.front = cv2.CascadeClassifier(os.path.join(base, "haarcascade_frontalface_alt2.xml"))
        self.profile = cv2.CascadeClassifier(os.path.join(base, "haarcascade_profileface.xml"))

    def detect(self, frame):
        H, W = frame.shape[:2]
        k = 540.0 / W
        small = cv2.resize(frame, (int(W * k), int(H * k)))
        gray = cv2.equalizeHist(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY))
        min_sz = (int(small.shape[1] * 0.12),) * 2
        boxes = list(self.front.detectMultiScale(gray, 1.1, 5, minSize=min_sz))
        boxes += list(self.profile.detectMultiScale(gray, 1.1, 5, minSize=min_sz))
        flipped = cv2.flip(gray, 1)
        for (x, y, w, h) in self.profile.detectMultiScale(flipped, 1.1, 5, minSize=min_sz):
            boxes.append((gray.shape[1] - x - w, y, w, h))
        out = []
        for (x, y, w, h) in boxes:
            x, y, w, h = x / k, y / k, w / k, h / k
            x0 = x - w * FACE_PAD["x"]
            x1 = x + w * (1 + FACE_PAD["x"])
            y0 = y - h * FACE_PAD["top"]
            y1 = y + h * (1 + FACE_PAD["bottom"])
            out.append((max(0, int(x0)), max(0, int(y0)), min(W, int(x1)), min(H, int(y1))))
        return out


def sample_times(start, end, fps):
    n = max(3, int((end - start) * fps))
    return [start + (end - start) * (i + 0.5) / n for i in range(n)]


def faces_over_window(frames, det, start, end, fps, hold=1.0):
    """Rostos por instante; segura a última detecção por `hold` s (cabeça inclinada some no Haar)."""
    res, last, last_t = [], [], -99.0
    for t in sample_times(start, end, fps):
        f = frames.at(t)
        boxes = det.detect(f) if f is not None else []
        if boxes:
            last, last_t = boxes, t
        elif t - last_t <= hold:
            boxes = last
        res.append((t, boxes))
    return res


def inter(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return max(0, x1 - x0) * max(0, y1 - y0)


def keepouts_at(keepout, t, weighted=False):
    out = []
    for k in keepout:
        if k["start"] <= t <= k["end"]:
            r = (k["x"], k["y"], k["x"] + k["w"], k["y"] + k["h"])
            out.append((r, float(k.get("weight", 1.0))) if weighted else r)
    return out


def resolve_x(mode, w, W, margin):
    if mode == "left":
        return margin
    if mode == "right":
        return W - margin - w
    return (W - w) // 2


def place_card(card, face_track, keepout, W, H, args):
    scales = card.get("scales", [1.0, 0.85, 0.72])
    xs = card.get("xs", ["center", "left", "right"])
    variants = card.get("variants") or [{"name": "full", "w": card["w"], "h": card["h"]}]
    rail = (980, 1180, W, H)
    best = None
    for vi, v in enumerate(variants):
        for s in scales:
            w, h = int(v["w"] * s), int(v["h"] * s)
            if w > W - 2 * args.margin:
                continue
            for xm in xs:
                x = resolve_x(xm, w, W, args.margin)
                for y in range(args.top_safe, args.caption_top - args.caption_gap - h + 1, 10):
                    r = (x, y, x + w, y + h)
                    area = float(w * h)
                    face_cov = ko_cov = 0.0
                    face_max = ko_max = 0.0
                    for t, faces in face_track:
                        fc = sum(inter(r, fb) for fb in faces)
                        kc = sum(inter(r, kb) * kw for kb, kw in keepouts_at(keepout, t, weighted=True))
                        face_cov += fc / area
                        ko_cov += kc / area
                        if faces:
                            face_max = max(face_max, fc / max(1, sum((fb[2] - fb[0]) * (fb[3] - fb[1]) for fb in faces)))
                        kbs = keepouts_at(keepout, t)
                        if kbs:
                            ko_max = max(ko_max, kc / max(1, sum((k[2] - k[0]) * (k[3] - k[1]) for k in kbs)))
                    n = max(1, len(face_track))
                    face_cov /= n
                    ko_cov /= n
                    rail_pen = inter(r, rail) / area
                    cost = (face_cov * 40 + ko_cov * 25 + rail_pen * 0.8
                            + (1 - s) * 1.2 + vi * 0.9)
                    if card.get("y_pref") is not None:
                        cost += abs(y - card["y_pref"]) / H * 0.3
                    if best is None or cost < best["cost"]:
                        best = dict(cost=round(cost, 4), variant=v["name"], x=x, y=y, w=w, h=h,
                                    scale=s, xmode=xm,
                                    overlap_face_pct=round(face_max * 100, 1),
                                    overlap_keepout_pct=round(ko_max * 100, 1))
    if best is None:
        return dict(clean=False, error="nenhuma variante cabe acima da legenda")
    best["clean"] = best["overlap_face_pct"] == 0 and best["overlap_keepout_pct"] == 0
    return best


def draw_debug(frame, faces, kos, rect, caption_top, label, W, H):
    img = frame.copy()
    ov = img.copy()
    cv2.rectangle(ov, (0, caption_top), (W, H), (0, 220, 255), -1)
    cv2.rectangle(ov, (980, 1180), (W, H), (0, 120, 255), -1)
    for k in kos:
        cv2.rectangle(ov, (int(k[0]), int(k[1])), (int(k[2]), int(k[3])), (0, 140, 255), -1)
    for f in faces:
        cv2.rectangle(ov, (f[0], f[1]), (f[2], f[3]), (0, 0, 255), -1)
    img = cv2.addWeighted(ov, 0.35, img, 0.65, 0)
    if rect:
        cv2.rectangle(img, (rect[0], rect[1]), (rect[2], rect[3]), (60, 255, 60), 8)
    cv2.putText(img, label, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 5, cv2.LINE_AA)
    return img


def draw_grid(frame, faces, caption_top, W, H):
    img = frame.copy()
    for x in range(0, W, 120):
        cv2.line(img, (x, 0), (x, H), (255, 255, 255), 1)
        cv2.putText(img, str(x), (x + 4, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    for y in range(0, H, 120):
        cv2.line(img, (0, y), (W, y), (255, 255, 255), 1)
        cv2.putText(img, str(y), (6, y - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
    for f in faces:
        cv2.rectangle(img, (f[0], f[1]), (f[2], f[3]), (0, 0, 255), 5)
    cv2.line(img, (0, caption_top), (W, caption_top), (0, 220, 255), 4)
    return img


def sheet(images, path, cols=6, tw=360):
    if not images:
        return
    th = int(images[0].shape[0] * tw / images[0].shape[1])
    tiles = [cv2.resize(i, (tw, th)) for i in images]
    while len(tiles) % cols:
        tiles.append(np.zeros_like(tiles[0]))
    rows = [cv2.hconcat(tiles[i:i + cols]) for i in range(0, len(tiles), cols)]
    cv2.imwrite(path, cv2.vconcat(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])


def cmd_grid(args):
    W, H, _ = probe(args.video)
    frames, det = Frames(args.video), FaceDetector()
    os.makedirs(args.out, exist_ok=True)
    imgs = []
    for t in [float(x) for x in args.at.split(",")]:
        f = frames.at(t)
        if f is None:
            continue
        img = draw_grid(f, det.detect(f), args.caption_top, W, H)
        cv2.putText(img, f"t={t:.2f}s", (W - 330, 90), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (255, 255, 255), 5)
        cv2.imwrite(os.path.join(args.out, f"grid_{t:07.2f}.jpg"), img)
        imgs.append(img)
    sheet(imgs, os.path.join(args.out, "grid_sheet.jpg"), cols=args.cols)
    print(f"[+] {len(imgs)} quadros com grade em {args.out}")


def cmd_place(args):
    W, H, _ = probe(args.video)
    cards = json.load(open(args.cards, encoding="utf-8"))
    keepout = json.load(open(args.keepout, encoding="utf-8")) if args.keepout else []
    frames, det = Frames(args.video), FaceDetector()
    result, debug_imgs = {}, []
    if args.debug:
        os.makedirs(args.debug, exist_ok=True)
    for c in cards:
        track = faces_over_window(frames, det, c["start"], c["end"], args.sample_fps)
        if c.get("ignore_faces"):
            track = [(t, []) for t, _ in track]
        p = place_card(c, track, keepout, W, H, args)
        result[c["id"]] = p
        flag = "OK " if p.get("clean") else "!! "
        print(f"{flag}{c['id']}: {p.get('variant')} x={p.get('x')} y={p.get('y')} "
              f"escala={p.get('scale')} rosto={p.get('overlap_face_pct')}% keepout={p.get('overlap_keepout_pct')}%")
        if args.debug and "x" in p:
            # quadro mais "carregado" da janela (mais rosto + keepout) para a verificação
            t_mid, faces_mid = max(track, key=lambda tf: len(tf[1]) + len(keepouts_at(keepout, tf[0])))
            f = frames.at(t_mid)
            if f is not None:
                rect = (p["x"], p["y"], p["x"] + p["w"], p["y"] + p["h"])
                img = draw_debug(f, faces_mid, keepouts_at(keepout, t_mid), rect, args.caption_top,
                                 f"{c['id']} {p['variant']} x{p['scale']}", W, H)
                cv2.imwrite(os.path.join(args.debug, f"{c['id']}.jpg"), img)
                debug_imgs.append(img)
    if args.debug:
        sheet(debug_imgs, os.path.join(args.debug, "placements_sheet.jpg"), cols=args.cols)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    bad = [k for k, v in result.items() if not v.get("clean")]
    print(f"[+] placements em {args.out}" + (f" | SEM ESPAÇO LIVRE: {', '.join(bad)}" if bad else " | todos limpos"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("grid", "place"):
        s = sub.add_parser(name)
        s.add_argument("video")
        s.add_argument("--caption-top", type=int, default=1500, help="y onde começa a faixa da legenda")
        s.add_argument("--cols", type=int, default=6)
        if name == "grid":
            s.add_argument("--at", required=True, help="tempos em segundos, separados por vírgula")
            s.add_argument("--out", required=True)
        else:
            s.add_argument("--cards", required=True)
            s.add_argument("--keepout", default=None)
            s.add_argument("--out", required=True)
            s.add_argument("--debug", default=None)
            s.add_argument("--sample-fps", type=float, default=3.0)
            s.add_argument("--top-safe", type=int, default=150)
            s.add_argument("--caption-gap", type=int, default=20)
            s.add_argument("--margin", type=int, default=44)
    args = ap.parse_args()
    cmd_grid(args) if args.cmd == "grid" else cmd_place(args)


if __name__ == "__main__":
    main()
