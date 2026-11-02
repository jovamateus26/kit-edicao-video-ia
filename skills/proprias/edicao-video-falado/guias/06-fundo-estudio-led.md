# Fundo de estúdio escuro com LED animado

Troca a parede de casa por um estúdio escuro com fitas de LED, sanca, neon, luzinhas, neblina e bokeh de lente, com a cor
mudando a cada notícia. É o fundo padrão do giro de notícias. Deixa o vídeo com cara de telejornal sem precisar de cenário.

## Ordem

1. **EDL fechada** (`audit.py` limpo). Mexeu na EDL depois, refaça o recorte.
2. **Recorte da pessoa com RVM**, em segundo plano, enquanto faz legenda e composição:
   ```bash
   uv run --with numpy --with onnxruntime python -I $PIPE/matte_rvm.py        # CPU: ~12 min para 80 s
   $VENV_TORCH/bin/python -I $PIPE/matte_rvm_gpu.py                           # GPU NVIDIA: ~1 s por segundo de vídeo
   ```
   Saída: `matte/pha.mkv` (alfa, sem perda) e `matte/fgr.mp4`. O modelo (15 MB, release oficial do RVM) é baixado uma vez
   para `~/.cache/rvm/` com conferência de hash. O `hyperframes remove-background` (u2net 320 px, sem coerência entre
   quadros) não serve: a borda treme e o cabelo vira bloco.
3. **`estudio.json` na `.work`** (modelo em `modelos/giro-noticias/.work/estudio.json`):
   - `climas`: clima de cor de cada bloco pelo assunto. Nomes no `studio.py`: `alerta` (segurança, ataque, risco),
     `violeta` (big techs, redes sociais, varejo), `energia` (data centers, chips, infraestrutura), `ambar` (IA de empresa,
     dinheiro, IPO), `verde` (saúde, ciência, clima), `apocalipse` (pergunta final dramática), `marca` (abertura/CTA).
     Também aceita `[matiz esq., matiz dir., matiz sanca]` em graus.
   - `topicos`: `[[0, "n1"], [13.2, "n2"], ...]` quando as trocas não vêm das tags do `index.html`.
   - `mesa`: `{"<fonte>": {"q": [a, b]}}` se houver mesa de verdade na frente (abaixo de y = a + b·x vira primeiro plano).
   - `limpar`: `{"<fonte>": {"q": [[x0, x1, y0, y1]]}}` canto onde o RVM gruda um pedaço do cenário no corpo (some o que é
     rosa/vermelho, esverdeado ou quase branco ali). Só se a roupa não tiver essas cores: uma placa mediana já furou a manga.
   - `rosto`: `{"<fonte>": {"q": [x, y]}}` centro da luz principal, se a detecção automática errar.
4. **Teste de quadros** (com o `make.py` já rodado, para as tags marcarem as trocas):
   ```bash
   uv run --with numpy --with opencv-python-headless python -I $PIPE/composite.py 3.5,14.0,27.2    # matte/qc_<t>.jpg
   ```
   Confira: luz no rosto, bordas, sobra de cenário, cabelo, mãos rápidas (borrão de movimento).
5. **Composição inteira** e remontagem:
   ```bash
   uv run --with numpy --with opencv-python-headless python -I $PIPE/composite.py   # ../assets/footage/fala_estudio.mp4
   FALA=fala_estudio.mp4 python3 -I make.py
   ```
   CPU: ~10 min para 80 s com o CPU livre (~30 min dividindo com o render). `Q0`/`Q1`/`PART` dividem em pedaços paralelos.
   GPU NVIDIA: `$VENV_TORCH/bin/python -I $PIPE/composite_gpu.py` (~21 q/s numa L4; com tempos, compara com a versão CPU).
6. **Enquadramento de telejornal** (giro gravado de corpo inteiro, longe da câmera): `reframe.py` sobre o `fala_estudio.mp4`.
   - O que faz:
     - deixa plano médio fechado (rosto e tronco) na maior parte do vídeo, alternando A (mais aberto) e B (mais fechado) a
       cada corte, como duas câmeras: isso esconde o jump cut;
     - mantém corpo inteiro, como foi gravado, só nas cenas-chave;
     - segue o rosto e compensa 60% da ida e volta da pessoa até a câmera.
   - Em plano aberto, a ida e volta até o celular e a mudança de distância entre as tomadas ficam evidentes. No plano
     fechado, o vídeo ganha cara de apresentador de telejornal.
   - No `estudio.json`, ponha `"planos": {"aberto": [...]}`: o início na fonte (campo `a` do `segs.json`) de cada trecho em
     corpo inteiro. No giro, são a abertura das notícias 2 em diante e o "segue o canal" do fim. Sem `aberto`, o script
     avisa e lista o `a` de cada trecho.
   - `"A": [450, 350]` e `"B": [520, 320]` (altura da caixa do rosto e topo do rosto no quadro novo, em px), `"zmax": 2.0` e
     `"segue": 0.6` já são o padrão.
   ```bash
   uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/reframe.py 2.0,14.5,30.0   # qc/rf_<t>.jpg
   uv run --with numpy --with opencv-python-headless==4.10.0.84 python -I $PIPE/reframe.py                # ~5,5 min para 67 s
   FALA=fala_estudio_zoom.mp4 python3 -I make.py
   ```
   - Saída: `../assets/footage/fala_estudio_zoom.mp4` (áudio copiado) e `chin.json` já no quadro novo. O original fica em
     `chin_raw.json`; se ele faltar ou estiver mais velho que a `fala.mp4`, o script roda o `chin.py` sozinho (~1 min).
   - No `make.py` do giro: `ZALT = 1.0` (o reframe já alterna os planos) e `DMAX = 0` (no plano fechado, subir a câmera
     cortaria o cabelo; print que não cabe rola ou vai para tela cheia).
   - Nos quadros de teste, confira o plano aberto nas cenas certas e o cabelo e o queixo dentro do quadro.
   - Mexeu na EDL: refaça recorte → composite → reframe e confira o `aberto`.

## O que foi aprovado e o que foi reprovado

- Aprovado: fundo que parece real e se mexe (onda de cor nas fitas, neblina subindo, luzinhas piscando, bokeh), cor por
  notícia, luz na pessoa nas mesmas cores do fundo.
- **Reprovado: "linha clara em volta de mim recortado".** Luz somada por cima da borda acende uma faixa de 15–25 px em volta
  da pessoa e denuncia o recorte. A cor das fitas entra **larga e multiplicada** pela pele e pela roupa; a borda se mistura
  com o fundo desfocado de trás, com choke de 3% no alfa.

## Pegadinhas técnicas

- Antes de `** 2.2` (gama), faça clip em [0, 1]: valor negativo vira NaN e o NaN aparece no fundo mesmo com alfa 0.
- Não use `-shortest` no mux final (cortou 4 quadros).
- O estúdio é calculado em meia resolução (ele é desfocado) e ampliado na composição.
- GPU com driver que só vai até CUDA 12.4: use `onnxruntime-gpu==1.22.0` e `torch==2.6.0+cu124` (as versões mais novas
  do PyPI são CUDA 13). No onnxruntime 1.22, religar um OrtValue devolvido trava no 2º quadro: ligue tudo por ponteiro de
  tensor do PyTorch com dois conjuntos de memória alternados (já feito no `matte_rvm_gpu.py`).
- Nunca rode o `composite.py` (numpy) em servidor de vCPUs lentos: 0,8 q/s. Lá, use o `composite_gpu.py`.
