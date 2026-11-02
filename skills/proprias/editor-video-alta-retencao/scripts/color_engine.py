#!/usr/bin/env python3
"""
Módulo de Normalização e Tratamento de Cor / Imagem (Color Engine).
Catálogo de presets de cor (contraste, saturação, nitidez, curva). Nenhum é padrão:
sem escolha explícita do estilo/prompt o pipeline usa "none" (imagem original).
"""

import argparse
import subprocess
import sys
import os

PRESETS = {
    "studio": (
        "eq=contrast=1.06:brightness=0.01:saturation=1.06,"
        "unsharp=5:5:0.5:5:5:0.0"
    ),
    "vibrant": (
        "eq=contrast=1.08:brightness=0.02:saturation=1.12,"
        "unsharp=5:5:0.6:5:5:0.0"
    ),
    "cinematic": (
        "eq=contrast=1.10:brightness=-0.01:saturation=0.98,"
        "curves=all='0/0 0.25/0.20 0.75/0.80 1/1',"
        "unsharp=5:5:0.5:5:5:0.0"
    ),
    "warm": (
        "eq=contrast=1.05:brightness=0.01:saturation=1.08,"
        "colorbalance=rs=0.04:gs=0.01:bs=-0.04,"
        "unsharp=5:5:0.5:5:5:0.0"
    ),
    "none": ""
}

def get_color_filter(preset: str = "none", custom_lut: str = None) -> str:
    """Retorna a string de filtro FFmpeg para o preset ou LUT selecionado."""
    if custom_lut and os.path.isfile(custom_lut):
        lut_path = os.path.abspath(custom_lut).replace(":", "\\:").replace("'", "\\'")
        return f"lut3d='{lut_path}'"
    if (preset or "none").lower() not in PRESETS:
        raise ValueError(f"Preset de cor desconhecido: {preset}. Opções: {', '.join(PRESETS)}")
    return PRESETS[(preset or "none").lower()]

def apply_color_grading(input_path: str, output_path: str, preset: str = "none", custom_lut: str = None, crf: int = 20):
    color_filter = get_color_filter(preset, custom_lut)
    if not color_filter:
        # Se for 'none', apenas copia
        cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", output_path]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-vf", color_filter,
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-c:a", "copy",
            output_path
        ]
    
    print(f"[*] Aplicando tratamento de cor (Preset: {preset})...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Erro ao aplicar cor: {res.stderr}")
    print(f"[+] Tratamento de cor concluído: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Tratamento e Normalização de Cor para Vídeos")
    parser.add_argument("input", help="Vídeo de entrada")
    parser.add_argument("output", help="Vídeo de saída")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), default="none", help="Preset de cor (none = original)")
    parser.add_argument("--lut", default=None, help="Caminho para arquivo .cube LUT opcional")
    parser.add_argument("--crf", type=int, default=20, help="Qualidade CRF")
    args = parser.parse_args()

    apply_color_grading(args.input, args.output, preset=args.preset, custom_lut=args.lut, crf=args.crf)

if __name__ == "__main__":
    main()
