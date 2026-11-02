"""Gera a trilha (MusicGen small, CPU): um clipe-semente (TOK/50 s; o MusicGen small aceita no máximo ~2000 tokens = 40 s) -> music/seed.wav
uv run --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple --with torch --with transformers --with soundfile --with numpy python -I music/gen.py "<prompt>" seed
"""
import os, sys
import numpy as np, soundfile as sf, torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration

W = os.path.dirname(os.path.abspath(__file__))
prompt, name = sys.argv[1], sys.argv[2]
torch.manual_seed(int(sys.argv[3]) if len(sys.argv) > 3 else 7)
proc = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
inp = proc(text=[prompt], padding=True, return_tensors="pt")
with torch.no_grad():
    audio = model.generate(**inp, do_sample=True, guidance_scale=3.5, max_new_tokens=int(os.environ.get("TOK", "1500")))  # 50 tokens/s
sr = model.config.audio_encoder.sampling_rate
sf.write(os.path.join(W, name + ".wav"), audio[0, 0].numpy().astype(np.float32), sr)
print("ok", name, audio.shape[-1] / sr, "s")
