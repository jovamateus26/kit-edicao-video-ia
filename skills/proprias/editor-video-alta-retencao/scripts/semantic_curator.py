#!/usr/bin/env python3
"""
Módulo de Curadoria Semântica e Narrativa (Semantic Curator Engine).
Identifica e elimina defeitos editoriais de fala que ferramentas acústicas não percebem:
1. Retakes Temáticos: Quando o locutor tenta falar a mesma ideia 2 ou mais vezes,
   o curador descarta a primeira tentativa (inferior/rascunho) e preserva a tomada definitiva.
2. Frases Incompletas / Abandonadas: Podas de orações que terminam em preposições
   ou verbos suspensos seguidos de silêncio (ex: "preparando um servidor para... vai...").
3. Ecos Narrativos: Repetições de argumentos ou pensamentos em janela curta de tempo.
"""

import re

STOPWORDS = {
    "para", "pra", "como", "mais", "esse", "essa", "este", "esta", "isso", "pelo", "pela",
    "qual", "fazer", "pode", "vamos", "aqui", "então", "também", "tudo", "onde",
    "quando", "muito", "pouco", "assim", "ainda", "depois", "antes", "sobre", "estar",
    "eles", "deles", "minha", "meus", "umas", "uns", "ter", "ser", "terá", "será"
}

DANGLING_ENDINGS = {
    "para", "pra", "de", "e", "com", "por", "em", "que", "onde", "quando", "antes",
    "vai", "vou", "ia", "era", "foi", "estava", "uma", "um"
}

def clean_word(token: str) -> str:
    return re.sub(r"[^\wáéíóúâêîôûãõç]", "", token.lower())

def extract_keywords(text: str) -> set:
    tokens = [clean_word(t) for t in text.split()]
    return set(t for t in tokens if len(t) >= 4 and t not in STOPWORDS)

def find_semantic_retakes(segments: list, max_gap: float = 40.0, min_containment: float = 0.55):
    """
    Varre os segmentos transcritos procurando retakes conceituais.
    Se o segmento A e o segmento B (até max_gap segundos depois) expressam o mesmo tema
    com sobreposição alta de termos-chave, o segmento A é marcado como rascunho/retake.
    """
    discarded_segment_indices = set()
    retake_reasons = {}
    
    n = len(segments)
    for i in range(n):
        if i in discarded_segment_indices:
            continue
            
        kw_a = segments[i].get("keywords")
        if not kw_a or len(kw_a) < 2:
            continue
            
        # Procura em segmentos posteriores dentro da janela de tempo
        for j in range(i + 1, n):
            if j in discarded_segment_indices:
                continue
                
            gap = segments[j]["start"] - segments[i]["end"]
            if gap > max_gap:
                break
                
            kw_b = segments[j].get("keywords")
            if not kw_b or len(kw_b) < 2:
                continue
                
            inter = kw_a.intersection(kw_b)
            if not inter:
                continue
                
            # Coeficiente de contenção: quanta da ideia de A está contida em B
            containment_a_in_b = len(inter) / len(kw_a)
            containment_b_in_a = len(inter) / len(kw_b)
            
            # Se A foi uma tentativa de introdução ou ideia repetida em B
            if (containment_a_in_b >= min_containment and len(inter) >= 3) or (containment_a_in_b >= 0.75 and len(inter) >= 2):
                # Se A tem frases abandonadas ou B é mais completo, descarta A
                discarded_segment_indices.add(i)
                overlap_str = ", ".join(list(inter)[:4])
                retake_reasons[i] = f"retake semântico descartado em favor do take definitivo aos {segments[j]['start']:.1f}s (tópicos: {overlap_str})"
                break
                
    return discarded_segment_indices, retake_reasons

def find_dangling_incomplete_clauses(words: list, pause_threshold: float = 0.35):
    """
    Identifica palavras que terminam frases de forma abrupta antes de uma pausa,
    deixando conectivos soltos como 'para... vai...' ou 'e antes...'.
    """
    discarded_word_indices = set()
    reasons = {}
    n = len(words)
    
    for i in range(n - 1):
        curr = words[i]
        nxt = words[i + 1]
        gap = nxt["start"] - curr["end"]
        
        # Se há uma pausa relevante após a palavra atual
        if gap >= pause_threshold:
            c = curr["clean"]
            # Se a palavra é um conectivo pendente ou preposição solta
            if c in DANGLING_ENDINGS:
                discarded_word_indices.add(i)
                reasons[i] = f"frase incompleta / preposição suspensa ('{curr['word']}')"
                
                # Se a palavra anterior também era conectivo (ex: 'para... vai'), remove em cadeia
                if i > 0 and words[i - 1]["clean"] in DANGLING_ENDINGS:
                    discarded_word_indices.add(i - 1)
                    reasons[i - 1] = f"frase incompleta / conectivo duplo ('{words[i-1]['word']} {curr['word']}')"
                    
    return discarded_word_indices, reasons

def curate_speech(words: list, raw_segments: list):
    """
    Executa a curadoria completa combinando poda sintática e eliminação de retakes temáticos.
    Retorna os índices das palavras descartadas e os motivos correspondentes.
    """
    discarded_indices = set()
    reasons = {}
    
    # 1. Poda de orações quebradas e conectivos suspensos
    dangling_indices, dangling_reasons = find_dangling_incomplete_clauses(words)
    discarded_indices.update(dangling_indices)
    reasons.update(dangling_reasons)
    
    # 2. Prepara segmentos com palavras-chave para análise semântica
    processed_segments = []
    for s in raw_segments:
        text = s.get("text", "")
        processed_segments.append({
            "start": s.get("start", 0.0),
            "end": s.get("end", 0.0),
            "text": text,
            "keywords": extract_keywords(text)
        })
        
    # 3. Detecta e descarta blocos de retake
    retake_seg_indices, retake_reasons = find_semantic_retakes(processed_segments)
    
    # Mapeia os segmentos descartados para as palavras individuais
    for seg_idx in retake_seg_indices:
        seg = processed_segments[seg_idx]
        reason = retake_reasons[seg_idx]
        for w_idx, w in enumerate(words):
            # Se a palavra está dentro do tempo do segmento descartado
            if w["start"] >= seg["start"] - 0.05 and w["end"] <= seg["end"] + 0.05:
                discarded_indices.add(w_idx)
                if w_idx not in reasons:
                    reasons[w_idx] = reason
                    
    return discarded_indices, reasons
