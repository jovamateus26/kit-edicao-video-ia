# Avisos de terceiros

O kit (instruções, guias, modelos e scripts) é licenciado sob MIT (`LICENSE`). As peças abaixo são de terceiros e
seguem a licença de cada uma.

## Dentro do kit

| O quê | Onde | Licença | Observação |
|---|---|---|---|
| Nomes, títulos e descrições do registry do HyperFrames (HeyGen) | `skills/proprias/editor-video-alta-retencao/referencias/catalogo_hyperframes.{json,md}` e `badges/hyperframes_models.json` | Apache-2.0 (`LICENSES/Apache-2.0.txt`) | catálogo derivado do registry de github.com/heygen-com/hyperframes, resumido e com campos nossos (uso, função) |
| Fonte Inter (The Inter Project Authors) | `skills/proprias/editor-video-alta-retencao/badges/assets/fonts/` | SIL Open Font License 1.1 | texto em `OFL-Inter.txt` na mesma pasta |
| Fonte Ubuntu Sans e Ubuntu Sans Mono (Canonical Ltd.) | mesma pasta | Ubuntu Font Licence 1.0 | texto em `UFL-1.0-UbuntuSans.txt` na mesma pasta |

## Baixado na instalação ou no primeiro uso (não vem no kit)

| O quê | Quem baixa | Licença | Observação |
|---|---|---|---|
| Skills do HyperFrames (HeyGen) | `instalar.sh` / `instalar.ps1`, de github.com/heygen-com/hyperframes (lista e versões em `skills/hyperframes.lista`) | Apache-2.0 | o clone traz o `LICENSE` original |
| Efeitos sonoros da skill `media-use` | vêm com as skills do HyperFrames | Pixabay Content License | uso livre nos vídeos; não redistribua os arquivos soltos |
| CLI `hyperframes` e `puppeteer-core` | `npx` | Apache-2.0 | |
| GSAP | CDN (jsDelivr) na hora do render | GSAP Standard License (gsap.com/standard-license) | gratuito, inclusive para uso comercial |
| faster-whisper, CTranslate2 | `wh` no primeiro uso (pip) | MIT | |
| cuBLAS e cuDNN da NVIDIA | `wh` no primeiro uso (pip, só com GPU NVIDIA) | licença da NVIDIA para as bibliotecas CUDA | |
| Modelo Robust Video Matting (`rvm_mobilenetv3_fp32.onnx`) | `matte_rvm.py` no primeiro uso, do release oficial | GPL-3.0 | o kit só baixa e executa o modelo |
| Pesos do MusicGen (`facebook/musicgen-small`) | `musicgen.py` no primeiro uso | CC-BY-NC 4.0 | **uso não comercial**: para vídeo monetizado ou de cliente, use trilha licenciada (biblioteca da plataforma, Pixabay, etc.) |
| ffmpeg, Python, Node.js, uv, Chrome/Edge | você instala | licenças próprias | |
