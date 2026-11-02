# Limpeza da fala: o padrão profissional

O vídeo é devolvido quando sobra qualquer um destes: pausa morta, "ããã"/"ééé", respiração audível, estalo de boca,
palavra repetida ("a Reuters acabou de… a Reuters acabou de"), gaguejo ("ele- eleitoral"), vogal esticada ("daaa das"),
pedaço da palavra vizinha numa emenda ("k" de "que", um "e…" baixinho), fim cortado no meio da entonação ou cauda em que
a pessoa se mexe para sair. Tudo isso é "falha amadora" e não é admitido.

## O que o `build.py` já faz

| Etapa | Valor | Observação |
|---|---|---|
| Limiar de pausa | `THR = −37 dB` absoluto | Sala ruidosa (−35 dB de fundo): −31 a −30,5 e cortes explícitos nas pausas que passam |
| Ripple | pausa interna > `MAX_GAP = 0,25 s` vira corte | fica ~0,16 s entre frases (`KEEP_PRE` 0,09 + `KEEP_POST` 0,07) |
| Ar morto | apara silêncio/respiração no começo e no fim de cada trecho | refino de borda pela energia (10 ms) |
| Respiração | debreath: trechos sem voz, graves, de energia média, −14 dB | protege 50 ms em volta das vogais |
| Estalos | `highpass=70`, `adeclick` | |
| Emendas | micro-fades seno de 20–25 ms | sem clique |
| Fim | `fadeout`: cauda de 0,9 s no último trecho | feche na frase inteira, olhando pra câmera |
| Dinâmica | compressor 3:1 + limiter | o nível final vem do `finalize.sh` |

## O que o whisper esconde (e como achar)

Janelas longas do whisper e o `wh edit` da fala montada **completam** palavras e **engolem** repetições coladas: uma
repetição sem pausa vira uma palavra curta de 1,4 s. Por isso:

1. **`audit.py` (obrigatório):** retranscreve cada trecho usado em janelas de 2,4 s (passo 1,8 s) direto na fonte e marca
   `REPETE`, `ESTICADA` e `FILLER`. Zero marca sem explicação antes do render.
2. **`!` nunca é "desalinhamento" sem medir.** Palavra curta com `!` (ex.: "de" de 1,4 s) é repetição escondida até prova
   em contrário. Meça na fonte com perfil de 10 ms/5 ms e centroide:
   - vogal "a"/"e" ≈ 1000 Hz; "o"/nasal ≈ 400–600 Hz; "s"/"tʃ" > 2000 Hz;
   - `prof5.py` mostra dB, vozeamento e centroide a cada 5 ms (achou "editar" onde o whisper ouvia "digitar").
3. **`edgecheck.py`:** suspeita de FIM (energia sobe nos últimos 60 ms = começo da próxima palavra) e de INÍCIO (rabo da
   anterior). Confira cada uma na fonte: `vad.py`, `prof5.py`, `wh try` com variantes.
4. **Pausas que o ripple não pegou:** respiração em −37 dB no meio da pausa segura o trecho. Varra a fala montada atrás
   de pausas > 0,25 s abaixo de −38 dB e corte à mão.

## Onde cortar

- **Fim do trecho:** antes da subida de energia da próxima palavra.
- **Fala contínua** ("criou um", "criando uma"): corte de forma que só uma das vogais fique; teste com `wh try`.
- **Ligação** "carros e" = "carroz‿e": corte no fim do "o".
- **Palavra repetida** ("mui|to"): o corte no meio funciona na oclusão do "t".
- **Vogal esticada** ("deee", "isso ééé… um"): corte o meio da vogal (perfil de 5 ms) e emende as pontas.
- **Pausa de vírgula que muda o som:** às vezes a pausa curta precisa ficar (`nosplit`/`ea`): sem ela um "o" curto vira "e".

## Fecho e cauda

- Termine na frase inteira, com ~0,4 s olhando pra câmera e fade.
- Nunca use como cauda o trecho em que a pessoa se levanta, desliga a câmera ou baixa o olhar. Se não der para cortar o
  áudio, escureça a imagem antes (fim escuro com o CTA por cima).

## Áudio de terceiros

Procure nas transcrições música com letra tocando ao fundo, TV, anúncio de outro vídeo: esses trechos ficam fora
(direitos autorais e distração).
