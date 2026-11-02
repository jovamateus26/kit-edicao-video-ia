#!/usr/bin/env python3
"""
Badge Kit — monta badges/overlays animados (HyperFrames) a partir de um spec JSON,
usando a biblioteca de modelos da skill (models.py) e o posicionamento seguro
(../scripts/overlay_safe_zones.py: nunca sobre rosto, informação importante ou legenda).

Comandos
--------
  models                                   lista os modelos de badge da skill (campos e deixas)
  captions-models                          lista os modelos caption-* (sem padrão: o estilo escolhe)
  hf-models [--funcao F] [--query txt]     lista os modelos HyperFrames BAIXADOS (~/Projetos/hyperframes-showcase)
  hf-install NOME --project DIR            copia um modelo baixado para DIR/public/compositions/ (ou indica o npx add)
  init --project DIR --video VIDEO         cria o projeto HyperFrames (fontes, GSAP, vídeo SDR com keyframes densos)
  build SPEC --project DIR [--draft]       gera DIR/public/index.html (usa DIR/placements.json se existir)
  measure --project DIR                    mede w/h reais de cada badge -> DIR/card_sizes.json
  place SPEC --project DIR --keepout K     calcula posições livres -> DIR/placements.json (+ debug em DIR/.debug)
  auto SPEC --project DIR --keepout K      build --draft -> measure -> place -> build (fluxo completo)
  gallery [--out PNG]                      gera a prévia visual de todos os modelos (preview/galeria.png)

Spec (exemplo completo: examples/reel3_sailfish.json)
----
  {"duration": 79.08, "fps": 30, "width": 1080, "height": 1920,
   "badges": [{"id": "c01", "model": "pill-banner", "start": 0.25, "end": 3.55,
               "fields": {"chip": "TENTATIVA #2", "accent": "SAILFISH OS", "title": "no Xperia XZ2"},
               "cues": {"chip": 0.35, "title": 0.5}}]}
  Campos opcionais por badge: xs, scales, ignore_faces, y_pref, draft_y (sobrescrevem o padrão do modelo).

  Bloco opcional "estilo" (vem do prompt/estilo.json; o kit não escolhe estilo):
    "estilo": {"badges": {"vars": {"--glass": "...", "--font-sans": "..."}, "css": "...", "legibility": false},
               "motion": {"in":  {"x": 120, "y": 0, "blur": 12, "duration": 0.5,  "ease": "power4.out"},
                          "out": {"x": -120, "y": 0, "blur": 12, "duration": 0.32, "ease": "power4.in"}}}
  Bloco "captions": model (obrigatório), words, vars, case (original|upper|lower), keywords,
    group {max_words, max_chars, pause}, scale, baseline_y, max_text_px.

O render (npx hyperframes render DIR/public -o out.mp4) já leva badges + legenda juntos.
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile

KIT = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(KIT)
sys.path.insert(0, KIT)
from models import LED, MODELS  # noqa: E402
import captions as CAP  # noqa: E402

SAFE_ZONES = os.path.join(SKILL, "scripts", "overlay_safe_zones.py")
HF_CATALOG = os.path.join(KIT, "hyperframes_models.json")


# ───────────────────────── utilitários ─────────────────────────
def q(t, fps):
    return round(round(float(t) * fps) / fps, 4)


def find_node():
    cands = sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/v2[2-9]*/bin/node")), reverse=True)
    return cands[0] if cands else (shutil.which("node") or "node")


def find_puppeteer():
    if os.environ.get("PUPPETEER_NODE_MODULES"):
        return os.environ["PUPPETEER_NODE_MODULES"]
    caches = [os.path.expanduser("~/.npm/_npx"), os.path.join(os.environ.get("LOCALAPPDATA", ""), "npm-cache", "_npx")]   # Windows: npm-cache
    achados = [d for c in caches for d in glob.glob(os.path.join(c, "*", "node_modules", "puppeteer-core"))]
    for d in sorted(achados, key=os.path.getmtime, reverse=True):
        return os.path.dirname(d) + "/"
    sys.exit("[!] puppeteer-core não encontrado. Rode uma vez: npx hyperframes doctor (instala o CLI e suas dependências).")


def find_chrome():
    pf, pf86, lad = (os.environ.get(k, "") for k in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"))
    for c in (os.environ.get("CHROME", ""), "/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium",
              "/usr/bin/chromium-browser", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              os.path.join(pf, r"Google\Chrome\Application\chrome.exe"), os.path.join(pf86, r"Google\Chrome\Application\chrome.exe"),
              os.path.join(lad, r"Google\Chrome\Application\chrome.exe"), os.path.join(pf86, r"Microsoft\Edge\Application\msedge.exe")):
        if c and os.path.exists(c):
            return c
    return shutil.which("google-chrome") or shutil.which("chromium") or "google-chrome"


def load_spec(path):
    spec = json.load(open(path, encoding="utf-8"))
    spec.setdefault("fps", 30)
    spec.setdefault("width", 1080)
    spec.setdefault("height", 1920)
    for b in spec["badges"]:
        if b["model"] not in MODELS:
            sys.exit(f"[!] Modelo desconhecido '{b['model']}' em {b['id']}. Veja: badge_kit.py models")
    return spec


def resolved(b):
    """Une os padrões do modelo com o que o spec sobrescreve."""
    m = MODELS[b["model"]]
    f = dict(m["fields"])
    f.update(b.get("fields", {}))
    return m, f, {k: b.get(k, m[k]) for k in ("width", "xs", "scales", "ignore_faces", "y_pref", "draft_y")}


# ───────────────────────── compilação GSAP ─────────────────────────
def compile_beats(C, beats, fps):
    js = []
    A = js.append
    for sel, t, kind, extra in beats:
        t = q(t, fps)
        S = f"{C} {sel}"
        if kind == "in":
            A(f"tl.fromTo('{S}', {{opacity:0, y:22}}, {{opacity:1, y:0, duration:0.42, ease:'power3.out'}}, {t});")
        elif kind == "stagger":
            A(f"tl.fromTo('{S}', {{opacity:0, y:24}}, {{opacity:1, y:0, duration:0.42, ease:'power3.out', stagger:0.12}}, {t});")
        elif kind == "pop":
            A(f"tl.fromTo('{S}', {{opacity:0, scale:0.7}}, {{opacity:1, scale:1, duration:0.5, ease:'back.out(1.7)'}}, {t});")
        elif kind == "strike":
            A(f"tl.fromTo('{S}', {{'--s':0}}, {{'--s':1, duration:0.35, ease:'power2.out'}}, {t});")
            A(f"tl.to('{C} .old', {{opacity:0.55, duration:0.3}}, {q(t + 0.2, fps)});")
        elif kind == "led":
            bg, sh = LED.get(extra or "blue", LED["blue"])
            A(f"tl.to('{C} .bulb', {{background:'{bg}', boxShadow:'{sh}', duration:0.25, ease:'power2.out'}}, {t});")
            A(f"tl.to('{C} .t-red', {{opacity:0, y:-20, duration:0.25}}, {t});")
            A(f"tl.fromTo('{C} .t-blue', {{opacity:0, y:20}}, {{opacity:1, y:0, duration:0.35, ease:'power3.out'}}, {t});")
            A(f"tl.fromTo('{C} .glass', {{boxShadow:'0 0 0 0 rgba(61,139,255,0)'}}, {{boxShadow:'0 0 90px 4px rgba(61,139,255,.45)', duration:0.3, ease:'power2.out'}}, {t});")
        elif kind == "type":
            text, dur = extra
            text = text.replace("\\", "\\\\").replace("'", "\\'")
            A(f"(function(){{const el=document.querySelector('{C} .type');const s='{text}';const o={{n:0}};"
              f"tl.to(o,{{n:s.length,duration:{dur},ease:'none',onUpdate:function(){{el.textContent=s.slice(0,Math.round(o.n));}}}},{t});}})();")
        elif kind == "select":
            sa, others = f"{C} .slot[data-i=\"{extra}\"]", f"{C} .slot:not([data-i=\"{extra}\"])"
            A(f"tl.to('{sa}', {{borderColor:'#4ade80', background:'rgba(74,222,128,.14)', boxShadow:'0 0 50px rgba(74,222,128,.35)', duration:0.35, ease:'power2.out'}}, {t});")
            A(f"tl.to('{sa} .name', {{color:'#4ade80', duration:0.3}}, {t});")
            A(f"tl.fromTo('{sa} .sel', {{opacity:0, scale:0.6}}, {{opacity:1, scale:1, duration:0.35, ease:'back.out(1.7)'}}, {t});")
            A(f"tl.to('{others}', {{opacity:0.4, duration:0.35}}, {t});")
        elif kind == "progress":
            t_end = q(extra, fps)
            d = round(max(0.3, t_end - t), 3)
            A(f"tl.fromTo('{C} .prog i', {{scaleX:0}}, {{scaleX:1, duration:{d}, ease:'power1.inOut'}}, {t});")
            A(f"(function(){{const el=document.querySelector('{C} .num');const o={{v:0}};"
              f"tl.to(o,{{v:100,duration:{d},ease:'power1.inOut',onUpdate:function(){{el.textContent=Math.round(o.v);}}}},{t});}})();")
            A(f"tl.to('{C} .pct .num', {{color:'#4ade80', duration:0.3}}, {t_end});")
        elif kind == "fldone":
            A(f"tl.to('{C} .fl-a', {{opacity:0, y:-18, duration:0.25}}, {t});")
            A(f"tl.fromTo('{C} .fl-b', {{opacity:0, y:18}}, {{opacity:1, y:0, duration:0.35, ease:'power3.out'}}, {t});")
            A(f"tl.fromTo('{C} .flashpill', {{boxShadow:'0 0 0 0 rgba(74,222,128,0)'}}, {{boxShadow:'0 0 60px 2px rgba(74,222,128,.45)', duration:0.3}}, {t});")
        elif kind == "check":
            A(f"tl.fromTo('{S}', {{opacity:0, x:30}}, {{opacity:1, x:0, duration:0.4, ease:'power3.out'}}, {t});")
            A(f"tl.fromTo('{S} .box', {{scale:0.3, rotation:-25}}, {{scale:1, rotation:0, duration:0.45, ease:'back.out(1.8)'}}, {t});")
        elif kind == "stamp":
            A(f"tl.fromTo('{S}', {{opacity:0, scale:1.35, rotation:-4}}, {{opacity:1, scale:1, rotation:-1.5, duration:0.3, ease:'power4.in'}}, {t});")
            A(f"tl.fromTo('{C}', {{y:0}}, {{y:10, duration:0.08, yoyo:true, repeat:1, ease:'power2.out'}}, {q(t + 0.3, fps)});")
    return js


def cmd_build(args, draft=None):
    spec = load_spec(args.spec)
    draft = args.draft if draft is None else draft
    proj = os.path.abspath(args.project)
    pub = os.path.join(proj, "public")
    os.makedirs(os.path.join(pub, "cards"), exist_ok=True)
    pl_path = os.path.join(proj, "placements.json")
    placements = json.load(open(pl_path, encoding="utf-8")) if (os.path.exists(pl_path) and not draft) else {}
    fps, W, H, dur = spec["fps"], spec["width"], spec["height"], float(spec["duration"])
    hosts, js = [], []
    estilo = spec.get("estilo") or {}
    mv = estilo.get("motion") or {}
    mi = {"x": 120, "y": 0, "blur": 12, "duration": 0.5, "ease": "power4.out", **(mv.get("in") or {})}
    mo = {"x": -120, "y": 0, "blur": 12, "duration": 0.32, "ease": "power4.in", **(mv.get("out") or {})}
    for b in spec["badges"]:
        m, f, lay = resolved(b)
        cid, s, e = b["id"], q(b["start"], fps), q(b["end"], fps)
        width = f'{lay["width"]}px' if isinstance(lay["width"], int) else lay["width"]
        p = placements.get(cid)
        if p and "x" in p:
            pos = f'left:{p["x"]}px;top:{p["y"]}px;scale:{p["scale"]};width:{width};'
        else:
            pos = f'left:44px;top:{lay["draft_y"]}px;width:{width};'
        frag = f'<div class="card" data-card-id="{cid}" data-model="{m["name"]}" style="{pos}">{m["html"](f)}</div>'
        with open(os.path.join(pub, "cards", f"{cid}.html"), "w", encoding="utf-8") as fh:
            fh.write(frag + "\n")
        hosts.append(f'<div id="card-{cid}" class="card-host clip" data-card-id="{cid}" data-start="{s}" '
                     f'data-duration="{round(e - s, 4)}" data-track-index="3">{frag}</div>')
        C = f'.card-host[data-card-id="{cid}"] .card'
        # entrada/saída: parâmetros do bloco estilo.motion (valores-base = movimento técnico neutro do kit)
        js.append(f"tl.fromTo('{C}', {{x:{mi['x']}, y:{mi['y']}, opacity:0, filter:'blur({mi['blur']}px)'}}, "
                  f"{{x:0, y:0, opacity:1, filter:'blur(0px)', duration:{mi['duration']}, ease:'{mi['ease']}'}}, {s});")
        js.append(f"tl.set('{C}', {{filter:'none'}}, {q(s + float(mi['duration']) + 0.02, fps)});")
        js.append(f"tl.to('{C}', {{x:{mo['x']}, y:{mo['y']}, opacity:0, filter:'blur({mo['blur']}px)', startAt:{{filter:'blur(0px)'}}, "
                  f"duration:{mo['duration']}, ease:'{mo['ease']}'}}, {q(e - float(mo['duration']) - 0.02, fps)});")
        js += compile_beats(C, m["beats"](f, b.get("cues", {}), float(b["start"]), float(b["end"])), fps)
    cap = spec.get("captions")
    if cap and cap.get("model") and cap["model"] != "none":
        cap_model = cap["model"]
        wpath = cap["words"] if os.path.isabs(cap["words"]) else os.path.join(os.path.dirname(os.path.abspath(args.spec)), cap["words"])
        words = CAP.load_words(wpath)
        scale = float(cap.get("scale", 0.75))
        src, groups = CAP.adapt(cap_model, words, dur, scale=scale, max_text_px=int(cap.get("max_text_px", 1000)),
                                keywords=cap.get("keywords", []), variables=cap.get("vars"), project=proj, fps=fps,
                                case=cap.get("case", "original"), group=cap.get("group"), extra_css=cap.get("css", ""))
        os.makedirs(os.path.join(pub, "compositions"), exist_ok=True)
        with open(os.path.join(pub, "compositions", "captions.html"), "w", encoding="utf-8") as fh:
            fh.write(src)
        hosts.append(CAP.mount_html(cap_model, src, dur, W, H, scale=scale, baseline_y=int(cap.get("baseline_y", 1640))))
        print(f"[+] Legendas HyperFrames: {cap_model} · {len(words)} palavras · {len(groups)} grupos")
    elif cap:
        print("[i] Bloco captions sem 'model': nenhuma legenda montada (o modelo vem do estilo/prompt).")
    css = open(os.path.join(KIT, "badges.css"), encoding="utf-8").read()
    tb = estilo.get("badges") or {}
    if tb.get("vars"):
        css += "\n:root { " + " ".join(f"{k}: {v};" for k, v in tb["vars"].items()) + " }\n"
    css += "\n" + tb.get("css", "")
    legib = '<div class="legibility"></div>' if tb.get("legibility") else ""
    if tb.get("legibility_css"):
        css += "\n.legibility { " + tb["legibility_css"] + " }\n"
    video = spec.get("video", "input-video.mp4")
    html = f"""<!doctype html>
<html lang="pt-BR">
<head><meta charset="utf-8" /><style>{css}</style></head>
<body>
<div id="stage" data-composition-id="{spec.get('composition_id', 'badge-kit')}" data-start="0" data-duration="{dur}" data-fps="{fps}" data-width="{W}" data-height="{H}">
  <div id="video-wrap">
    <video id="bg-video" src="{video}" playsinline data-has-audio="true" data-start="0" data-duration="{dur}" data-track-index="1"></video>
  </div>
  {legib}
  {chr(10).join(hosts)}
  <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
  <script>
  (function () {{
    const tl = window.gsap.timeline({{ paused: true }});
{chr(10).join('    ' + l for l in js)}
    window.__timelines = window.__timelines || {{}};
    window.__timelines["{spec.get('composition_id', 'badge-kit')}"] = tl;
  }})();
  </script>
</div>
</body>
</html>
"""
    with open(os.path.join(pub, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"[+] {len(spec['badges'])} badges -> {pub}/index.html ({'rascunho' if not placements else 'posições de placements.json'})")


# ───────────────────────── medir / posicionar ─────────────────────────
MEASURE_JS = r"""
import { createRequire } from "module";
import { writeFileSync } from "fs";
import { pathToFileURL } from "url";
const [,, page_path, out_path, node_modules, chrome, shot] = process.argv;
const require = createRequire(node_modules);
const puppeteer = require("puppeteer-core");
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ["--allow-file-access-from-files", "--no-sandbox"] });
const page = await browser.newPage();
await page.setViewport({ width: 1080, height: 1920 });
await page.goto(pathToFileURL(page_path).href, { waitUntil: "load" });
const sizes = await page.evaluate(async () => {
  await document.fonts.ready;
  const out = {};
  document.querySelectorAll(".card").forEach((c) => { out[c.dataset.cardId] = { w: c.offsetWidth, h: c.offsetHeight }; });
  return out;
});
if (out_path !== "-") writeFileSync(out_path, JSON.stringify(sizes, null, 2));
if (shot) await page.screenshot({ path: shot, fullPage: true });
console.log(JSON.stringify(sizes));
await browser.close();
"""


def run_measure(page_path, out_path, shot=None):
    tmp = os.path.join(tempfile.mkdtemp(prefix="badgekit-"), "measure.mjs")
    with open(tmp, "w") as fh:
        fh.write(MEASURE_JS)
    cmd = [find_node(), tmp, page_path, out_path, find_puppeteer(), find_chrome()] + ([shot] if shot else [])
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"[!] Falha ao medir: {res.stderr[-800:]}")
    return json.loads(res.stdout.strip().splitlines()[-1])


def cmd_measure(args):
    proj = os.path.abspath(args.project)
    sizes = run_measure(os.path.join(proj, "public", "index.html"), os.path.join(proj, "card_sizes.json"))
    for k, v in sizes.items():
        print(f"  {k}: {v['w']}x{v['h']}")


def cmd_place(args):
    spec = load_spec(args.spec)
    proj = os.path.abspath(args.project)
    sizes = json.load(open(os.path.join(proj, "card_sizes.json"), encoding="utf-8"))
    cards = []
    for b in spec["badges"]:
        _, _, lay = resolved(b)
        sz = sizes[b["id"]]
        cards.append({"id": b["id"], "start": b["start"], "end": b["end"], "ignore_faces": lay["ignore_faces"],
                      "variants": [{"name": "full", "w": round(sz["w"]), "h": round(sz["h"])}],
                      "scales": lay["scales"], "xs": lay["xs"], "y_pref": lay["y_pref"]})
    cards_path = os.path.join(proj, "cards.json")
    json.dump(cards, open(cards_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    video = os.path.join(proj, "public", spec.get("video", "input-video.mp4"))
    cmd = ["uv", "run", "-q", SAFE_ZONES, "place", video, "--cards", cards_path, "--out", os.path.join(proj, "placements.json"),
           "--debug", os.path.join(proj, ".debug"), "--cols", "7"]
    if args.keepout:
        cmd += ["--keepout", os.path.abspath(args.keepout)]
    subprocess.run(cmd, check=True)
    print(f"[i] Confira {proj}/.debug/placements_sheet.jpg (verde nunca sobre vermelho/laranja/amarelo).")


def cmd_auto(args):
    cmd_build(args, draft=True)
    cmd_measure(args)
    cmd_place(args)
    cmd_build(args, draft=False)
    print("[+] Pronto. Próximo: npx hyperframes lint/snapshot/render em", os.path.join(os.path.abspath(args.project), "public"))


# ───────────────────────── projeto ─────────────────────────
def cmd_init(args):
    proj = os.path.abspath(args.project)
    pub = os.path.join(proj, "public")
    os.makedirs(os.path.join(pub, "fonts"), exist_ok=True)
    for fnt in glob.glob(os.path.join(KIT, "assets", "fonts", "*")):
        shutil.copy2(fnt, os.path.join(pub, "fonts"))
    if args.video:
        trc = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=color_transfer",
                              "-of", "default=nw=1:nk=1", args.video], capture_output=True, text=True).stdout.strip()
        vf = []
        if trc in ("arib-std-b67", "smpte2084"):
            tin = trc
            print(f"[i] Vídeo HDR ({trc}) detectado -> convertendo para SDR bt709 (evita falha do render HyperFrames).")
            vf = ["-vf", f"zscale=tin={tin}:min=bt2020nc:pin=bt2020:t=linear:npl=203,format=gbrpf32le,zscale=p=bt709,"
                         "tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p",
                  "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
        out = os.path.join(pub, "input-video.mp4")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", args.video] + vf +
                       ["-c:v", "libx264", "-crf", "17", "-g", str(args.fps), "-keyint_min", str(args.fps), "-pix_fmt", "yuv420p",
                        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k", out], check=True)
        dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                             capture_output=True, text=True).stdout.strip()
        print(f"[+] Vídeo preparado: {out} ({float(dur):.2f}s) — use esse valor em spec.duration")
    print(f"[+] Projeto pronto em {proj}. Próximos passos: grid (overlay_safe_zones.py) -> keepout.json -> spec -> auto")


# ───────────────────────── modelos HyperFrames baixados ─────────────────────────
def cmd_models(args):
    for k, m in MODELS.items():
        print(f"\n■ {k}  [{m['zone']}]  largura={m['width']}  xs={','.join(m['xs'])}")
        print(f"  {m['desc']}")
        print(f"  campos: {json.dumps(m['fields'], ensure_ascii=False)}")


def cmd_hf_models(args):
    cat = json.load(open(HF_CATALOG, encoding="utf-8"))
    print(f"Fonte local: {cat['fonte_local']}  |  galeria: {cat['galeria_local']}")
    for it in cat["models"]:
        if args.funcao and args.funcao.lower() not in it["funcao"].lower():
            continue
        hay = " ".join([it["name"], it["uso"], it["descricao_original"], " ".join(it["tags"])]).lower()
        if args.query and not all(w in hay for w in args.query.lower().split()):
            continue
        ok = "✓" if os.path.isdir(os.path.expanduser(it["path"])) else "✗ (baixar: npx hyperframes add)"
        dims = f"{it['dimensions']['width']}x{it['dimensions']['height']}" if it.get("dimensions") else "—"
        print(f"\n{ok} {it['name']}  [{it['type']} · {it['funcao']} · {dims}{' · ' + str(it['duration']) + 's' if it.get('duration') else ''}]")
        print(f"  {it['uso']}")
        print(f"  9:16: {it['adaptacao_9x16']}")


def cmd_captions_models(args):
    print("Sem modelo padrão: o modelo e suas vars vêm do estilo (prompt / estilo.json).")
    print("\nLEGENDA CONTÍNUA (use no bloco \"captions\" do spec):")
    for k, (pat, d) in CAP.CONTINUOUS.items():
        print(f"  {'✓' if CAP.find_model(k) else '✗'} {k.ljust(24)} {d}")
    print("\nDESTAQUE (frase única; use como momento de pico, não como trilha):")
    for k, d in CAP.HERO_ONLY.items():
        print(f"  {'✓' if CAP.find_model(k) else '✗'} {k.ljust(24)} {d}")
    print("\n✗ = não baixado: npx hyperframes add NOME --dir <projeto>/public")


def cmd_hf_install(args):
    cat = {i["name"]: i for i in json.load(open(HF_CATALOG, encoding="utf-8"))["models"]}
    it = cat.get(args.name)
    proj = os.path.abspath(args.project)
    src = os.path.expanduser(it["path"]) if it else None
    if not it or not os.path.isdir(src):
        print(f"[i] '{args.name}' não está baixado localmente. Instale do registry (precisa de internet):")
        print(f"    npx hyperframes add {args.name} --dir {os.path.join(proj, 'public')} --no-clipboard")
        return
    sub = "compositions" if it["type"] == "block" else os.path.join("compositions", "components")
    dst = os.path.join(proj, "public", sub)
    os.makedirs(dst, exist_ok=True)
    for f in glob.glob(os.path.join(src, "*")):
        target = os.path.join(dst, os.path.basename(f))
        if os.path.isdir(f):
            shutil.copytree(f, target, dirs_exist_ok=True)
        else:
            shutil.copy2(f, target)
    print(f"[+] {args.name} copiado para {dst}")
    if it["type"] == "block":
        d = it.get("dimensions") or {}
        print(f"""    Monte no index.html (bloco):
    <div class="clip" data-composition-id="{args.name}" data-composition-src="{sub}/{args.name}.html"
         data-start="T" data-duration="{it.get('duration') or 'D'}" data-track-index="4"
         data-width="{d.get('width', 1080)}" data-height="{d.get('height', 1920)}"></div>""")
    else:
        print(f"    Componente: cole HTML/CSS/JS de {sub}/{args.name}.html na composição (instruções no comentário do topo).")
    print(f"    {it['adaptacao_9x16']}")
    print("    Lembre: posição sempre pelo overlay_safe_zones.py (§6.B) — nunca sobre rosto, informação ou legenda.")


# ───────────────────────── galeria ─────────────────────────
GALLERY_CSS = """
body.gallery { width: 1080px; height: auto; overflow: visible; background: radial-gradient(120% 60% at 30% 0%, #2a3350 0%, #0d1018 60%); }
.gallery .wrap { padding: 60px 44px 80px; display: flex; flex-direction: column; gap: 46px; }
.gallery .item { position: relative; }
.gallery .item .card { position: relative; left: 0 !important; top: 0 !important; }
.gallery .lbl { font-family: "Ubuntu Sans Mono", monospace; font-size: 24px; color: #9aa6b8; letter-spacing: .12em; margin-bottom: 14px; }
.gallery .lbl b { color: #38e1ff; }
.gallery .side { display: flex; gap: 40px; align-items: flex-start; }
.gallery .t-red { opacity: 0 !important; } .gallery .t-blue { opacity: 1 !important; }
.gallery .bulb { background: radial-gradient(circle at 35% 30%, #d8ecff, #3d8bff 55%, #0b2e7a) !important; box-shadow: 0 0 44px 10px rgba(61,139,255,.85) !important; }
.gallery .slot .sel { opacity: 1 !important; } .gallery .slot[data-i="0"] { border-color: #4ade80; background: rgba(74,222,128,.14); }
.gallery .slot[data-i="0"] .name { color: #4ade80; } .gallery .slot:not([data-i="0"]) { opacity: .4; }
.gallery .strike { --s: 1; } .gallery .os.old { opacity: .55; }
.gallery .prog i { transform: scaleX(.77) !important; }
"""


def cmd_gallery(args):
    css = open(os.path.join(KIT, "badges.css"), encoding="utf-8").read().replace('url("fonts/', 'url("assets/fonts/')
    items, sides = [], []
    for k, m in MODELS.items():
        f = dict(m["fields"])
        body = m["html"](f)
        if k == "terminal-typing":
            body = body.replace('<span class="type"></span>', f'<span class="type">{f["command"]}</span>')
        if k == "progress-pill":
            body = body.replace('<span class="num">0</span>', '<span class="num">77</span>')
        width = f'{m["width"]}px' if isinstance(m["width"], int) else m["width"]
        block = (f'<div class="item"><div class="lbl"><b>{k}</b> · {m["zone"]}</div>'
                 f'<div class="card" data-card-id="{k}" style="width:{width}">{body}</div></div>')
        (sides if k in ("vertical-win", "side-status") else items).append(block)
    page = (f'<!doctype html><html><head><meta charset="utf-8"><style>{css}{GALLERY_CSS}</style></head>'
            f'<body class="gallery"><div class="wrap">{"".join(items)}<div class="side">{"".join(sides)}</div></div></body></html>')
    page_path = os.path.join(KIT, "preview", "galeria.html")
    os.makedirs(os.path.dirname(page_path), exist_ok=True)
    with open(page_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    out = os.path.abspath(args.out or os.path.join(KIT, "preview", "galeria.png"))
    run_measure(page_path, "-", shot=out)
    print(f"[+] Galeria: {out}  (HTML: {page_path})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("models")
    sub.add_parser("captions-models")
    s = sub.add_parser("hf-models"); s.add_argument("--funcao"); s.add_argument("--query")
    s = sub.add_parser("hf-install"); s.add_argument("name"); s.add_argument("--project", required=True)
    s = sub.add_parser("init"); s.add_argument("--project", required=True); s.add_argument("--video"); s.add_argument("--fps", type=int, default=30)
    s = sub.add_parser("build"); s.add_argument("spec"); s.add_argument("--project", required=True); s.add_argument("--draft", action="store_true")
    s = sub.add_parser("measure"); s.add_argument("--project", required=True)
    for name in ("place", "auto"):
        s = sub.add_parser(name); s.add_argument("spec"); s.add_argument("--project", required=True); s.add_argument("--keepout")
        if name == "auto":
            s.set_defaults(draft=False)
    s = sub.add_parser("gallery"); s.add_argument("--out")
    a = ap.parse_args()
    {"models": cmd_models, "captions-models": cmd_captions_models, "hf-models": cmd_hf_models, "hf-install": cmd_hf_install, "init": cmd_init, "build": cmd_build,
     "measure": cmd_measure, "place": cmd_place, "auto": cmd_auto, "gallery": cmd_gallery}[a.cmd](a)


if __name__ == "__main__":
    main()
