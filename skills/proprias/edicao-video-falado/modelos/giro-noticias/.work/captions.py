"""Legenda revisada (pt-BR) alinhada às palavras do whisper na fala editada -> data.json

Entrada: transcript_edit.json (_pipeline/wh edit sobre segs/cat.wav). O texto revisado abaixo é a fonte da verdade;
os tempos vêm do whisper por alinhamento de sequência (difflib). Palavra-chave em amarelo: prefixo '*'. Legenda em caixa alta (CSS), 2-3 palavras por bloco.
Uso: python3 -I captions.py

TEXT e FIX abaixo são do EXEMPLO (giro com 5 notícias): troque pela fala revisada do seu vídeo e pelas suas correções.
"""
import difflib, json, os, re, unicodedata

W = os.path.dirname(os.path.abspath(__file__))
TEXT = """
A *Binance | sofreu | um *ataque | *hacker | *bilionário. |
A maior | *corretora | de *cripto | do mundo | *esvaziou | a *carteira | após uma | *invasão | em *servidores | e *suspendeu | todos os | *saques | às *pressas. |
Eles | *prometem | *cobrir | todo o | *rombo, | mas as | *perdas | estimadas | já *assustam | o *mercado. |
E acabou | a *busca | *limpa. |
O *Google | confirmou | que as | *respostas | por *inteligência | *artificial | da pesquisa | vão ter | *anúncios | *patrocinados | no *Brasil | até *dezembro. |
Os *produtos | *pagos | vão aparecer | *misturados | no meio | do *resumo | da *IA. |
E o *Gemini | liberou | uma | *atualização | que vai | *salvar | seu | *expediente. |
Agora pra | *abrir, | *visualizar, | *editar | *PDFs, | *planilhas, | *documentos | inteiros, | direto | na *janela | da *conversa | da IA, | sem precisar | *baixar | ou *instalar | nenhum | *programa. |
E seu | *chip | de celular | da *TIM? | *Atenção, | a nova | *controladora | *italiana | avisou | que a | *operação | *brasileira | não é | *estratégica, | o que | pode *mexer | com mais de | *60 | *milhões | de *linhas | telefônicas | aqui no | *Brasil. |
E a | *General | *Motors | levou | uma *multa | *pesada | de *220 | *milhões | de *dólares | por *espionar | *motoristas | através | do *carro | e *vender | *históricos | de *aceleração | e *freadas | para as | *seguradoras, | aumentando | o *preço | da *apólice | sem *consentimento. |
Qual é essa | *notícia | que te pegou | mais de | *surpresa? |
*Comenta | aí e | *compartilha | pra tua | *galera | ficar | *ligada | também. |
"""


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]", "", s)


raw_toks = TEXT.split()
BREAK = set()  # '|' força quebra de grupo antes da próxima palavra
toks = []
for t in raw_toks:
    if t == "|":
        BREAK.add(len(toks))
    else:
        toks.append(t)
TR = json.load(open(os.path.join(W, "transcript_edit.json")))   # wh edit: lista de palavras {w, s, e, p, src}
ws = [w for seg in TR for w in seg["words"]] if TR and "words" in TR[0] else TR
# whisper escreve "70%" como "70" "%": junta símbolos soltos na palavra anterior
wl = []
for w in ws:
    if wl and norm(w["w"]) == "" and w["w"].strip():
        wl[-1]["e"] = w["e"]
        continue
    wl.append(dict(w))
A = [norm(t) for t in toks]
B = [norm(w["w"]) for w in wl]
times = [None] * len(toks)
sm = difflib.SequenceMatcher(a=A, b=B, autojunk=False)
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == "equal" or (tag == "replace" and i2 - i1 == j2 - j1):
        for k in range(i2 - i1):
            times[i1 + k] = (wl[j1 + k]["s"], wl[j1 + k]["e"])
    elif tag == "replace":  # n palavras do texto <-> m do whisper: reparte o intervalo
        s0, e0 = wl[j1]["s"], wl[j2 - 1]["e"]
        for k in range(i2 - i1):
            times[i1 + k] = (s0 + (e0 - s0) * k / (i2 - i1), s0 + (e0 - s0) * (k + 1) / (i2 - i1))
        print("  ~", " ".join(toks[i1:i2]), "<->", " ".join(w["w"] for w in wl[j1:j2]))
    elif tag == "delete":
        print("  sem tempo:", " ".join(toks[i1:i2]))
# preenche faltas por interpolação
for i, t in enumerate(times):
    if t is None:
        p = next(times[k] for k in range(i - 1, -1, -1) if times[k])
        n = next((times[k] for k in range(i + 1, len(times)) if times[k]), (p[1] + 0.3, p[1] + 0.6))
        times[i] = (p[1], max(p[1] + 0.05, n[0]))

# POR EPISÓDIO — tempos corrigidos à mão (conferidos na fonte com vad.py). Exemplo: o whisper colou o "Qual" (106,66 s na fonte) no fim do trecho anterior
FIX = [("Qual", 1, 59.63, 59.80), ("notícia", 1, 59.98, 60.30), ("que", 0, 60.30, 60.40)]   # nth 0 = última ocorrência
for word, nth, s0, e0 in FIX:
    i = [k for k, t in enumerate(toks) if norm(t) == norm(word)][nth - 1]
    times[i] = (s0, e0)
    times[i - 1] = (times[i - 1][0], min(times[i - 1][1], s0 - 0.05))

# palavra sem duração (whisper colou com a anterior): divide o tempo da anterior
for i in range(1, len(times)):
    (ps, pe), (cs, ce) = times[i - 1], times[i]
    if ce - cs < 0.05 and pe - ps > 0.3:
        mid = round((ps + pe) / 2, 3)
        times[i - 1], times[i] = (ps, mid), (mid, max(ce, pe))
# palavras coladas pelo whisper (mesmo início) ganham no mínimo 0,1 s cada, para a legenda não piscar
for i in range(1, len(times)):
    if times[i][0] < times[i - 1][0] + 0.1:
        s0 = times[i - 1][0] + 0.1
        times[i] = (s0, max(times[i][1], s0 + 0.1))

segs = json.load(open(os.path.join(W, "segs.json")))
DUR = segs["duration"]
words = [{"w": t, "t": round(s, 3), "e": round(e, 3), "brk": i in BREAK} for i, (t, (s, e)) in enumerate(zip(toks, times))]

# grupos: quebra em pontuação, gap > 0.6 s, máx. 3 palavras / 18 caracteres
groups, cur = [], []
def text_of(g): return " ".join(x["w"].lstrip("*").rstrip(".,?!:") for x in g)
for tk in words:
    if cur:
        gap = tk["t"] - cur[-1]["e"]
        if tk["brk"] or cur[-1]["w"][-1] in ".,?!:" or gap > 0.6 or len(cur) >= 3 or len(text_of(cur + [tk])) > 15:
            groups.append(cur); cur = []
    cur.append(tk)
groups.append(cur)
CAPS = []
for gi, g in enumerate(groups):
    t0 = max(0.0, g[0]["t"] - 0.04)
    nxt = groups[gi + 1][0]["t"] - 0.04 if gi + 1 < len(groups) else DUR
    t1 = min(nxt, g[-1]["e"] + 0.5)
    CAPS.append({"t0": round(t0, 3), "t1": round(t1, 3),
                 "w": [{"x": x["w"].lstrip("*").rstrip(".,?!:"), "k": x["w"].startswith("*"), "t": x["t"]} for x in g]})
json.dump({"caps": CAPS, "words": words, "dur": DUR}, open(os.path.join(W, "data.json"), "w"), ensure_ascii=False)
# palavras.json (transcript HyperFrames) e SRT para entrega
json.dump([{"text": w["w"].lstrip("*"), "start": w["t"], "end": w["e"]} for w in words],
          open(os.path.join(W, "palavras.json"), "w"), ensure_ascii=False, indent=1)
for c in CAPS:
    print(f"{c['t0']:6.2f}-{c['t1']:6.2f} " + " ".join(("*" if w["k"] else "") + w["x"] for w in c["w"]))
print("dur", DUR, "grupos", len(CAPS))
