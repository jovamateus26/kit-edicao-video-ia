#!/usr/bin/env python3
"""
Regenera o inventário completo do registry HyperFrames usado pela skill.

Saídas (em ../referencias/):
  catalogo_hyperframes.json  lista bruta do registry + campo "funcao" e "baixado_local"
  catalogo_hyperframes.md    tabela por função, só descrição técnica do próprio registry

O catálogo é um INVENTÁRIO: não recomenda, não ordena por gosto e não associa itens a nichos.
Uso:  python3 atualizar_catalogo.py   (precisa de Node 22+ e internet)
"""
import glob
import json
import os
import subprocess
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SKILL, "referencias")
SHOWCASE = os.path.expanduser("~/Projetos/hyperframes-showcase")

# Ordem = prioridade para decidir a função principal de um item (primeira tag que bater).
FUNCOES = [
    ("legenda", {"captions", "caption-style"}, {"inline-highlight"}),
    ("transicao", {"transition", "transition-primitive", "transitions-dev-port", "wipe"}, set()),
    ("lower-third / identificacao", {"lower-third"}, set()),
    ("titulo / tipografia", {"title-card", "typography", "text", "text-effects", "handwritten", "kinetic-text"}, set()),
    ("dados / graficos / mapas", {"data", "chart", "map", "geography"}, set()),
    ("codigo / terminal", {"code", "developer", "code-animation"}, set()),
    ("ui / chat / cursor", {"mock-ui", "ui-props", "cursor", "chat"}, set()),
    ("social / notificacao / cta", {"social", "notification"}, set()),
    ("overlay / anotacao", {"overlay", "annotation", "highlight", "media-treatment-overlay"}, set()),
    ("produto / showcase / galeria", {"showcase", "product-demo", "carousel", "gallery", "images", "ad-template"}, set()),
    ("logo / marca", {"logo"}, set()),
    ("fundo / textura / shader", {"background", "shader", "webgpu", "webgpu-shader", "webgl", "texture", "gradient", "particles"}, set()),
    ("camera / 3d / video", {"camera", "3d", "3d-motion", "video-primitive", "depth"}, set()),
    ("primitiva de movimento", {"motion-primitive"}, set()),
]


def funcao(item):
    tags = set(item.get("tags", []))
    for nome, tagset, names in FUNCOES:
        if item["name"] in names or tags & tagset or (nome == "legenda" and item["name"].startswith("caption-")):
            return nome
    return "outros"


def local_names():
    return {os.path.basename(p) for p in glob.glob(os.path.join(SHOWCASE, "*", "*")) if os.path.isdir(p)}


def main():
    nodes = sorted(glob.glob(os.path.expanduser("~/.nvm/versions/node/v2[2-9]*/bin")), reverse=True)
    env = dict(os.environ)
    if nodes:
        env["PATH"] = nodes[0] + os.pathsep + env.get("PATH", "")
    res = subprocess.run(["npx", "-y", "hyperframes", "catalog", "--json"], stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL, text=True, env=env)
    if res.returncode != 0:
        sys.exit("[!] Falha ao ler o registry (precisa de internet e Node 22+).")
    items = json.loads(res.stdout)
    local = local_names()
    for it in items:
        it["funcao"] = funcao(it)
        it["baixado_local"] = it["name"] in local
        it.pop("preview", None)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "catalogo_hyperframes.json"), "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)

    ordem = [n for n, _, _ in FUNCOES] + ["outros"]
    lines = [
        "# Catálogo completo do registry HyperFrames",
        "",
        f"Inventário gerado por `scripts/atualizar_catalogo.py`: **{len(items)} itens** "
        f"({sum(i['type'] == 'block' for i in items)} blocks, {sum(i['type'] == 'component' for i in items)} components). "
        "Descrições copiadas do próprio registry. A ordem é alfabética dentro de cada função: nada aqui é recomendação de estilo.",
        "",
        "Legenda das colunas: **L** = já baixado em `~/Projetos/hyperframes-showcase`; dimensões `—` = component (se adapta ao host).",
        "",
        "Instalar: `npx hyperframes add NOME --dir <projeto>/public` · Buscar por significado: `npx hyperframes catalog --query \"...\"`",
        "",
    ]
    for nome in ordem:
        grupo = sorted((i for i in items if i["funcao"] == nome), key=lambda i: i["name"])
        if not grupo:
            continue
        lines += [f"## {nome} ({len(grupo)})", "", "| Item | Tipo | L | Dimensões | Duração | Descrição |", "|---|---|---|---|---|---|"]
        for i in grupo:
            d = i.get("dimensions") or {}
            dim = f"{d.get('width')}×{d.get('height')}" if d else "—"
            dur = f"{i['duration']:.1f}s" if i.get("duration") else "—"
            desc = (i.get("description") or i.get("title") or "").replace("|", "/").replace("\n", " ")
            if len(desc) > 180:
                desc = desc[:177].rstrip() + "…"
            lines.append(f"| `{i['name']}` | {i['type']} | {'✓' if i['baixado_local'] else ''} | {dim} | {dur} | {desc} |")
        lines.append("")
    with open(os.path.join(OUT, "catalogo_hyperframes.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[+] {len(items)} itens -> {OUT}/catalogo_hyperframes.{{json,md}}")


if __name__ == "__main__":
    main()
