# Segunda rodada de análise sob o ARCcC: falsificar os contratos (2026-10-01)

> **Pergunta que este documento responde:** depois de fechar os selos do
> relatório 08, a base esconde problemas profundos que a leitura do código não
> mostra? E, se não esconde, é hora de começar features?
>
> **Base analisada:** `bd22d1b` (`main`). **Correções desta rodada:** `fd8453d`
> (motor) e `a1ab625` (documento e arquivo de paginação). **Medido** no Linux do
> agente (Python 3.11, 4 núcleos); as sondagens ficam no rascunho da sessão, fora
> do repositório (regra de higiene do `AGENTS.md`); o método de cada número está
> no Apêndice A.
>
> **Limite do que sei:** nada aqui rodou no Windows. O que é específico dele
> (página de código ANSI, travas de arquivo, `Out-of-Tree`) foi conferido por
> leitura e pela compilação cruzada com MinGW-w64, não por execução.
>
> Relacionados: `08-analise-arccc-v1-1-e-forma-de-trabalho.md` (a rodada
> anterior, de leitura e medição), `01-pendencias-atuais.md` (lista viva).

---

## 1. Resumo

1. **Método novo:** a primeira rodada leu o código e mediu estrutura. Esta
   rodada fez o contrário: pegou cada promessa que a base faz (o leitor recusa
   arquivo ruim, o desfazer é exato, a tela é igual à composição inteira, salvar
   não muda o que foi capturado...) e tentou **derrubá-la por execução**, com um
   oráculo independente do código testado. Só vale como "a promessa se sustenta"
   a sondagem que **poderia** ter falhado (prova de mutação: desfaz a correção,
   o teste reprova).
2. **A base não estava sem defeito profundo: havia dois, no motor, e nenhum
   estava no caminho do usuário comum.** Um travamento do processo
   (`select_rect(2**31 - 1, 0, 1, 1)`, o mouse não produz essa coordenada) e uma
   deriva visual (depois de um traço ao lado de um filtro de área, a tela diferia
   da composição inteira em até 53 níveis, em milhares de pixels, até a próxima
   recomposição total). Os dois estão corrigidos, com teste que reprova sem a
   correção.
3. **Três defeitos menores de arquivo e plataforma**, também corrigidos: manifesto
   hostil chegava ao motor como `OverflowError`/`zlib.error` em vez de
   "arquivo inválido"; o manifesto gravava o caminho absoluto de quem salvou; o
   arquivo de paginação do desfazer não abria numa pasta temporária com nome fora
   da página de código ANSI do Windows.
4. **Um achado novo, registrado e não corrigido (D24):** processo morto deixa o
   arquivo de paginação do desfazer na pasta temporária, e nada o limpa depois.
5. **A maioria das promessas se sustentou** (Seção 4): 720 documentos salvos e
   reabertos sem diferença, 1200 arquivos corrompidos sem uma exceção inesperada,
   composição idêntica com 1 a 16 threads e na compilação AVX2, salvar enquanto
   se pinta grava o que foi capturado, memória e threads planas em 40 ciclos de
   abrir, pintar e fechar.
6. **Veredito (Seção 6): sim, é hora de feature**, com três condições que são
   exigências da primeira feature que as tocar, não trabalho de organização
   antecipado: o custo do traço sob filtro de área (S1.5), a parada de 0,2 a 0,7 s
   ao abrir documento denso, e rodar a sondagem de contrato como porta de cada
   feature nova.

---

## 2. Como a análise foi feita (ARCcC aplicado à análise)

A seção 4.4 do ARCcC diz como construir: responsabilidade, contrato, teste do
contrato antes do código, fatia vertical, evidência. Aplicada à análise, o mesmo
laço vira:

| Passo da construção | Passo da análise |
|---|---|
| Responsabilidade em uma frase | A promessa do componente, em uma frase ("a tela mostra a composição do documento") |
| Tipo e teste do contrato | O oráculo: algo que calcula a resposta por outro caminho (composição inteira, implementação de 32 bits, arquivo antes de salvar) |
| Implementação mínima | A sondagem mínima que gera entradas além do que a interface produz (processo filho isolado, limite de memória, sementes fixas) |
| Fatia vertical real | Interface → ponte → motor real, sem dublê |
| Evidência | Número medido e prova de mutação (a sondagem reprova sem a correção) |
| Volta à fundação | Seis perguntas da 4.4.7, no changelog |

Duas regras da rodada: (a) sondagem que roda sem falhar **não** prova nada até
ter reprovado uma vez de propósito; (b) o que a sondagem acha entra em dois
lugares, a correção e o teste que fica no repositório, e a sondagem em si volta
para o rascunho.

---

## 3. Defeitos achados (todos com correção e teste, exceto D24)

Numeração segue o relatório 08 (D1–D18).

### D19 — coordenada extrema derrubava o processo (motor, `fd8453d`)

`select_rect(2**31 - 1, 0, 1, 1)` terminava com SIGSEGV. `generateRectMask` e
`generateEllipseMask` calculavam `x + w - 1`, `-w`, `cx - rx - 1` e o quadrado do
raio do canto em `int`, e o polígono por linha de varredura convertia um `double`
fora do alcance. Achado ao enviar entradas inválidas a todos os 173 métodos da
facade (12 sementes, processo filho isolado): **1 queda**, todo o resto recusava
com erro limpo. Corrigido com aritmética de 64 bits e limite antes da conversão.
6000 cenas sãs (retângulo com raio e pena, elipse, polígono com e sem
anti-alias, quatro modos de combinação) dão o mesmo hash antes e depois; 800
ficam como pino. Teste: `tests/test_selection_extreme_coordinates.py` (reprova
com código de retorno -11 sem a correção).

*Quem sente:* ninguém hoje, o mouse não gera essa coordenada. É o motor
cumprindo a promessa de que "fora do alcance é recusado".

### D20 — a tela diferia da composição inteira ao lado de um filtro de área (motor, `fd8453d`)

Depois de um traço perto de uma camada de ajuste de área (desfoque gaussiano,
nitidez, pixelizar), a imagem na tela diferia da composição inteira até algo
forçar a recomposição total: até 53 níveis em milhares de pixels; 56 de 400
pilhas aleatórias. O compositor ampliava a região suja pelo alcance dos filtros e
escrevia tudo, mas a faixa de fora não tinha vizinhos para o filtro e saía
errada. Achado por uma propriedade (desfazer e refazer operações aleatórias e
comparar a tela: 600 sequências, 6819 passos). Corrigido: compõe com o dobro do
alcance de contexto, escreve a região mais um alcance e devolve a faixa de fora
como estava (`RegionMargin`); o dano da pirâmide cobre só o que mudou. 400
pilhas aleatórias de camadas, grupos, modos e filtros: 56 diferiam, 0 diferem.
Teste: `tests/test_composite_region_filters.py` (reprova com diferenças de 33 a
47 níveis sem a correção).

*Quem sente:* o artista que pinta sob um desfoque via halos que sumiam sozinhos.

*Custo, medido (4K, traço de 30 amostras sob camada de desfoque, mediana de 5):*
raio 20: 57 → 99 ms; raio 60: 366 → 849 ms; raio 100: 1065 → 2887 ms; raio 0
(sem filtro de área): 12,9 → 12,5 ms. O custo é o contexto maior. O caminho para
recuperá-lo é guardar a composição anterior ao filtro (S1.5), e fica para a
feature que precisar. **Isto é uma troca assumida: correção primeiro, velocidade
quando houver quem a use.**

### D21 — manifesto hostil escapava como exceção do motor (documento, `a1ab625`)

Em 1200 arquivos corrompidos (Seção 4), 8 produziram erro inesperado: 7 vezes
`zlib.error` cru (entrada deflate danificada dentro do zip) e 1 vez `TypeError`
vindo de `set_canvas_height_preset`. Lendo o que a validação cobria, apareceu a
causa comum: o bloco `paper` do manifesto não era validado, e um id de textura
≥ 2³¹ chegava à ponte como `OverflowError` com o documento já meio construído.
`validate_auxiliary` agora valida o papel (tipo e faixa de cada campo; cor como
lista de 3 ou 4 números) e o leitor trata `zlib.error` como arquivo corrompido.
Mesmo arquivo de 1200 mutantes, mesma semente: **8 inesperados → 0**. Teste:
`tests/test_document_hostile_manifest.py` (12; 4 reprovam sem a correção).

### D22 — o manifesto gravava o caminho absoluto de quem salvou (`a1ab625`)

`save_capture` colocava `"file_path": str(target)` no manifesto. Ninguém lia o
campo; quem recebe o arquivo recebia o nome da pasta do autor (usuário, projeto,
disco). Removido, com teste de que o manifesto gravado não contém a pasta.

### D23 — arquivo de paginação do desfazer não abria em pasta fora da página ANSI (motor, `a1ab625`)

No Windows, `std::filesystem::path::string()` converte para a página de código
ANSI: uma pasta temporária sob um usuário "田中" ou "Łukasz" virava `?`, o arquivo
não abria, o disco de rascunho ficava desligado em silêncio e o histórico acima
do limite de memória era **podado em vez de paginado** (o artista perdia
profundidade de desfazer sem aviso). `ScratchDiskManager` agora guarda o caminho
como `std::filesystem::path` em toda operação; a `string` só serve a
`getFilePath()`. **Limite honesto:** o Linux nunca teve o defeito, então
`tests/test_scratch_disk_unicode_path.py` **não pode reprovar aqui**; ele
registra o que o build do Windows tem de continuar fazendo, e a compilação
cruzada (`check_windows_build.py`, 76/76 escalar e AVX2) confere que as
sobrecargas de `path` compilam. A prova de execução fica para o Windows.

### D24 — arquivo de paginação órfão depois de processo morto (motor, **aberto**)

Medido: saída normal remove o arquivo; `os._exit(0)` (e qualquer queda ou
encerramento forçado) o deixa na pasta temporária, e nenhum código varre os
órfãos na partida. Com o histórico paginado, o órfão tem o tamanho do que foi
paginado: **4,4 MB** na sondagem (60 traços de pincel 500 px, 4K, limite de
desfazer 0); 0 byte quando nada foi paginado. Durante a rodada, os processos
filhos mortos pelo fuzz deixaram **444 arquivos vazios** em `/tmp`. Correção
possível: na partida, apagar `lumenia_scratch_<pid>_*` cujo `pid` não está vivo
(precisa do teste de processo vivo por plataforma, `OpenProcess` no Windows).
Não corrigido agora: o usuário só sente depois de uma queda e com histórico longo,
o que não entra na linha de chegada (`01-pendencias-atuais.md`); registrado
para entrar junto de qualquer feature que aumente o histórico pago em disco.

---

## 4. O que a rodada confirmou (promessas que se sustentaram)

| Promessa | Sondagem | Volume | Resultado |
|---|---|---|---|
| O leitor recusa arquivo ruim sem queda, travada nem exceção alheia | 1200 mutantes (bytes trocados, truncamento, zeros, manifesto com valor extremo, tiles, payloads, ICC com lixo), cada um num processo com limite de 6 GiB | 1200 | 1083 recusados limpos, 117 abrem; **0 queda, 0 travada, 0 inesperado** (antes de D21: 8) |
| A ponte recusa argumento ruim | cada um dos 173 métodos da facade com valores extremos, processo filho, 12 sementes | 173 × 12 | 1 queda (D19), o resto recusa limpo |
| Desfazer e refazer são exatos | sequências aleatórias de operações comparando composição incremental e inteira | 600 sequências, 6819 passos | achou D20; depois da correção, 0 diferença |
| A tela é a composição inteira | 400 pilhas aleatórias (camadas, grupos, alguns modos de mesclagem, os 7 tipos de filtro) comparando composição por região e inteira | 400 | 56 diferiam → 0 |
| Composição não depende de threads nem de SIMD | mesma cena com `OMP_NUM_THREADS` 1, 2, 3, 4, 7 e 16; build `-mavx2` contra todos os pinos de pixel e de caracterização | 6 + suíte | idêntica; AVX2 passa tudo |
| Salvar grava o que foi capturado, mesmo pintando durante a gravação | traços na thread principal durante a escrita, arquivo comparado com a captura | 6 ensaios, 136 a 200 traços durante a escrita | idêntico em 6 de 6 |
| Salvar e abrir reproduz o documento | 720 documentos aleatórios (camadas, grupos, filtros, modos, papel, textura, perfil de cor, DPI) | 720 | **0 diferença** |
| Abrir, pintar e fechar não vaza | 40 ciclos num documento 1600×1000 de 4 camadas pintadas | 40 | RSS 177 MB (igual em todas as 8 amostras), 5 descritores abertos, 1 thread Python |
| Máscaras de seleção iguais ao código anterior | 6000 cenas sãs, hash antes e depois | 6000 | idênticos |

As sondagens que acharam D19 a D21 foram **reprovadas de propósito** (correção
desfeita, teste reprova) antes de valer como evidência. As demais valem como
"não achei com este volume e este oráculo", não como "provado".

---

## 5. Resíduos (medidos, fora do que esta rodada corrigiu)

| Item | Medida | Por que não foi tratado |
|---|---|---|
| Parada ao abrir documento 4K denso | 0,2 a 0,7 s na thread da interface (composição única na adoção) | Fecha com documento construído fora da thread e anexado em tempo constante (motor e ponte, versão 7); é o selo "Arquivo" 🟡 |
| Custo do traço sob filtro de área | 1,7× a 2,7× em raio 20 a 100 (Seção 3, D20) | Cache da composição pré-filtro (S1.5), puxado por feature |
| Pedidos globais ao registro do motor | 21 em 18 arquivos | Congelados na catraca; só descem |
| Facade nativa | 173 métodos no `.pyi`, 29 sem uso no cliente da ponte | Mudança de motor e ponte (versão 7), junto da feature |
| `compositeRegionWithScratch` | nenhum chamador (código morto do motor) | Sai junto de S1.5, que decide o destino do overlay do traço |
| D11 (prévia da transformação) | não tratado | Puxado pela feature de transformação |
| D24 (órfão de paginação) | Seção 3 | Registrado, com correção desenhada |

---

## 6. Veredito: é hora de feature?

**Sim.** Os critérios:

- **O que a rodada procurava existe e foi achado:** dois defeitos de motor que a
  leitura não mostrava, ambos fora do caminho do usuário comum e ambos
  corrigidos com teste. O resto das promessas sustentou-se sob 9 sondagens com
  volume de 6 a 6000 casos. Uma terceira rodada de organização acharia menos que
  esta, e já está abaixo do que a linha de chegada manda tratar (defeito que o
  usuário sente hoje).
- **A base aguenta feature porque pega a próxima regressão:** as correções
  desta rodada entraram com teste que reprova sem elas, e os contratos (papéis do
  motor, portas do canvas, catracas) rodam na suíte, 1826 testes, saída 0.

**Três condições, que valem como exigência da feature que tocar o assunto:**

1. **Feature que adiciona ou usa camadas de filtro de área** traz o S1.5 (cache
   da composição pré-filtro) na mesma entrega; sem ele o artista paga 1,7× a 2,7×
   por traço sob desfoque.
2. **Feature que mexe em abrir, camadas ou histórico** traz a sondagem de
   contrato correspondente como teste do repositório. Candidatas já escritas no
   rascunho: o salvar-e-abrir de 720 documentos (versão de 20 sementes cabe na
   suíte), a propriedade de desfazer e refazer, e o diferencial de composição
   por região (já promovido).
3. **Toda feature passa pelo ciclo da 4.4 com a pergunta nova**: *qual
   promessa esta feature faz e qual sondagem tentaria derrubá-la?* A resposta vai
   no commit.

**O que esta rodada não cobriu** (a lista de onde ainda pode haver defeito):
execução no Windows (D23 vale só por leitura e compilação), ASan e UBSan, ordem
dos eventos da interface com `pytest-qt` e entrada real, fuzz de importação de
imagem e de perfil ICC além dos mutantes de perfil, e o ramo Windows das medidas
de memória. A primeira cobertura que valeria rodar quando o dono tiver o
Windows à mão é a suíte completa e `run_app_benchmarks.py` lado a lado com os
números do Linux.

---

## Apêndice A — como cada número foi medido

- **Mutantes de arquivo:** `.lmn` semente de 4 camadas, 10 mutadores (troca de
  bytes, truncamento, zeros, valor extremo no manifesto, cabeçalho e corpo de
  tiles, payloads curtos, longos e trocados, perfil ICC com lixo); cada
  mutante abre num processo filho como `DocumentActions._finish_open` abre, exibe
  uma região e salva de novo, com `RLIMIT_AS` de 6 GiB e limite de 45 s.
  Semente 2, 1200 mutantes: 1075 + 117 + 8 antes; 1083 + 117 depois.
- **Argumentos ruins:** valores extremos (zero, negativos, `2**31`, `2**63`,
  NaN, infinito, texto longo) para cada método da facade, um processo filho por
  método, 12 sementes.
- **Desfazer e refazer:** sequências aleatórias de traço, camada, filtro,
  mesclagem, desfazer e refazer; depois de cada passo, a composição incremental
  (a que a tela recebe) é comparada com a composição inteira do mesmo estado.
- **Composição por região:** 400 pilhas aleatórias de camadas, grupos e filtros
  (150×110 px); diferença máxima em níveis de 0 a 255, composição por região
  contra composição inteira.
- **Determinismo:** hash da composição com `OMP_NUM_THREADS` fixado; build
  `-mavx2` com os pinos de `tests/golden/`.
- **Salvar com corrida:** 6 ensaios, hash do que o arquivo grava contra o hash da
  captura, com traços na thread principal durante a escrita.
- **Salvar e abrir:** `roundtrip_prop.py 0 720`, estado (modelo de camadas, hash
  de pixels com alfa 0 zerado, composição, papel, perfil, DPI) antes e depois.
- **Ciclos:** 40 ciclos de abrir, 6 traços, fechar, com RSS, descritores e
  threads amostrados a cada 5.
- **Órfão de paginação:** `os._exit(0)` contra saída normal; tamanho do arquivo
  deixado na pasta temporária.
- **Custo do traço sob desfoque:** 4K, 30 amostras, mediana de 5; antes e
  depois da correção, com a mesma cena.
- **Suíte:** `python -m pytest --collect-only -q` somado por arquivo: 1826;
  `python -m pytest`: saída 0. `check_windows_build.py`: 76/76 escalar e 76/76
  AVX2.
