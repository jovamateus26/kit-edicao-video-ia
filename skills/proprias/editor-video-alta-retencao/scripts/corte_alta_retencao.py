#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "faster-whisper",
#     "av<14",
# ]
# ///
"""
Motor de edição de vídeo falado: corte técnico + entregáveis. Estilo-neutro.
Suporta execução em arquivo único ou em Pasta de Projeto Auto-Contida.

Toda decisão ESTÉTICA (cor, modelo/cores/caixa da legenda, B-roll, movimento, badges) vem do
estilo: flags da linha de comando ou `estilo.json` (na pasta do projeto ou via --estilo).
Sem estilo, o script só faz o técnico e não escolhe visual nenhum.

Fluxo Completo:
1. Detecção automática de mídias na pasta do projeto (Vídeo principal + B-rolls locais)
2. Isolamento de arquivos intermediários em .cache/
3. Extração e transcrição acústica (faster-whisper) com detecção milimétrica de filler words
4. Higienização: Remoção de 'éee', 'hum', gaguejos e silêncios mortos
5. Renderização do corte com micro-crossfade (+ cor, só se o estilo pedir; zero re-encode extra)
6. B-roll local (só se o estilo/flags ativarem), com parâmetros do estilo
7. Transcrição palavra a palavra do corte final (palavras.json, legendas.srt) em caixa original
8. Versão legendada com o modelo caption-* que o estilo definir (sem estilo de legenda = não renderiza)
9. Empacotamento de entregáveis em final/ com relatório e base para a copy
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

# Importa módulos auxiliares locais se disponíveis
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

try:
    from color_engine import get_color_filter
except ImportError:
    def get_color_filter(preset="none", custom_lut=None):
        return ""

try:
    from broll_engine import (
        find_local_broll_assets,
        generate_image_gflow,
        image_to_kenburns_video,
        overlay_brolls
    )
except ImportError:
    def find_local_broll_assets(d): return []
    def overlay_brolls(m, b, o, f="vertical"): shutil.copy2(m, o)

FILLER_WORDS = {
    "é", "éé", "ééé", "eee", "eh", "ehh", "hum", "humm", "hummm", 
    "hm", "hmm", "ãh", "ãã", "ã", "ah", "ahh", "hã", "hãm", "uh", "uhm", 
    "ooo", "óó", "ham", "er", "err"
}

def clean_word(token: str) -> str:
    return re.sub(r"[^\wáéíóúâêîôûãõç]", "", token.lower())

def run_cmd(cmd, desc=""):
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Erro ao executar {desc or cmd[0]}: {res.stderr}")
    return res.stdout

def get_video_duration(video_path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", video_path
    ]
    out = run_cmd(cmd, "ffprobe duration").strip()
    return float(out)

def extract_audio(video_path: str, output_wav: str):
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        output_wav
    ]
    run_cmd(cmd, "extração de áudio")

def get_whisper_model(model_size="small", device="auto"):
    from faster_whisper import WhisperModel
    if device == "auto":
        try:
            import ctypes
            ctypes.CDLL("libcublas.so.12")
            device = "cuda"
        except Exception:
            device = "cpu"
    print(f"[*] Inicializando Whisper ({model_size}) no dispositivo: {device.upper()}...")
    compute_type = "float16" if device == "cuda" else "int8"
    return WhisperModel(model_size, device=device, compute_type=compute_type)

def transcribe_and_detect_fillers(audio_path: str, model_size="small", device="auto"):
    model = get_whisper_model(model_size, device=device)
    print(f"[*] Transcrevendo áudio com timestamps por palavra e detecção de hesitações...")
    
    prompt = "Transcreva tudo exatamente incluindo hesitações, pausas e interjeições como é, hum, ah, ãh, né, tipo."
    segments, _ = model.transcribe(
        audio_path,
        language="pt",
        word_timestamps=True,
        initial_prompt=prompt,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=250)
    )
    
    words = []
    full_text_list = []
    raw_segments = []
    for segment in segments:
        s_text = segment.text.strip()
        full_text_list.append(s_text)
        raw_segments.append({
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "text": s_text
        })
        for w in segment.words:
            w_text = w.word.strip()
            if not w_text:
                continue
            words.append({
                "word": w_text,
                "clean": clean_word(w_text),
                "start": round(w.start, 3),
                "end": round(w.end, 3),
                "duration": round(w.end - w.start, 3),
                "probability": round(w.probability, 3)
            })
    return words, " ".join(full_text_list), raw_segments

def filter_words_and_build_cuts(words, total_duration, raw_segments=None, min_silence=0.35, pad_start=0.06, pad_end=0.08, max_phrase_rep=5, rep_gap=3.0):
    discarded_indices = set()
    reasons = {}
    n = len(words)
    
    # 0. Curadoria Semântica (Poda de Retakes e Frases Incompletas/Dangling)
    if raw_segments:
        try:
            from semantic_curator import curate_speech
            sem_disc, sem_reasons = curate_speech(words, raw_segments)
            discarded_indices.update(sem_disc)
            reasons.update(sem_reasons)
            print(f"[*] Curadoria Semântica: {len(sem_disc)} palavras de retakes/orações quebradas podadas.")
        except Exception as e:
            print(f"[!] Aviso na curadoria semântica: {e}")
            
    # 1. Checagem de Filler Sounds explícitos
    for i in range(n):
        if i in discarded_indices:
            continue
        curr = words[i]
        c = curr["clean"]
        if c in FILLER_WORDS:
            if c == "é":
                has_prev_gap = (i > 0 and (curr["start"] - words[i-1]["end"]) > 0.25)
                has_next_gap = (i < n - 1 and (words[i+1]["start"] - curr["end"]) > 0.25)
                if curr["duration"] >= 0.35 or (has_prev_gap and has_next_gap):
                    discarded_indices.add(i)
                    reasons[i] = "hesitação vocal alongada ('é...')"
            else:
                discarded_indices.add(i)
                reasons[i] = f"filler sound ('{curr['word']}')"

    # 2. Motor Avançado N-Gram: Detecção de Falsos Inícios e Repetições (Frases de 5 até 1 palavras)
    # Detecta padrões como "então bora lá... então bora lá" ou "então... então... então"
    for k in range(max_phrase_rep, 0, -1):
        i = 0
        while i < n:
            if i in discarded_indices:
                i += 1
                continue
                
            # Coleta k palavras válidas a partir de i
            chunk_a_indices = []
            curr_idx = i
            while curr_idx < n and len(chunk_a_indices) < k:
                if curr_idx not in discarded_indices:
                    chunk_a_indices.append(curr_idx)
                curr_idx += 1
                
            if len(chunk_a_indices) < k:
                i += 1
                continue
                
            # Coleta as próximas k palavras válidas após chunk_a
            chunk_b_indices = []
            while curr_idx < n and len(chunk_b_indices) < k:
                if curr_idx not in discarded_indices:
                    chunk_b_indices.append(curr_idx)
                curr_idx += 1
                
            if len(chunk_b_indices) < k:
                i += 1
                continue
                
            chunk_a_clean = [words[idx]["clean"] for idx in chunk_a_indices]
            chunk_b_clean = [words[idx]["clean"] for idx in chunk_b_indices]
            
            # Se as frases ou palavras forem idênticas
            if chunk_a_clean == chunk_b_clean:
                first_b_start = words[chunk_b_indices[0]]["start"]
                last_a_end = words[chunk_a_indices[-1]]["end"]
                gap = first_b_start - last_a_end
                
                # Se o intervalo entre os dois blocos for menor que rep_gap (tempo típico de recomeçar a fala)
                if gap <= rep_gap:
                    phrase_str = " ".join([words[idx]["word"] for idx in chunk_a_indices])
                    for idx in chunk_a_indices:
                        discarded_indices.add(idx)
                        reasons[idx] = f"repetição / falso início ({k} palavra(s): '{phrase_str}')"
                    # Repete sem avançar i para capturar repetições triplas (ex: A, A, A -> descarta os dois primeiros)
                    continue
            i += 1

    discarded = []
    valid_words = []
    for idx, w in enumerate(words):
        if idx in discarded_indices:
            discarded.append({**w, "reason": reasons.get(idx, "hesitação")})
        else:
            valid_words.append(w)

    print(f"[*] Total de palavras detectadas: {len(words)}")
    print(f"[*] Filler words & repetições identificadas para remoção: {len(discarded)}")
    
    if not valid_words:
        return [(0.0, total_duration)], discarded
        
    raw_segments = []
    for w in valid_words:
        s = max(0.0, w["start"] - pad_start)
        e = min(total_duration, w["end"] + pad_end)
        raw_segments.append((s, e))
        
    merged_segments = []
    cur_s, cur_e = raw_segments[0]
    for next_s, next_e in raw_segments[1:]:
        if next_s <= cur_e + min_silence:
            cur_e = max(cur_e, next_e)
        else:
            merged_segments.append((round(cur_s, 3), round(cur_e, 3)))
            cur_s, cur_e = next_s, next_e
    merged_segments.append((round(cur_s, 3), round(cur_e, 3)))
    
    return merged_segments, discarded

def render_cut_video(input_path, segments, output_path, formato="vertical", crf=20, color_preset="none", custom_lut=None):
    print(f"[*] Renderizando corte com micro-crossfade em {len(segments)} trechos...")
    
    scale_filter = (
        "crop=trunc(ih*9/16/2)*2:ih:(iw-ow)/2:0,scale=1080:1920"
        if formato == "vertical"
        else "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2"
    )
    
    # Adiciona tratamento de cor diretamente no grafo de filtros (zero re-encode extra)
    color_filter = get_color_filter(color_preset, custom_lut)
    final_v_filters = scale_filter
    if color_filter:
        print(f"[*] Integrando normalização de cor '{color_preset}' no pipeline...")
        final_v_filters += f",{color_filter}"
    
    filter_lines = []
    concat_inputs = []
    fade_d = 0.008  # 8ms micro-fade
    
    for i, (s, e) in enumerate(segments):
        dur = max(0.02, e - s)
        actual_fade = min(fade_d, dur / 3)
        fade_out_start = max(0.0, dur - actual_fade)
        
        filter_lines.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}];")
        filter_lines.append(
            f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS,"
            f"afade=t=in:ss=0:d={actual_fade:.4f},"
            f"afade=t=out:st={fade_out_start:.4f}:d={actual_fade:.4f}[a{i}];"
        )
        concat_inputs.append(f"[v{i}][a{i}]")
        
    filter_lines.append(
        f"{''.join(concat_inputs)}concat=n={len(segments)}:v=1:a=1[concat_v][out_a];"
    )
    filter_lines.append(f"[concat_v]{final_v_filters}[out_v]")
    
    filter_script_content = "\n".join(filter_lines)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as script_file:
        script_file.write(filter_script_content)
        script_path = script_file.name
        
    try:
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-filter_complex_script", script_path,
            "-map", "[out_v]", "-map", "[out_a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
            "-c:a", "aac", "-b:a", "192k",
            output_path
        ]
        run_cmd(cmd, "renderização do vídeo sem legenda")
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)

def to_srt_time(sec):
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    msecs = int(round((sec - int(sec)) * 1000))
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msecs:03d}"

def to_ass_time(sec):
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    csecs = int(round((sec - int(sec)) * 100))
    if csecs >= 100:
        csecs = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{csecs:02d}"

def generate_verbatim_subtitles(video_sem_legenda, output_srt, output_ass, model_size="small", formato="vertical", device="auto",
                                ass_style=None, group=None):
    print("[*] Transcrevendo o corte final palavra a palavra...")
    
    temp_wav = video_sem_legenda + ".tmp_sub.wav"
    extract_audio(video_sem_legenda, temp_wav)
    
    try:
        model = get_whisper_model(model_size, device=device)
        segments, _ = model.transcribe(
            temp_wav,
            language="pt",
            word_timestamps=True,
            vad_filter=True,
            condition_on_previous_text=False,
            no_speech_threshold=0.6,
            initial_prompt=None
        )
        
        all_words = []
        for segment in segments:
            for w in segment.words:
                cleaned = w.word.strip()
                if cleaned:
                    all_words.append({
                        "text": cleaned,  # caixa original; upper/lower é decisão do estilo
                        "start": w.start,
                        "end": w.end
                    })
                    
        # palavras com tempo (formato transcript.json do HyperFrames) para os modelos caption-* do HyperFrames
        words_json = os.path.join(os.path.dirname(output_srt), "palavras.json")
        with open(words_json, "w", encoding="utf-8") as f:
            json.dump([{"text": w["text"], "start": round(w["start"], 3), "end": round(w["end"], 3)} for w in all_words],
                      f, ensure_ascii=False, indent=1)
        print(f"[*] Palavras com tempo (HyperFrames) salvas em: {words_json}")

        g = {"max_words": 3, "max_chars": 20, "pause": 0.35, **(group or {})}
        chunks = []
        current_chunk = []
        current_char_count = 0
        
        for i, w in enumerate(all_words):
            word_len = len(w["text"])
            has_pause = (current_chunk and (w["start"] - current_chunk[-1]["end"]) > g["pause"])
            reached_limit = (len(current_chunk) >= g["max_words"] or (current_char_count + word_len > g["max_chars"]))
            
            if current_chunk and (has_pause or reached_limit):
                chunks.append(current_chunk)
                current_chunk = [w]
                current_char_count = word_len
            else:
                current_chunk.append(w)
                current_char_count += word_len + 1
                
        if current_chunk:
            chunks.append(current_chunk)
            
        srt_lines = []
        for idx, chunk in enumerate(chunks, start=1):
            s_time = to_srt_time(chunk[0]["start"])
            e_time = to_srt_time(chunk[-1]["end"])
            text = " ".join([item["text"] for item in chunk])
            srt_lines.append(f"{idx}\n{s_time} --> {e_time}\n{text}\n")
            
        with open(output_srt, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines) + "\n")
            
        st = {"font": "Arial", "size": 46 if formato == "vertical" else 28, "primary": "&H00FFFFFF",
              "active": None, "outline": 3.0, "shadow": 0, "bold": 0, "case": "original",
              "margin_v": 300 if formato == "vertical" else 90, **(ass_style or {})}
        margin_v, font_size = st["margin_v"], st["size"]
        fmt = (lambda t: t.upper()) if st["case"] == "upper" else (lambda t: t.lower()) if st["case"] == "lower" else (lambda t: t)
        hi = (lambda t: r"{\c" + st["active"] + "&}" + t + r"{\c" + st["primary"] + "&}") if st["active"] else (lambda t: t)
        play_x = 1080 if formato == "vertical" else 1920
        play_y = 1920 if formato == "vertical" else 1080
        
        ass_header = f"""[Script Info]
Title: Legendas (fallback ASS)
ScriptType: v4.00+
PlayResX: {play_x}
PlayResY: {play_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Base,{st["font"]},{font_size},{st["primary"]},{st["primary"]},&H00000000,&H80000000,{-1 if st["bold"] else 0},0,0,0,100,100,0,0,1,{st["outline"]},{st["shadow"]},2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, Effect, Text
"""
        ass_dialogues = []
        for chunk in chunks:
            if len(chunk) == 1:
                s_time = to_ass_time(chunk[0]["start"])
                e_time = to_ass_time(chunk[0]["end"])
                text = hi(fmt(chunk[0]["text"]))
                ass_dialogues.append(f"Dialogue: 0,{s_time},{e_time},Base,,0,0,,{text}")
            else:
                for cur_idx, cur_w in enumerate(chunk):
                    w_start = to_ass_time(cur_w["start"])
                    w_end = to_ass_time(cur_w["end"])
                    styled_words = []
                    for j, w in enumerate(chunk):
                        txt = fmt(w["text"])
                        if j == cur_idx:
                            styled_words.append(hi(txt))
                        else:
                            styled_words.append(txt)
                    dialogue_text = " ".join(styled_words)
                    ass_dialogues.append(f"Dialogue: 0,{w_start},{w_end},Base,,0,0,,{dialogue_text}")
            
        with open(output_ass, "w", encoding="utf-8") as f:
            f.write(ass_header + "\n".join(ass_dialogues) + "\n")
            
        print(f"[*] Legenda SRT salva em: {output_srt}")
        print(f"[*] Legenda ASS (fallback) salva em: {output_ass}")
    finally:
        if os.path.exists(temp_wav):
            os.remove(temp_wav)

def burn_subtitles(video_sem_legenda, ass_path, srt_path, output_com_legenda, formato="vertical", crf=20):
    print("[*] Queimando legenda ASS (fallback)...")
    margin_v = 300 if formato == "vertical" else 90
    font_size = 46 if formato == "vertical" else 28
    
    if os.path.isfile(ass_path):
        escaped_path = os.path.abspath(ass_path).replace(":", "\\:").replace("'", "\\'")
        vf_arg = f"ass='{escaped_path}'"
    else:
        escaped_path = os.path.abspath(srt_path).replace(":", "\\:").replace("'", "\\'")
        style = f"FontSize={font_size},FontName=Arial,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=3,Shadow=0,Alignment=2,MarginV={margin_v}"
        vf_arg = f"subtitles='{escaped_path}':force_style='{style}'"
        
    cmd = [
        "ffmpeg", "-y", "-i", video_sem_legenda,
        "-vf", vf_arg,
        "-c:v", "libx264", "-preset", "fast", "-crf", str(crf),
        "-c:a", "copy",
        output_com_legenda
    ]
    run_cmd(cmd, "queima de legendas")

def render_hyperframes_captions(video_sem_legenda, words_json, output_com_legenda, final_dir, model, estilo=None):
    """Legenda com o modelo caption-* que o estilo definir. Retorna True se renderizou."""
    import glob as _glob
    kit = os.path.join(os.path.dirname(SCRIPT_DIR), "badges", "badge_kit.py")
    proj = os.path.join(final_dir, "hyperframes")
    node_bins = sorted(_glob.glob(os.path.expanduser("~/.nvm/versions/node/v2[2-9]*/bin")), reverse=True)
    env = dict(os.environ)
    if node_bins:
        env["PATH"] = node_bins[0] + os.pathsep + env.get("PATH", "")
    try:
        print(f"[*] Legendas HyperFrames ({model}): preparando projeto em {proj}")
        run_cmd([sys.executable, kit, "init", "--project", proj, "--video", video_sem_legenda], "badge_kit init")
        dur = get_video_duration(os.path.join(proj, "public", "input-video.mp4"))
        spec_path = os.path.join(proj, "spec.json")
        if not os.path.exists(spec_path):
            leg = dict((estilo or {}).get("legenda") or {})
            cap = {"model": model, "words": os.path.abspath(words_json), "keywords": leg.get("keywords", [])}
            for k in ("vars", "case", "group", "scale", "baseline_y", "max_text_px", "css"):
                if k in leg:
                    cap[k] = leg[k]
            spec = {"_sobre": "Spec do badge_kit. Adicione badges em 'badges' e rode build/auto; a legenda já está configurada.",
                    "video": "input-video.mp4", "duration": round(dur, 3), "fps": 30, "width": 1080, "height": 1920,
                    "estilo": {k: v for k, v in (estilo or {}).items() if k in ("badges", "motion")},
                    "badges": [], "captions": cap}
            with open(spec_path, "w", encoding="utf-8") as f:
                json.dump(spec, f, ensure_ascii=False, indent=2)
        run_cmd([sys.executable, kit, "build", spec_path, "--project", proj], "badge_kit build")
        out = os.path.join(proj, "output.mp4")
        res = subprocess.run(["npx", "hyperframes", "render", os.path.join(proj, "public"), "-o", out, "--fps", "30"],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
        if res.returncode != 0 or not os.path.exists(out):
            print("[!] Render HyperFrames falhou:\n" + res.stdout[-1500:])
            return False
        shutil.copy2(out, output_com_legenda)
        print(f"[+] Legenda HyperFrames renderizada: {output_com_legenda}")
        return True
    except Exception as e:
        print(f"[!] Legendas HyperFrames indisponíveis ({e}).")
        return False

def generate_publication_copy(transcribed_text: str, output_md_path: str):
    """Base neutra para a copy: palavras-chave + transcrição. Títulos, tom e hashtags são escritos
    pelo agente conforme o prompt (a skill não impõe tom nem fórmula de CTR)."""
    words = re.findall(r"\b[a-zA-ZáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ]{4,}\b", transcribed_text.lower())
    common_stops = {"para", "como", "mais", "esse", "essa", "este", "esta", "isso", "pelo", "pela", "qual", "fazer", "pode", "vamos", "aqui", "então"}
    keywords = list(dict.fromkeys(w for w in words if w not in common_stops))[:12]
    content = f"""# Base para publicação

> Material de apoio. Títulos, texto de capa, descrição e hashtags: escrever no tom definido no prompt.

## Palavras-chave detectadas
{", ".join(keywords) if keywords else "(nenhuma)"}

## Transcrição do corte final
{transcribed_text.strip()}
"""
    with open(output_md_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"[+] Base de publicação salva em: {output_md_path}")

def resolve_target(target_path: str):
    """Resolve se o target é um diretório de projeto ou arquivo único de vídeo."""
    if os.path.isdir(target_path):
        project_dir = os.path.abspath(target_path)
        cache_dir = os.path.join(project_dir, ".cache")
        final_dir = os.path.join(project_dir, "final")
        
        # Encontra o vídeo principal (maior vídeo ou arquivo na pasta que não seja broll)
        video_exts = (".mp4", ".mov", ".mkv", ".webm")
        candidates = []
        for root, dirs, files in os.walk(project_dir):
            if ".cache" in root or "final" in root:
                continue
            for f in files:
                if any(f.lower().endswith(ext) for ext in video_exts):
                    full = os.path.join(root, f)
                    candidates.append((full, os.path.getsize(full)))
                    
        if not candidates:
            raise FileNotFoundError(f"Nenhum arquivo de vídeo encontrado na pasta: {target_path}")
            
        # O maior arquivo costuma ser a gravação principal
        candidates.sort(key=lambda x: x[1], reverse=True)
        main_video = candidates[0][0]
        return main_video, project_dir, cache_dir, final_dir
    else:
        main_video = os.path.abspath(target_path)
        project_dir = os.path.dirname(main_video)
        cache_dir = os.path.join(project_dir, ".cache")
        final_dir = os.path.join(project_dir, "final")
        return main_video, project_dir, cache_dir, final_dir

def main():
    parser = argparse.ArgumentParser(description="Edição de vídeo falado: corte técnico + entregáveis (estilo vem do prompt/estilo.json)")
    parser.add_argument("target", help="Caminho do arquivo de vídeo OU pasta temática do projeto")
    parser.add_argument("--formato", choices=["vertical", "horizontal"], default="vertical", help="Formato do vídeo final")
    parser.add_argument("--estilo", default=None, help="estilo.json com as decisões estéticas (padrão: <projeto>/estilo.json, se existir)")
    parser.add_argument("--color", choices=["studio", "vibrant", "cinematic", "warm", "none"], default=None, help="Preset de cor (sem estilo: none)")
    parser.add_argument("--lut", default=None, help="Caminho para arquivo .cube LUT opcional")
    parser.add_argument("--broll", choices=["auto", "manual", "none"], default=None, help="B-roll (sem estilo: none). manual = só mídias locais")
    parser.add_argument("--model", default="small", help="Modelo Whisper (tiny, base, small, medium)")
    parser.add_argument("--min-silence", type=float, default=0.35, help="Duração mínima do silêncio para corte (segundos)")
    parser.add_argument("--crf", type=int, default=20, help="Qualidade CRF do vídeo (18-23)")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto", help="Dispositivo de execução Whisper")
    parser.add_argument("--plan", default=None, help="Caminho para arquivo JSON de plano editorial com intervalos autorizados")
    parser.add_argument("--keep-cache", action="store_true", help="Preserva arquivos temporários em .cache/")
    parser.add_argument("--legenda", choices=["hyperframes", "ass", "none"], default="hyperframes",
                        help="hyperframes = modelo caption-* do HyperFrames; ass = fallback ASS; none = sem versão legendada")
    parser.add_argument("--legenda-modelo", default=None, help="Modelo caption-* (sobrescreve estilo.legenda.modelo). Sem modelo, não legenda")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.target):
        print(f"[!] Erro: Alvo '{args.target}' não existe.")
        sys.exit(1)
        
    main_video, project_dir, cache_dir, final_dir = resolve_target(args.target)
    estilo_path = args.estilo or os.path.join(project_dir, "estilo.json")
    estilo = {}
    if os.path.isfile(estilo_path):
        with open(estilo_path, encoding="utf-8") as ef:
            estilo = json.load(ef)
        print(f"[*] Estilo: {estilo_path}")
    elif args.estilo:
        print(f"[!] Estilo '{args.estilo}' não encontrado."); sys.exit(1)
    # flags > estilo.json > neutro
    args.color = args.color or estilo.get("cor", {}).get("preset") or "none"
    args.lut = args.lut or estilo.get("cor", {}).get("lut")
    broll_cfg = estilo.get("broll", {})
    args.broll = args.broll or broll_cfg.get("modo") or "none"
    leg_cfg = estilo.get("legenda", {})
    args.legenda_modelo = args.legenda_modelo or leg_cfg.get("modelo")
    os.makedirs(cache_dir, exist_ok=True)
    os.makedirs(final_dir, exist_ok=True)
    
    print("=" * 60)
    print(f"[*] Projeto: {os.path.basename(project_dir)}")
    print(f"[*] Vídeo Principal: {os.path.basename(main_video)}")
    print(f"[*] Pasta Temporária (.cache): {cache_dir}")
    print(f"[*] Pasta Final de Entregáveis: {final_dir}")
    print("=" * 60)
    
    final_sem_legenda = os.path.join(final_dir, "final_sem_legenda.mp4")
    final_com_legenda = os.path.join(final_dir, "final_com_legenda.mp4")
    legendas_srt = os.path.join(final_dir, "legendas.srt")
    legendas_ass = os.path.join(final_dir, "legendas.ass")
    relatorio_json = os.path.join(final_dir, "relatorio_cortes.json")
    copy_md = os.path.join(final_dir, "publicacao_copy.md")
    
    dur_original = get_video_duration(main_video)
    print(f"[*] Duração original: {dur_original:.2f}s")
    
    temp_audio = os.path.join(cache_dir, "input_mono.wav")
    extract_audio(main_video, temp_audio)
    
    words, full_text, raw_segments = transcribe_and_detect_fillers(temp_audio, model_size=args.model, device=args.device)
    
    # Aplicação de Plano Editorial de Curadoria (se houver)
    plan_file = args.plan
    if not plan_file and os.path.isfile(os.path.join(project_dir, "plano_editorial.json")):
        plan_file = os.path.join(project_dir, "plano_editorial.json")
        
    if plan_file and os.path.isfile(plan_file):
        print(f"[*] Aplicando Plano Editorial de Curadoria: {plan_file}")
        with open(plan_file, "r", encoding="utf-8") as pf:
            plan_data = json.load(pf)
        allowed_intervals = []
        for item in plan_data:
            if isinstance(item, dict):
                allowed_intervals.append((float(item["start"]), float(item["end"])))
            elif isinstance(item, (list, tuple)):
                allowed_intervals.append((float(item[0]), float(item[1])))
                
        words = [w for w in words if any(s <= w["start"] and w["end"] <= e for s, e in allowed_intervals)]
        print(f"[*] Palavras selecionadas pelo plano editorial: {len(words)}")
        
    segments, discarded = filter_words_and_build_cuts(
        words, dur_original, raw_segments=raw_segments, min_silence=args.min_silence
    )
    
    # 1. Renderiza corte higienizado + Normalização de Cor
    render_cut_video(
        main_video, segments, final_sem_legenda,
        formato=args.formato, crf=args.crf,
        color_preset=args.color, custom_lut=args.lut
    )
    
    # 2. Tratamento de B-Roll se ativado
    if args.broll != "none":
        local_assets = find_local_broll_assets(project_dir, exclude_path=main_video)
        # Se encontrou assets locais manuais, compõe o primeiro
        if local_assets:
            chosen = local_assets[0]
            print(f"[+] Asset manual de B-roll detectado: {chosen}")
            broll_video = os.path.join(cache_dir, "broll_clip.mp4")
            if chosen.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                image_to_kenburns_video(chosen, broll_video, duration=float(broll_cfg.get("duracao", 2.5)), formato=args.formato,
                                        zoom_max=float(broll_cfg.get("zoom_max", 1.0)))
            else:
                broll_video = chosen
            
            # Insere em ~1/3 do vídeo cortado
            dur_cut = get_video_duration(final_sem_legenda)
            target_st = max(3.0, dur_cut * 0.35)
            temp_brolled = os.path.join(cache_dir, "with_broll.mp4")
            overlay_brolls(final_sem_legenda, [(broll_video, target_st, float(broll_cfg.get("duracao", 2.5)))], temp_brolled,
                           formato=args.formato, fade_d=float(broll_cfg.get("dissolve", 0.2)))
            shutil.move(temp_brolled, final_sem_legenda)
            
    dur_final = get_video_duration(final_sem_legenda)
    tempo_economizado = dur_original - dur_final
    pct_economizado = (tempo_economizado / dur_original) * 100 if dur_original > 0 else 0
    
    # 3. Transcrição + versão legendada (só com estilo de legenda definido)
    generate_verbatim_subtitles(final_sem_legenda, legendas_srt, legendas_ass, model_size=args.model, formato=args.formato,
                                device=args.device, ass_style=leg_cfg.get("ass"), group=leg_cfg.get("group"))
    if args.legenda == "hyperframes" and not args.legenda_modelo:
        print("[i] Estilo de legenda não definido (estilo.legenda.modelo / --legenda-modelo): versão legendada não renderizada.")
        print("    palavras.json e legendas.srt estão prontos; defina o modelo e rode o badge_kit (ver SKILL.md).")
        final_com_legenda = None
    elif args.legenda == "hyperframes":
        ok = render_hyperframes_captions(final_sem_legenda, os.path.join(final_dir, "palavras.json"), final_com_legenda,
                                         final_dir, model=args.legenda_modelo, estilo=estilo)
        if not ok:
            print("[!] Usando fallback: karaokê ASS queimado com ffmpeg.")
            burn_subtitles(final_sem_legenda, legendas_ass, legendas_srt, final_com_legenda, formato=args.formato, crf=args.crf)
    elif args.legenda == "ass":
        burn_subtitles(final_sem_legenda, legendas_ass, legendas_srt, final_com_legenda, formato=args.formato, crf=args.crf)
    else:
        final_com_legenda = None

    # 4. Copy e Estratégia de Postagem
    generate_publication_copy(full_text, copy_md)
    
    # 5. Relatório Técnico
    relatorio = {
        "projeto": os.path.basename(project_dir),
        "arquivo_origem": main_video,
        "formato": args.formato,
        "preset_cor": args.color,
        "estilo": estilo_path if estilo else None,
        "legenda_modelo": args.legenda_modelo,
        "duracao_original_segundos": round(dur_original, 2),
        "duracao_final_segundos": round(dur_final, 2),
        "tempo_economizado_segundos": round(tempo_economizado, 2),
        "percentual_retencao_otimizado": f"{pct_economizado:.1f}%",
        "total_trechos_preservados": len(segments),
        "total_fillers_removidos": len(discarded),
        "detalhes_fillers_removidos": discarded,
        "arquivos_entregues": [
            final_sem_legenda,
            *([final_com_legenda] if final_com_legenda else []),
            legendas_srt,
            legendas_ass,
            copy_md
        ]
    }
    
    with open(relatorio_json, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, ensure_ascii=False, indent=2)
        
    # Limpeza da pasta .cache se não solicitada a preservação
    if not args.keep_cache and os.path.exists(cache_dir):
        shutil.rmtree(cache_dir, ignore_errors=True)
        print("[*] Cache temporário limpo.")
        
    print("\n" + "=" * 60)
    print("           EDIÇÃO CONCLUÍDA COM SUCESSO!           ")
    print("=" * 60)
    print(f"[-] Duração Original: {dur_original:.2f}s")
    print(f"[+] Duração Otimizada: {dur_final:.2f}s ({tempo_economizado:.2f}s cortados | {pct_economizado:.1f}% mais dinâmico)")
    print(f"[+] Filler Words & Hesitações Cortadas: {len(discarded)}")
    print(f"[+] Cor Aplicada: Preset '{args.color}'")
    print(f"[+] Pasta Final: {final_dir}")
    print(f"    - final_sem_legenda.mp4")
    if final_com_legenda:
        print(f"    - final_com_legenda.mp4 ({args.legenda_modelo or 'ass'})")
    print(f"    - palavras.json, legendas.srt & legendas.ass")
    print(f"    - publicacao_copy.md (base para a copy)")
    print("=" * 60)

if __name__ == "__main__":
    main()
