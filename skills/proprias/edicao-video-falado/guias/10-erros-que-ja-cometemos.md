# Erros que já cometemos (e viraram regra)

Cada item abaixo fez um vídeo voltar. Leia antes de entregar.

| O que aconteceu | Regra |
|---|---|
| Vídeo postado com quadros borrados e coloridos | `errmap.py` em todo bruto copiado do celular; não usar trechos com erro (`03-material-bruto.md`) |
| Imagem lavada, sem contraste | detecção de HDR com `-of default=nw=1:nk=1` (com `csv` sai vírgula e o tonemap não roda) |
| Áudio dessincronizado depois de um furo | extrair com `aresample=async=1:first_pts=0` |
| Respirações, "ããã", "praaa… pra" e repetições inteiras passaram no 1º corte | limiar absoluto −37 dB, ripple 0,25 s, debreath, adeclick, `audit.py` |
| Fim cortado seco no meio da entonação; cauda com a pessoa levantando | fechar na frase inteira, ~0,4 s olhando pra câmera, fade |
| Pedaço do começo da próxima palavra no fim de um trecho ("e…", "k") | `edgecheck.py` e conferir cada borda na fonte, não na fala montada |
| "a Reuters acabou de… a Reuters acabou de" passou como um "de" de 1,4 s | `!` em palavra curta = repetição até prova em contrário; `audit.py` antes de todo render |
| Pergunta provocativa usada como fecho | frase curta repetida em tomadas seguidas é o **gancho** de abertura |
| Pessoa olhando pra baixo (lendo a pauta) e se mexendo fora de contexto | revisão visual quadro a quadro; cortar ou cobrir com print grande |
| Parte de uma notícia não se confirmava | cortar o que não tem fonte; nunca selo de checagem na tela |
| Menção a pessoa/fato que o apresentador não falou | não acrescentar nada que não esteja na fala |
| "Prints" de pauta gerada por IA eram artes com texto inventado | prova é sempre o print real da matéria |
| Pauta de IA com fatos e números errados ("dezenas", "o dobro", valor convertido errado) | conferir número a número na fonte; ajustar tag e post ao que a fonte diz |
| Versão sem legenda dobrava o tempo de render | um vídeo só, com legenda |
| Giro com 2 min 25 s | notícia entre 60 e 90 s: enxugar cada notícia, manter todas, decidir antes do RVM |
| Contorno claro em volta da pessoa recortada | luz colorida larga e multiplicada; borda misturada com o fundo desfocado; nunca somar luz na borda |
| Tela dividida "cortando a tela" | sem split no giro: pessoa em tela cheia + print no espaço livre, ou print em tela cheia |
| Card encostando no queixo quando a pessoa se aproxima | `chin.py` com pior caso por intervalo + snapshot nos instantes críticos |
| `@` sem fundo reprovado no `check` (contraste) | `@` fixo com fundo escuro translúcido |
| Instrução falada ("corta essa parte") transcrita como "não corta" | ouvir a instrução com `wh snip`; opinião que ele pediu para cortar sai |
| Whisper do arquivo inteiro pulou 4 s da fala montada | completar o `transcript_edit.json` com `wh snip` |
| Whisper desalinha em pausas longas | janelas curtas (`wh snip`) e `vad.py` para achar o instante certo |
| Palavra ouvida errada ("digitar" × "editar") | perfil de 5 ms (`prof5.py`): fricativa, vogal e oclusiva têm assinatura própria |
| Espera com `until ! pgrep -f` travou 9 min | esperar pela notificação, pelo arquivo ou `wait PID` |
| Música com letra tocando ao fundo da gravação | procurar áudio de terceiros nas transcrições e deixar fora |
| Câmera frontal com o logo ao contrário | `hflip` no build |
| Nome de produto incerto no whisper | perguntar ao usuário antes de pôr na legenda |
| Comentário em quadro de tarefas acordou um agente e gastou execução | avisar antes de comentar onde há agentes ou notificações |
