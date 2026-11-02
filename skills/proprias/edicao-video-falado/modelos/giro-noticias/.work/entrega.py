"""Gera os arquivos de entrega em ../../final: legendas.srt, palavras.json e relatorio_cortes.json. Uso: python3 -I entrega.py"""
import json, os

W = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(W, "..", "..", "final")
os.makedirs(F, exist_ok=True)
data = json.load(open(os.path.join(W, "data.json")))
segs = json.load(open(os.path.join(W, "segs.json")))


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


srt = []
for i, c in enumerate(data["caps"], 1):
    srt.append(f"{i}\n{ts(c['t0'])} --> {ts(c['t1'])}\n{' '.join(w['x'] for w in c['w'])}\n")
open(os.path.join(F, "legendas.srt"), "w").write("\n".join(srt))
json.dump([{"text": w["w"].lstrip("*"), "start": w["t"], "end": w["e"]} for w in data["words"]],
          open(os.path.join(F, "palavras.json"), "w"), ensure_ascii=False, indent=1)
kept = []
for s in segs["segments"]:
    if kept and kept[-1]["fala"] == s["label"]:
        kept[-1]["fim_fonte"] = s["b"]; kept[-1]["fim_saida"] = round(s["out"] + s["dur"], 3)
    else:
        kept.append({"fonte": s["src"], "fala": s["label"], "inicio_fonte": s["a"], "fim_fonte": s["b"], "inicio_saida": s["out"],
                     "fim_saida": round(s["out"] + s["dur"], 3)})
rel = {   # POR EPISÓDIO: preencha com o que aconteceu nesta edição (o modelo é o relatório de cortes que acompanha o vídeo)
    "fonte": "ARQUIVO.MOV (duração, HDR/SDR, rotação). Varredura de erros de cópia (errmap.py): N quadros com erro",
    "chaves": {"a": "ARQUIVO"},
    "duracao_bruta_s": 0.0,
    "duracao_final_s": round(segs["duration"] + 2.2, 3),
    "ordem": "gancho -> notícia 1 -> notícia 2 -> ... -> pergunta + CTA",
    "layout": "sem split: apresentador em tela cheia no estúdio de LED (fundo trocado com RVM); tags e prints flutuam entre o queixo e a "
              "legenda (chin.py), a câmera sobe até 340 px por notícia e o piso escuro esconde a borda de baixo",
    "removido": [
        "sem fonte: 'trecho' (o que a matéria diz de verdade)",
        "tomadas repetidas: 'frase' (N tomadas, entrou a melhor)",
        "achado pela auditoria (audit.py, edgecheck.py, vad.py, prof5.py): ...",
        "pausas mortas e respirações: toda pausa interna acima de 0,25 s vira corte (ripple), deixando ~0,16 s entre frases",
    ],
    "revisao_visual": "quadros de cada ponto de corte conferidos: olhar pra câmera, mão no rosto, olhar pra baixo; prints nunca sobre o rosto nem sobre a legenda",
    "tratamento_audio": "respirações atenuadas em 14 dB, adeclick (estalos de boca), micro-crossfade seno de 20-25 ms em cada emenda, "
                        "fade de 0,9 s no fim, compressor 3:1 e limitador; trilha ~11 dB abaixo da voz; final em -14 LUFS / -1 dBTP",
    "mantido": kept,
}
json.dump(rel, open(os.path.join(F, "relatorio_cortes.json"), "w"), ensure_ascii=False, indent=1)
print("ok", len(srt), "legendas;", len(kept), "trechos")
