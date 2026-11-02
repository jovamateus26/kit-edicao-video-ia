#!/usr/bin/env python3
"""
Módulo de B-Roll Inteligente e Elegante (B-Roll Engine).
Insere recortes visuais sutis (2 a 3.5 segundos) em momentos estratégicos:
1. Prioriza mídias manuais deixadas pelo usuário na pasta do projeto.
2. Se configurado, aciona o gflow-cli local para gerar imagens conceituais discretas.
3. Converte imagens em clipe (zoom Ken Burns opcional) e sobrepõe com dissolvência, mantendo o áudio original contínuo.
   Zoom, duração, dissolvência e sufixo estético do prompt de geração vêm do estilo (nenhum é imposto).
"""

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

def run_cmd(cmd, desc=""):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Erro em {desc or cmd[0]}: {res.stderr}")
    return res.stdout

def find_local_broll_assets(project_dir: str, exclude_path: str = None):
    """Varre a pasta do projeto procurando imagens ou vídeos que não sejam o arquivo principal."""
    valid_exts = (".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov")
    candidates = []
    
    abs_exclude = os.path.abspath(exclude_path) if exclude_path else None
    
    # Procura na raiz do projeto e em pastas como 'raw', 'assets' ou 'broll'
    search_dirs = [project_dir, os.path.join(project_dir, "raw"), os.path.join(project_dir, "assets")]
    
    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for f in os.listdir(d):
            full_path = os.path.abspath(os.path.join(d, f))
            if not os.path.isfile(full_path):
                continue
            if abs_exclude and full_path == abs_exclude:
                continue
            name_lower = f.lower()
            if any(name_lower.endswith(ext) for ext in valid_exts):
                # Ignora temporários, finais e lixeira
                if name_lower.startswith("final") or "sem_legenda" in name_lower or "com_legenda" in name_lower:
                    continue
                if name_lower.startswith(".") or "temp" in name_lower or "cache" in name_lower:
                    continue
                candidates.append(full_path)
    return candidates

def get_gflow_bin() -> str:
    """Localiza o binário do gflow no PATH ou em caminhos padrão."""
    bin_path = shutil.which("gflow")
    if bin_path:
        return bin_path
    fallback = os.path.expanduser("~/.local/bin/gflow")
    if os.path.isfile(fallback):
        return fallback
    return "gflow"

def generate_image_gflow(prompt: str, output_path: str, aspect: str = "9:16", model: str = "nano2", timeout: int = 60,
                         style_suffix: str = "") -> bool:
    """Gera uma imagem conceitual sutil via gflow-cli (gflow image t2i)."""
    gflow_bin = get_gflow_bin()
    # Estética da imagem = o que o estilo pedir (style_suffix). A skill só garante o técnico: sem texto/marca d'água.
    styled_prompt = ", ".join(p for p in (prompt, style_suffix, "no text, no watermark") if p)
    print(f"[*] Chamando gflow-cli image t2i: '{prompt}'...")
    try:
        cmd = [
            gflow_bin, "image", "t2i", styled_prompt,
            "-o", output_path,
            "--aspect", aspect,
            "--model", model
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if res.returncode == 0 and os.path.isfile(output_path):
            print(f"[+] Imagem gerada com sucesso via gflow: {output_path}")
            return True
        else:
            print(f"[-] gflow retornou status {res.returncode}: {res.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[!] Timeout na geração do gflow (>{timeout}s). Prosseguindo sem B-roll de IA.")
        return False
    except Exception as e:
        print(f"[!] Falha ao executar gflow: {e}")
        return False

def generate_video_gflow(prompt: str, output_path: str, aspect: str = "9:16", duration: int = 4, timeout: int = 90) -> bool:
    """Gera um vídeo conceitual curto via gflow-cli (gflow video t2v)."""
    gflow_bin = get_gflow_bin()
    print(f"[*] Chamando gflow-cli video t2v: '{prompt}'...")
    try:
        cmd = [
            gflow_bin, "video", "t2v", prompt,
            "-o", output_path,
            "--aspect", aspect,
            "--duration", str(duration)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout)
        if res.returncode == 0 and os.path.isfile(output_path):
            print(f"[+] Vídeo gerado com sucesso via gflow: {output_path}")
            return True
        else:
            print(f"[-] gflow retornou status {res.returncode}: {res.stderr[:200]}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[!] Timeout na geração de vídeo gflow (>{timeout}s).")
        return False
    except Exception as e:
        print(f"[!] Falha ao executar gflow video: {e}")
        return False

def image_to_kenburns_video(image_path: str, output_clip: str, duration: float = 2.5, formato: str = "vertical",
                            zoom_max: float = 1.10):
    """Transforma uma imagem estática em clipe; zoom_max=1.0 desliga o Ken Burns."""
    w, h = (1080, 1920) if formato == "vertical" else (1920, 1080)
    fps = 30
    total_frames = int(duration * fps)
    
    # zoom linear de 1.0 até zoom_max ao longo da duração (1.0 = imagem parada)
    step = max(0.0, (float(zoom_max) - 1.0) / max(total_frames, 1))
    vf = (
        f"scale=8000:-1,"
        f"zoompan=z='min(zoom+{step:.6f},{float(zoom_max):.4f})':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
        f"d={total_frames}:s={w}x{h}:fps={fps},"
        f"format=yuv420p"
    )
    
    cmd = [
        "ffmpeg", "-y", "-loop", "1", "-i", image_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        output_clip
    ]
    run_cmd(cmd, "conversão Ken Burns")

def overlay_brolls(main_video: str, brolls: list, output_video: str, formato: str = "vertical", fade_d: float = 0.20):
    """
    Sobrepõe a lista de B-rolls [(clip_path, start_time, duration)] no vídeo principal.
    Aplica dissolvência de fade_d segundos nas bordas visuais (0 = corte seco), sem alterar o áudio falado.
    """
    if not brolls:
        shutil.copy2(main_video, output_video)
        return
        
    print(f"[*] Inserindo {len(brolls)} B-roll(s) com transições suaves...")
    
    inputs = ["-i", main_video]
    filter_chains = []
    current_v = "0:v"
    
    
    for idx, (broll_path, st, dur) in enumerate(brolls, start=1):
        inputs.extend(["-i", broll_path])
        fade_out_st = max(0.0, dur - fade_d)
        
        # Filtro de fade in/out no próprio clipe de B-roll + escala + corte estrito de duração
        w, h = (1080, 1920) if formato == "vertical" else (1920, 1080)
        filter_chains.append(
            f"[{idx}:v]trim=0:{dur},setpts=PTS-STARTPTS,"
            f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
            f"format=yuva420p,"
            f"fade=t=in:st=0:d={fade_d}:alpha=1,"
            f"fade=t=out:st={fade_out_st:.3f}:d={fade_d}:alpha=1,"
            f"setpts=PTS-STARTPTS+{st}/TB[broll_{idx}];"
        )
        
        next_v = f"v_over_{idx}"
        filter_chains.append(
            f"[{current_v}][broll_{idx}]overlay=enable='between(t,{st},{st + dur})':format=auto[{next_v}];"
        )
        current_v = next_v
        
    # O áudio original [0:a] permanece 100% intocado
    filter_complex = "".join(filter_chains).rstrip(";")
    
    cmd = [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", f"[{current_v}]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "copy",
        "-shortest",
        output_video
    ]
    run_cmd(cmd, "composição de B-roll")
    print(f"[+] B-rolls compostos com sucesso: {output_video}")

def main():
    parser = argparse.ArgumentParser(description="Gerenciador e Compositor de B-Roll")
    parser.add_argument("video", help="Vídeo base")
    parser.add_argument("output", help="Vídeo final com B-Roll")
    parser.add_argument("--asset", help="Imagem ou vídeo de B-roll")
    parser.add_argument("--start", type=float, default=5.0, help="Tempo de início do B-roll (segundos)")
    parser.add_argument("--duration", type=float, default=2.5, help="Duração do B-roll")
    parser.add_argument("--formato", default="vertical", choices=["vertical", "horizontal"])
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print(f"[!] Vídeo base {args.video} não existe.")
        sys.exit(1)

    with tempfile.TemporaryDirectory() as tmpdir:
        broll_clip = args.asset
        if args.asset.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            broll_clip = os.path.join(tmpdir, "kenburns.mp4")
            image_to_kenburns_video(args.asset, broll_clip, duration=args.duration, formato=args.formato)
            
        overlay_brolls(args.video, [(broll_clip, args.start, args.duration)], args.output, formato=args.formato)

if __name__ == "__main__":
    main()
