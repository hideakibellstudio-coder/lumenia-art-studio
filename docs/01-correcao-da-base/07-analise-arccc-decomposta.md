# Análise ARCcC decomposta do Lumenia (2026-09-26)

> **Pergunta que este documento responde:** a base atual aguenta receber as
> features que um software de desenho precisa para competir, sem quebrar? Onde
> não aguenta, o que precisa ser solidificado antes, e em que ordem?
>
> **Base analisada:** `bd07511` (`main`). **Medido** no Linux do agente
> (4 núcleos, Python 3.11, Qt offscreen, motor compilado com g++ `-O2`,
> escalar). Os tempos absolutos no Windows do dono vão diferir; as proporções
> e o crescimento com o tamanho do canvas valem. O ARCcC-Navigator não existe
> neste ambiente: as medições vêm das catracas do repositório, de `coverage`,
> de `lizard` (complexidade de C++ e Python, instalado fora do repositório) e
> de scripts de medição da sessão (não versionados). Cada número tem o método
> no Apêndice A.
>
> Relacionados: `01-pendencias-atuais.md` (lista viva),
> `../02-arquitetura/01-framework-arccc.md` (o método de construção),
> `../05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md`
> (rotas de produto e Rota C comercial).

---

## Sumário

0. [Método: o ARCcC usado para analisar](#0-método-o-arccc-usado-para-analisar)
1. [Resumo executivo](#1-resumo-executivo)
2. [Nível 0 — o contrato que o mercado cobra](#2-nível-0--o-contrato-que-o-mercado-cobra)
3. [Nível 1 — pilares](#3-nível-1--pilares)
4. [Motor C++ nó a nó](#4-motor-c-nó-a-nó)
5. [Ponte PyBind11](#5-ponte-pybind11)
6. [Interface Python nó a nó](#6-interface-python-nó-a-nó)
7. [Recomposição: fluxos ponta a ponta](#7-recomposição-fluxos-ponta-a-ponta)
8. [Catálogo de defeitos e riscos](#8-catálogo-de-defeitos-e-riscos)
9. [Prontidão para features](#9-prontidão-para-features)
10. [Plano de solidificação](#10-plano-de-solidificação)
11. [O que preservar](#11-o-que-preservar)
- [Apêndice A — medições e comandos](#apêndice-a--medições-e-comandos)
- [Apêndice B — complexidade](#apêndice-b--complexidade)
- [Apêndice C — cobertura por pacote](#apêndice-c--cobertura-por-pacote)
- [Apêndice D — acoplamento e dívida medida](#apêndice-d--acoplamento-e-dívida-medida)
- [Apêndice E — documentação desatualizada](#apêndice-e--documentação-desatualizada)
- [Apêndice F — estudo externo do motor (avaliado em 2026-09-26)](#apêndice-f--estudo-externo-do-motor-avaliado-em-2026-09-26)

---

## 0. Método: o ARCcC usado para analisar

O ARCcC (*Atomic Recursive Componentization by Contract*) constrói o sistema
decompondo-o recursivamente em componentes atômicos ligados por contratos.
Aqui o mesmo movimento serve para **auditar**, em três passos.

**Passo 1 — decompor (descer).** Produto → pilar → camada → pacote → módulo.
Cada nó recebe a mesma ficha:

| Campo | Pergunta |
|---|---|
| Responsabilidade | Cabe numa frase sem "e"? Se precisa de "e", o nó tem duas. |
| Contrato | O que recebe, o que entrega, quem chama. É estreito e tipado, ou largo e descoberto em tempo de execução? |
| Dono do estado | Quem escreve cada dado? Quantos escritores? |
| Dependências | Medidas (`import`, `#include`), só para baixo? |
| Tamanho e complexidade | Linhas, complexidade ciclomática (CCN), parâmetros. |
| Testes | Cobertura e tipo de teste que protege o nó. |
| Invariantes e riscos | O que precisa ser sempre verdade, e o que já quebra. |
| Prontidão | Quando a próxima feature chegar aqui, o nó absorve ou quebra? |

**Passo 2 — recompor (subir).** Percorrer os fluxos que o usuário sente
(traço, tela, arquivo, desfazer, camadas, cor) atravessando os nós e medindo
cada etapa. Defeitos de contrato quase sempre aparecem nas **junções**, não
dentro dos nós. Por isso a recomposição acha coisas que a leitura nó a nó não
acha. Exemplo desta análise: a ponta borracha da caneta (Seção 8, D1).

**Passo 3 — confrontar com o contrato do mercado.** O nível 0 é o "contrato"
que um software de desenho competitivo precisa cumprir. Para cada cláusula
não cumprida: qual nó teria de mudar, e se ele está pronto para mudar.

**Veredito por nó:**

| Selo | Significado |
|---|---|
| 🟢 Sólido | Contrato claro, testado, sem dívida relevante. Preservar. |
| 🟡 Adequado | Funciona; dívida localizada, sem risco de espalhar. |
| 🟠 Frágil | Funciona hoje; a próxima feature que passar por aqui espalha custo ou quebra. |
| 🔴 Bloqueante | Impede competir ou arrisca o trabalho do usuário. |

---

## 1. Resumo executivo

**Veredito geral.** A *organização* do código está sólida: camadas sem ciclo
no motor e na interface, contratos explícitos na fronteira, catracas que não
deixam a dívida voltar, 81% de cobertura em `ui/` e 1015 testes. O que ainda
não está pronto para competir é o **teto técnico de três subsistemas
fundacionais**, que toda feature futura vai herdar:

1. **Exibição do canvas (🔴).** Em zoom de 100% ou mais, cada repintura copia
   o canvas **inteiro duas vezes**: do C++ para `bytes`, e de novo no
   `QImage.copy()`. Mesmo quando só 20 pixels mudaram. Custo medido da
   repintura: 7,2 ms em 1920×1080 e 34 ms em 3840×2160. Só a cópia custa
   ~114 ms em 6000×4000.
   - Em 4K a tela não acompanha 60 Hz; em 6000×4000 fica em ~9 quadros/s.
   - O traço em si é barato (0,07–0,24 ms por amostra da caneta, com o motor
     incluído).
   - É o gargalo número 1 do produto.
2. **Pixel fixo em RGBA de 8 bits (🟠 hoje, 🔴 para o futuro).** O tipo
   `ColorRGBA` mora em `engine/utils`, a camada mais baixa. Ele atravessa
   tile, composição, os 9 motores de pincel, seleção, histórico, ponte e
   arquivo. Cada feature escrita em cima dele aumenta o custo de chegar a
   16 bits.
3. **Arquivo síncrono (🔴).** Salvar um documento 4K com 10 camadas trava a
   interface por 4,1 s e sobe o pico de memória em +609 MB. Abrir o mesmo
   arquivo trava por 3,1 s. O salvamento automático repete o salvar a cada
   60 s, para cada documento alterado.

**Defeitos concretos achados agora (Seção 8), os dois mais graves:**
- **D1:** a ponta borracha da caneta liga o motor **Borrar** (id 6) em vez da
  **Borracha** (id 3). O teste da rodada anterior cravou o valor errado.
- **D2:** quando o motor não consegue criar o contexto de um documento (falta
  de memória num canvas grande), a falha é engolida. O documento anterior
  continua ativo no motor, e o que o usuário fizer no documento novo vai para
  o anterior.

Nenhum dos dois é consequência das regras: os dois são lugares onde elas não
foram seguidas. D1 é um número solto onde o ARCcC e a Lei do Rio nº 4 pedem um
enum tipado; D2 é uma falha que não chega a quem chamou, onde o contrato do
ARCcC pede que o erro seja devolvido. (As Leis do Rio detalham o ARCcC; não
concorrem com ele.)

**O que está sólido e deve ser preservado (Seção 11):**
- Motor em camadas com `#include` só para baixo.
- Histórico único para pixels e estrutura, com paginação em disco.
- Documento como fonte única, com guardas de projeção.
- Estado compartilhado com um escritor por assunto.
- Testes de caracterização de traço e composição.
- Conferência de Windows antes de cada commit.

**Plano (Seção 10), em cinco fases, nesta ordem:**

| Fase | Foco |
|---|---|
| **S0** | Corrigir os defeitos achados (pequenos, uma sessão). |
| **S1** | Desempenho que o usuário sente: exibição por região alterada, arquivo em segundo plano, salvamento automático que não trava. |
| **S2** | Contratos de extensão: núcleo comum de rasterização dos pincéis, descritor único de propriedade de camada, backend segregado, registros de ferramenta/filtro/formato. |
| **S3** | Decisão e preparação da profundidade de cor e de um só pipeline de cor. |
| **S4** | Distribuição comercial (já registrada como Rota C). |

Cada item tem critério de pronto medível. Nenhuma fase adiciona feature: ela
remove o obstáculo para a feature que vem depois.

---

## 2. Nível 0 — o contrato que o mercado cobra

Referências de mercado são conhecimento público dos produtos (Photoshop,
Clip Studio Paint, Krita, Procreate) e **não foram medidas nesta análise**.
A coluna "Lumenia hoje" foi verificada no código ou medida.

### 2.1 Traço e pincel

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Latência da caneta até a tela | Canvas na GPU (Krita/OpenGL, Procreate/Metal, Photoshop) | Motor rápido (0,07–0,24 ms por amostra); exibição copia o canvas inteiro a cada repintura | exibição | 🔴 |
| Variedade de motores | Muitos motores e pontas | 9 motores (pincel, lápis, nanquim, borracha, marcador, desfoque, borrar, aquarela, óleo) | `engine/core/engines` | 🟡 |
| Biblioteca do usuário | Salvar, importar e exportar pincéis (ABR, bundles do Krita, materiais do CSP, `.brush`/`.brushset` do Procreate) | 33 presets fixos no código Python, em 9 categorias. **Não há como salvar, importar ou exportar pincel** | `brush_plugin` | 🟠 |
| Curva de pressão | Por pincel e calibração global | Bézier de 4 pontos por dinâmica (tamanho, fluxo, velocidade) mais um expoente global. A curva vai direto ao motor, fora do `BrushState` (D5) | `curve_window`, `ui/core/state` | 🟡 |
| Estabilizador | Sim | Sim (`DynamicStabilizer`) | `core/stroke` | 🟢 |
| Inclinação e rotação da caneta | Sim | Chegam ao motor; sombreado por inclinação no lápis | `pointer_sample` → `core/brush` | 🟡 |

### 2.2 Tela

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Canvas grande fluido (8K+) | Sim | Diálogo limita a 16384 px; o custo de exibição cresce com a área inteira | exibição | 🔴 |
| Girar e espelhar a vista | Sim | Sim | viewport | 🟢 |
| Zoom afastado rápido | Sim | Sim: pirâmide de LOD (0,03–1 ms) | `MipmapPyramid` | 🟢 |

### 2.3 Camadas

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Modos de mesclagem | Photoshop tem 27 | 13 modos. Faltam, entre outros: Luz Suave/Forte/Linear, Cor, Matiz, Saturação, Luminosidade, Subtrair, Dividir, Escurecer Linear | `core/document/blending` | 🟠 |
| Máscara de camada (não destrutiva) | Photoshop, Krita, CSP | **Não existe** (há máscara de recorte e trava de alfa) | camada inteira | 🟠 |
| Grupos, recorte, trava de alfa, camada de ajuste | Sim | Sim; 7 tipos de filtro de ajuste | `core/document` | 🟢 |
| Camada vetorial, texto editável | CSP, Photoshop, Krita | Não: forma e texto viram pixels na hora | ferramentas | 🟠 |

### 2.4 Seleção e transformação

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Retângulo, elipse, laço, varinha, modificar | Sim | Sim | `core/selection` | 🟢 |
| Transformação livre e distorção | Sim | Sim. A prévia (Qt, bilinear) difere do resultado (motor, bicúbico) | transform | 🟡 |
| Dobrar/liquefazer, malha | Sim | Não | — | ⚪ feature |

### 2.5 Cor

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| ICC real, 16 bits por canal, prova de cores | Photoshop, Krita | ICC real (LittleCMS) só para perfil personalizado e prova. Os 14 perfis nativos são fórmulas aproximadas com nome de padrão. 8 bits por canal | `core/color` + `ui/core/color` | 🔴 para impressão, 🟡 para ilustração sRGB |

### 2.6 Arquivo

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| PSD (abrir e salvar) | Padrão de troca entre todos | **Não existe** | IO | 🔴 interoperabilidade |
| Formato nativo robusto | Sim | `.lmn` (zip + manifesto + RGBA por camada), validação ao gravar, `.bak`, migração de versão | `ui/core/document` | 🟢 correção, 🔴 desempenho |
| Salvamento automático sem travar | Sim | Trava (4 s por documento 4K/10 camadas, a cada 60 s) | `recovery_controller` | 🔴 |
| Exportar | Muitos formatos | PNG e JPEG com ICC | `image_actions` | 🟡 |

### 2.7 Fluxo de trabalho

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Painel de histórico | Sim | Não; o motor já expõe ids e descrição dos passos | — | ⚪ quase pronto |
| Imagem de referência | Sim | Não | — | ⚪ feature |
| Ferramenta degradê | Sim | Não | — | ⚪ feature |
| Animação | CSP, Krita, Procreate | Não | — | ⚪ decisão de produto |
| Atalhos configuráveis | Sim | Sim | `shortcut_registry` | 🟢 |
| Idiomas | Vários | 4 idiomas, 1020 chaves, 0 faltando | `i18n` | 🟢 |

### 2.8 Extensibilidade, distribuição e plataforma

| Cláusula | Mercado | Lumenia hoje | Nó | Selo |
|---|---|---|---|---|
| Plugins e scripts | Krita (Python), Photoshop (UXP) | Só painéis de interface. Tipos BRUSH/FILTER/TOOL/IO declarados, sem ponto de extensão. O plugin recebe a janela principal e o backend inteiro | `ui/core/plugins` | 🟠 |
| Instalador assinado e atualização | Sim | Instalador Inno + portátil; sem assinatura (aviso do SmartScreen) e sem atualização automática | `scripts` | 🔴 comercial |
| Plataformas | Windows/macOS (Krita também Linux; Procreate só iPad) | Só Windows | — | ⚪ decisão |

**Leitura do nível 0.** As cláusulas vermelhas se dividem em dois grupos:
- **Fundação:** exibição, arquivo síncrono, cor aproximada. Afetam tudo o que
  vier depois, então vêm primeiro.
- **Feature que depende de fundação:** PSD (precisa do registro de formatos
  e da leitura em lote), 16 bits, máscara de camada.

---

## 3. Nível 1 — pilares

Linhas contadas em arquivos rastreados pelo git (`.py`, `.cpp`, `.hpp`, `.pyi`).

| Pilar | Arquivos | Linhas | Camadas internas | Testes que o protegem | Selo |
|---|---:|---:|---|---|---|
| `engine/` (C++20) | 151 | 17.565 | `utils` 219 · `infrastructure` 721 · `core` 12.641 · `boundary` 3.984 | Pela ponte (pytest), caracterização de traço e composição, injeção de falhas no histórico (`tests/native/`) | 🟡 |
| `bridge/` (PyBind11) | 10 | 1.438 (inclui `.pyi` de 573) | `infrastructure` → `core` → `boundary` | `.pyi` × binário, política de erros | 🟡 |
| `ui/` (Python/PySide6) | 355 | 46.427 | `infrastructure` 4.886 · `core` 20.760 · `boundary` 1.525 · `plugins` 19.255 | 81% de cobertura (27.276 comandos) | 🟡 |
| `tests/` | 139 | 18.466 | 692 funções de teste, 1015 casos coletados, 63 arquivos com o motor real | — | 🟢 |
| `scripts/`, `benchmarks/` | 10 | 1.434 | build nativo, portátil, instalador, conferência de Windows, pre-commit, soak | `test_pre_commit_hook`, contratos de build | 🟢 |

**Leituras do nível 1:**
- **Proporção de código:** a interface tem 2,6× mais código que o motor.
  Esperado para um app Qt com muitos diálogos. Mas 19,3 mil linhas estão em
  plugins, e 9,6 mil delas num único plugin, o `workspace_core`. Na prática
  ele é o coração da aplicação (canvas, docas, barras), e o sistema de
  plugins é quase só um mecanismo de montagem da casca.
- **Testes do C++:** o motor não tem framework de teste próprio (gtest,
  Catch2). Tudo é testado por Python através da ponte. Isso é bom para o
  contrato público. Deixa sem proteção direta o que não é exposto (o miolo
  dos motores de pincel, por exemplo), e é por isso que a caracterização por
  imagem (`tests/golden/`) é tão importante.
- **Documentação:** 118 READMEs, um por pasta, com dependências medidas.

---

## 4. Motor C++ nó a nó

### 4.1 `engine/utils` (5 headers, 219 linhas) — 🟢 código, 🟠 decisão

- **Responsabilidade:** tipos de valor (`ColorRGBA`, `Point2D`, `Rect2D`,
  `Dab`, `MathUtils`).
- **Contrato:** só headers, sem dependências.
- **Achado:** o comentário de `ColorRGBA.hpp` diz a verdade: *"Cor RGBA8
  (sRGB, alfa reto): o tipo de pixel do motor inteiro"*. Estando no nível mais
  baixo, tudo o que existe acima depende dessa escolha. Ela amarra a
  profundidade de cor (Seção 10, S3).

### 4.2 `engine/infrastructure` (5 arquivos, 721 linhas) — 🟡

| Módulo | O que faz | Achado |
|---|---|---|
| `compression/Lz4Codec` (265) | LZ4 próprio para tiles e histórico | `compressBlock` CCN 34, `decompressBlock` 22. A compressão de camadas inativas (`compress_inactive_layers`) está na ponte, mas **nada na interface chama** (D8). Com 100 camadas cheias em 4K, são ~3,3 GB sem compressão. |
| `storage/ScratchDiskManager` (235) | Paginação do histórico em disco | 🟢 |
| `telemetry/EngineTelemetry` (221) | Tempo por estágio do traço (cinemática, interpolação, dab, desfazer, composição) | 🟢 Instrumento certo para as metas da Seção 10. |

### 4.3 `engine/core/math` (16 arquivos, 1.663 linhas) — 🟡

- **Responsabilidade:** geometria das guias (régua reta e curva, 1P/2P/3P,
  isométrica, curvilínea), simetria (espelho, espelho duplo, radial), snap,
  Bézier, transformação da viewport.
- **Complexidade:** `CurvilinearSnapEngine::snap` CCN 24,
  `GuideSnapEngine::snapPerspective` 17.
- **Achados:**
  - **Lei do Rio 2:** `canvas/math/camera_3d_projector.py` refaz em Python
    `rotate3DBackward`, `curveFromNormal` e `curvilinearCameraRadius`, que
    este módulo já tem (pendência 14).
  - A facade expõe componentes de snap "fase D0" (`estimateTrajectory`,
    `stepSnapLock`) só para teste. É superfície pública que existe por
    conveniência de teste.

### 4.4 `engine/core/stroke` (5 arquivos, 363 linhas) — 🟢

`PointerEvent`, `VelocityTracker`, `DynamicStabilizer`. Pequeno, uma
responsabilidade, sem achado.

### 4.5 `engine/core/brush` (4 arquivos, 406 linhas) — 🟠

- **Responsabilidade:** o perfil do pincel e a dinâmica (pressão, velocidade,
  jitter).
- **Achado de forma:** `BrushProfile` é uma struct única com os parâmetros de
  **todos** os motores (grafite, nanquim, marcador, desfoque, borrar,
  aquarela, óleo) mais os comuns: ~70 campos.
- **Custo de adicionar um motor hoje:** um bloco na struct comum, `def_readwrite`
  campo a campo na ponte (é por isso que `bind_math_brush.cpp` tem 141
  bindings), o `.pyi`, o dicionário do perfil em Python, os presets, os grupos
  de parâmetros do painel avançado e as traduções.
- **Complexidade:** `DynamicMapper::applyJitter` CCN 23.

### 4.6 `engine/core/engines` (17 arquivos, 2.235 linhas) — 🟠 (o nó que mais vai receber feature)

- **Contrato:** bom. `IBrushEngine` (`renderDab` + ganchos de ativação e
  início/fim de traço) e uma fábrica única (`BrushEngineFactory`).
- **Tipos:** o tipo 0 (pincel básico) não passa pela fábrica: usa o
  `DabRenderer` direto.
- **Achado principal — duplicação estrutural.** Cada um dos 8 motores
  reimplementa, dentro do próprio `renderDab`:
  - o recorte de tiles pela caixa do dab;
  - a geometria da pegada (ângulo, aspecto, dureza, borda);
  - a trava de alfa;
  - a máscara de seleção.

  Medido com `lizard`:

  | `renderDab` | Linhas (NLOC) | CCN |
  |---|---:|---:|
  | Pencil | 188 | 44 |
  | Blur | 178 | 38 |
  | Eraser | 137 | 34 |
  | Inker | 152 | 33 |
  | Marker | 170 | 33 |
  | Smudge | 170 | 31 |
  | Oil | 152 | 30 |
  | Watercolor | 156 | 25 |
  | `DabRenderer::renderDab` | 273 | 71 |

- **Consequência:**
  - Corrigir um detalhe de máscara ou de trava de alfa exige 9 edições.
  - Um motor novo nasce copiando ~150 linhas.
  - Dar a todos os motores algo transversal (textura por dab, pincel duplo,
    dinâmica de cor, 16 bits) multiplica o trabalho por 9.
- **ARCcC:** viola a atomicidade (cada `renderDab` tem 4 responsabilidades) e
  a recursividade (o componente comum não foi extraído).

### 4.7 `engine/core/raster` (17 arquivos, 2.214 linhas) — 🟠

- **Responsabilidade:** interpolação de dabs, dab padrão, balde, transformação
  livre e distorção, otimização de pincel grande, blend SIMD.
- **Complexidade concentrada:**
  - `FloodFill::execute`: 221 linhas, CCN 80, 12 parâmetros (a função mais
    complexa do motor).
  - `DabRenderer::renderDab`: CCN 71.
  - `TransformEngine::beginTransform`: CCN 41.
  - `DabInterpolator::interpolateSpline`: CCN 21.
- **SIMD:** `SimdSpanBlender` tem caminho AVX2, mas o build distribuído é
  escalar. Não há escolha em tempo de execução (Seção 10, S1.4).

### 4.8 `engine/core/canvas` (10 arquivos, 855 linhas) — 🟡

- **Responsabilidade:** `PixelBuffer` (RGBA8 em `std::vector`), `Tile` de
  128×128 (64 KB) com copy-on-write e compressão, `TileGrid` esparsa,
  `SpatialCuller`, `MipmapPyramid` (LOD).
- **Achado técnico:** `PixelBuffer` calcula `width * height * 4` em `int` e só
  depois converte para `size_t`. Acima de 23170×23170 a conta estoura. Hoje os
  caminhos da interface barram antes (D13), mas o motor não se protege
  sozinho.

### 4.9 `engine/core/document` (20 arquivos, 2.432 linhas) — 🟡

- **Responsabilidade:** pilha de camadas, camada, grupo, camada de filtro,
  composição, mesclagem, filtros, mesclar/achatar.
- **Composição:** por região suja, com OpenMP (17 `#pragma omp` no motor,
  11 deles na composição e nos filtros).
  - Opções de gama linear e "deep color": acumula em `double`, mas armazena
    em 8 bits.
  - `blendPixel`: 132 linhas, CCN 32. `LayerMerger::flattenGroup`: CCN 32.
- **Escala com camadas:** durante o traço, cada segmento recompõe **todas** as
  camadas da região suja. Não há cache das camadas abaixo e acima da ativa.
  - Camadas esparsas: 0,15 → 0,27 ms por amostra, de 1 para 100 camadas.
  - Com 20 camadas sobrepondo o traço: 67–74 ms por traço de 120 amostras
    (contra 28 ms com uma camada).
  - Cresce com o número de camadas **com conteúdo sob o pincel**.
- **Modos:** 13 modos de mesclagem e 7 filtros (matiz/saturação,
  brilho/contraste, desfoque gaussiano, balanço de cores, nitidez+vinheta,
  inversão+limiar, pixelizar).

### 4.10 `engine/core/selection` (6 arquivos, 1.198 linhas) — 🟡

- **Responsabilidade:** máscara de 8 bits por pixel, varinha, formas com
  anti-alias por cobertura, morfologia (expandir, contrair, suavizar),
  contornos.
- **Complexidade:** `generateWandMask` CCN 67; `getContourLoops` CCN 23.

### 4.11 `engine/core/history` (3 arquivos, 485 linhas) — 🟢

- **Responsabilidade:** `TileUndoManager`. Passos de pixel (tile antes/depois,
  comprimido, paginável em disco) e passos estruturais (cópia copy-on-write da
  pilha de camadas + seleção) na **mesma linha do tempo**.
- **Limites:** 50 passos e 512 MB (padrão aplicado pela ponte; o construtor
  do motor tem 256 MB).
- **Complexidade:** `moveStep` CCN 30.
- **Testes:** protegido por injeção de falhas (`tests/native/history_faults.cpp`).
  Um dos nós mais maduros do sistema.

### 4.12 `engine/core/color` (4 arquivos, 528 linhas) — 🔴 para cor exata

- **Responsabilidade:** 14 perfis "nativos" (sRGB, Display P3, Adobe RGB,
  Rec. 2020, 4 CMYK, 3 simulações de daltonismo, acromatopsia, sRGB linear,
  ACEScg).
- **Achado:** são **fórmulas aproximadas com nome de padrão**. Rec. 2020 é
  `pow(c, 0.9) · 1.05`; os CMYK são uma simulação com ganho de ponto; sRGB
  linear é `pow(c, 2.2)`.
- **Impacto:** para quem pinta em sRGB e exporta PNG, não aparece. Para quem
  confia em "FOGRA39" ou "Adobe RGB (1998)" para impressão, o nome promete
  uma conversão que o código não faz. Regra do benchmark: *a interface não
  promete o que o motor não faz*.
- Ver também o pipeline duplo (7.7).

### 4.13 `engine/core/texture` (4 arquivos, 262 linhas) — 🟢

Texturas procedurais de forma, altura e grão.

### 4.14 `engine/boundary/orchestrator` (29 arquivos, 3.019 linhas) — 🟡

- **Desenho:** bom. Orquestradores por assunto (traço, seleção, balde,
  transformação, pilha de camadas, memória, colagem, exportação, snap, estado
  do documento). O `DocumentContext` agrega "o que uma operação de documento
  toca" e faz de "o documento mudou" um método, não uma disciplina.
- **Funções longas com muitos parâmetros:**
  - `StrokeOrchestrator::updateStrokeRaw`: 184 linhas, CCN 39.
  - `renderDabsPipeline`: CCN 26, **17 parâmetros**.
  - `BufferPasteOrchestrator::paste`: CCN 31, 15 parâmetros.
  - `endStrokeRaw`: CCN 26.
- **Leitura:** muitos parâmetros é sinal de contexto que ainda não virou
  tipo, como o `DocumentContext` virou.

### 4.15 `engine/boundary/public-api` (6 arquivos, 965 linhas) — 🟡

- **`PaintEngineFacade`:** um objeto por documento, ~150 métodos públicos.
- **Dois contratos misturados:**
  - A API de operações: `addLayer`, `floodFill`, `commitTransform`...
    Estreita por operação. Bom.
  - Acesso direto ao estado interno por referência mutável:
    `getLayerStack()`, `getBrushProfile()`, `getSelectionMask()`,
    `getStabilizer()`, `getCanvasTexture()`. A ponte usa isso para expor o
    perfil campo a campo. É vazamento de encapsulamento: qualquer mudança
    interna vira mudança de contrato.
- **Memória fixa por documento:** `m_outputBuffer` e `m_displayBuffer` são dois
  buffers de tela cheia (2 × 33 MB em 4K; 2 × 1 GB em 16384²), mais mipmaps e
  a máscara de seleção.

---

## 5. Ponte PyBind11

**Tamanho:** 1.438 linhas (865 de C++, 573 de `.pyi`). 333 entradas de
binding em 5 arquivos: `bind_math_brush` 141, `bind_stroke` 57, `bind_tools`
54, `bind_layers` 42, `bind_canvas` 39. O `.pyi` tem 165 métodos.

| Aspecto | Estado | Selo |
|---|---|---|
| Camadas internas | `infrastructure` (buffers, política de erros) → `core` (bindings) → `boundary` (`.pyi`), verificadas por teste | 🟢 |
| Contrato tipado | `.pyi` comparado com o binário em teste | 🟢 |
| Erros | Motor só lança `std::invalid_argument`, que vira `ValueError`; política escrita | 🟢 |
| **GIL** | Liberado em **1** lugar (`render_stroke_preview`). Salvar em segundo plano, compor em outra thread ou gerar miniaturas sem travar dependem disso nas operações longas | 🟠 |
| **Buffers** | Todo pixel sai como `py::bytes`, que é uma cópia. Não há visão sem cópia (buffer protocol/`memoryview`) para a tela nem para salvar | 🔴 (metade do problema da exibição e do pico de memória ao salvar) |
| Perfil do pincel | Exposto campo a campo (`def_readwrite`) | 🟠 |

---

## 6. Interface Python nó a nó

### 6.1 `ui/infrastructure` (40 arquivos, 4.886 linhas)

| Módulo | Linhas | Cobertura | Selo | Achados |
|---|---:|---:|---|---|
| `bridge_client` | 2.468 | 81% | 🟡 | `AladynBackend` = base + 10 mixins sobre `AladynBackendBase` (estado declarado na base). Ver a lista abaixo da tabela. |
| `config` | 389 | 89% | 🟢 | JSON com esquema e migração. |
| `i18n` | 214 | 83% | 🟢 | 1020 chaves × 4 idiomas, 0 faltando. Sem preferência salva, segue o idioma do sistema. |
| `theme` | 835 | 86% | 🟡 | Ainda 147 cores fixas em 40 arquivos (catraca). |
| `logging` | 281 | **28%** | 🟠 | Registro de queda nativa (faulthandler) e logger. Cobertura mais baixa do projeto num módulo que só age quando algo já deu errado. |
| `icons`, `accessibility`, `app_info`, `runtime_paths` | 698 | 52–100% | 🟢 | 66 controles com nome acessível na janela principal. |

**Achados no `bridge_client`:**
1. **Histórico-sombra:** `_action_stack` e `_redo_stack` são escritos a cada
   traço e nunca lidos (D7). `_is_filling` nunca vira `True`.
2. **Descoberta em caminho quente:** `native_has(...)` (um `getattr`) a cada
   repintura em `get_display_pixel_buffer`.
3. **Segunda cópia do canvas:** `get_qimage` faz `QImage(...).copy()` (7.1).
4. **Cor com dois caminhos:** motor para os perfis 0–13, LittleCMS (Pillow)
   para ≥ 100 e para a prova de cores. A reserva é um caminho fixo do Windows
   (`C:\Windows\System32\spool\drivers\color\RSWOP.icm`) (7.7).

### 6.2 `ui/core/engine` — o contrato da interface com o motor (1.531 linhas, 93%) — 🟠

- **`EngineBackend`:** 176 métodos numa classe abstrata só.
- **Sub-protocolos:** existem 11 declarados (`CoreLifecycle`, `Stroke`,
  `Brush`, `CanvasResource`, `Layer`, `Geometry`, `Telemetry`, `Color`,
  `RenderPipeline`, `History`, `SelectionTransform`). Mas todo consumidor
  recebe o backend inteiro por `EngineRegistry.instance().get_backend()`.
- **Uso medido fora da ponte (métodos distintos por pacote):**

  | Pacote | Métodos distintos |
  |---|---:|
  | `ui/core/document` | 57 |
  | `workspace_core` | 45 |
  | `ui/core/dialogs` | 24 |
  | `ui/boundary` | 20 |
  | `ui/core/state` | 13 |
  | `brush_plugin` | 11 |
  | `layers_plugin` | 10 |

  Até 34 métodos não têm chamador fora da ponte (heurística por nome;
  confirmar antes de remover).
- **Por que é 🟠:** é a interface mais larga do sistema. Qualquer segunda
  implementação (motor em processo separado, motor de teste, caminho de GPU)
  teria de cumprir 176 métodos. Nenhum consumidor declara quais usa.

### 6.3 `ui/core/document` (16 arquivos, 2.520 linhas, 88%) — 🟡 correção, 🔴 desempenho de arquivo

- **Responsabilidade:** documento como fonte única. Inclui a pilha de camadas
  (`LocalLayerManager`) e o `history.transaction`, que põe pixel e metadado
  num passo só. Mais o formato `.lmn` com esquema e migração, a restauração e
  a recuperação.

**Achados:**
1. **Projeção dupla.** A árvore de camadas existe em Python (fonte da verdade)
   e no motor (projeção), com guardas (`assert_projection`,
   `bind_projection_identities`). Funciona. O custo aparece em cada
   propriedade nova: a máscara de recorte atravessa **26 arquivos em 11
   pastas**; a trava de alfa, **43 arquivos em 15 pastas**. Não há um
   descritor único de propriedade de camada.
2. **Descoberta no caminho do arquivo.** O serializador é o arquivo com mais
   `getattr`/`hasattr` sobre o motor (14 + 3). Justamente no caminho que grava
   o trabalho do usuário, o contrato é descoberto, não garantido.
3. **Complexidade no caminho do arquivo:** `save` CCN 27; `read`,
   `_validate_manifest` e `validate_auxiliary` CCN 31 cada;
   `restore_document` 24 (todos com `noqa` registrado).
4. **Salvar é síncrono e de tela cheia:**
   - Cada camada vira um buffer do tamanho do canvas; tiles vazios não são
     omitidos.
   - Todos os buffers ficam em memória até o zip terminar.
   - Depois de gravar, o arquivo é relido para validar.

   Medido (valores na Seção 7.3):

   | Documento (10 camadas) | Salvar | Pico de memória | Arquivo |
   |---|---:|---:|---:|
   | 1920×1080 | 1,14 s | +169 MB | 0,4 MB |
   | 3840×2160 | 4,07 s | +609 MB | 0,6 MB |

   O arquivo é pequeno porque os traços do teste são esparsos.
5. **Dívida registrada:** `layer_backend_sync` avisa o canvas por atalho
   global (`canvas_access`).

### 6.4 `ui/core/state` (7 arquivos, 676 linhas, 100%) — 🟢

`BrushState`, `ToolState`, `GeometryState`, as regras entre estados num lugar
só (`state_links`) e um escritor por assunto no motor (`BrushEngineSync`,
`ToolEngineSync`).

**Furo (D5):** as curvas Bézier da janela "Perfis & Curvas LUT" não passam por
aqui. `curve_window.sync_to_engine` escreve direto no perfil do motor. Há dois
escritores da dinâmica do pincel, e a curva não é salva com o pincel.

### 6.5 `ui/core/plugins` (13 arquivos, 1.370 linhas, 77%) — 🟠

**Bom:** descoberta, dependências, ativação transacional, instalador com
manifesto sha256 e `minimum_api_version`.

**Achados:**
1. `PluginType` declara BRUSH, FILTER, TOOL e IO. **Zero** usos: nenhum
   desses tipos tem ponto de extensão (D9).
2. O `PluginContext` entrega `main_window` e o backend inteiro. Um plugin de
   terceiro teria acesso a tudo, sem contrato estreito.
3. Plugin é código Python sem isolamento: instalar é executar código com os
   privilégios do usuário. Para uma loja de plugins, precisa de política de
   confiança (assinatura, aviso).

### 6.6 Telas, diálogos, widgets e componentes (13,2 mil linhas) — 🟡

| Pacote | Linhas | Cobertura |
|---|---:|---:|
| `screens` | 5.141 | 84% |
| `dialogs` | 3.698 | 86% |
| `widgets` | 2.715 | 71% |
| `components` | 1.681 | 90% |

Pontos fracos de cobertura: `splash_screen` 0%, `filter_edit_popup` 14%,
`shape_dropdown` 37%, `step_button` 37%, `color_wheel` 49%.

### 6.7 `ui/core/tools.py` e `tool_settings.py` — 🟠

Ferramentas são um dicionário fixo (17 entradas) com despacho por string no
roteador de entrada. Adicionar uma ferramenta hoje toca:
- `TOOL_META`;
- os padrões e validadores em `tool_settings`;
- `input_router` e `ToolManager`;
- a view de opções;
- ícone e tradução.

Não há registro de ferramentas.

### 6.8 `ui/boundary/orchestrator` (12 arquivos, 1.524 linhas, 66%) — 🟠

- `MainWindow` e as ações (documento, edição, imagem, diálogos, recuperação).
- `document_actions` (novo, abrir, salvar, exportar) tem **37%** de cobertura.
  O caminho do arquivo do usuário é o menos testado da casca.
- Abrir imagem acima de ~8192×8192 falha no decodificador do Qt (limite de
  256 MB) com a mensagem "Não foi possível ler a imagem", enganosa para um
  arquivo válido (D13).
- A recuperação salva a cada 60 s, de forma síncrona.

### 6.9 `ui/plugins` (144 arquivos, 19.255 linhas)

**`workspace_core` — 9.577 linhas, 80% (🟡):**

| Subpasta | Linhas |
|---|---:|
| `canvas/tools` | 2.018 |
| `workspace` (raiz) | 1.870 |
| `canvas/viewport` | 1.350 |
| `dock` | 1.286 |
| `secondary_tool_bar` + `views` | 1.122 |
| `canvas/renderers` | 992 |
| `canvas` (raiz) | 402 |
| `canvas/math` | 369 |

O `RenderWidget` tem 399 linhas.

Achados:
1. `viewport_renderer` pede o canvas inteiro a cada repintura em zoom ≥ 1
   (7.1). Em zoom < 1 usa LOD e custa 0,3–3,4 ms. Esse caminho é bom.
2. **Forma e texto** são rasterizados com `QPainter` num `QImage` do tamanho
   do canvas inteiro a cada confirmação (96 MB em 6000×4000). Não usam o
   pincel e não são editáveis depois (D12).
3. **Transformação:** prévia bilinear do Qt, resultado bicúbico do motor
   (D11).
4. **Ponta borracha:** o roteador liga o motor 6 (D1).

**Painéis:**

| Painel | Linhas | Cobertura | Pontos a notar |
|---|---:|---:|---|
| `brush_plugin` | 2.816 | 69% | Presets fixos em código; `engine_params_widget` 32%; `brush_selector_popup` 16% |
| `layers_plugin` | 2.660 | 67% | `view` 30%; `filter_layer_flow` 34% |
| `recording_plugin` | 1.674 | 87% | Traduzido nesta rodada |
| `geometry_plugin` | 1.309 | 93% | — |
| `navigator_plugin` | 580 | 74% | — |
| `telemetry_plugin` | 507 | 85% | — |
| `color_plugin` | 109 | 88% | — |

---

## 7. Recomposição: fluxos ponta a ponta

### 7.1 Traço: da caneta ao pixel na tela

| # | Etapa | Onde | Custo medido |
|---|---|---|---|
| 1 | `QTabletEvent` → `PointerSample` (pressão, inclinação, rotação, ponta borracha) | `render_widget.tabletEvent`, `pointer_sample.py` | — |
| 2 | Roteador → pipeline do traço → `backend.paint_stroke` | `input_router`, `canvas_stroke_pipeline`, `aladyn_stroke_mixin` | Etapas 2–5 juntas, por amostra: **0,068 ms (p50) / 0,163 ms (p95)** em 1080p; **0,241 / 0,626 ms** em 4K |
| 3 | `update_stroke_raw` → velocidade, estabilizador, dinâmica (mapeador + curvas), simetria e snap | `StrokeOrchestrator::updateStrokeRaw` | (incluído acima) |
| 4 | Interpolação (spline) → registro do tile para desfazer → `renderDab` do motor ativo | `renderDabsPipeline`, `engines/*` | (incluído acima) |
| 5 | Recomposição da região suja com todas as camadas → `outputBuffer` | `Compositor::compositeRegion` | Cresce com camadas sob o pincel (4.9) |
| 6 | `update(rect)` → `paintEvent` → `ViewportRenderer.render` | viewport | — |
| 7 | **Zoom < 1:** LOD pré-filtrado | `get_qimage_lod` → `MipmapPyramid` (hoje `get_display_image` → `get_display_lod_region`, ver D4/D18) | 0,03 / 0,33 / 1,04 ms (1080p / 4K / 6000×4000), pirâmide limpa; sujo: 2,6 / 10,3 / 12,9 ms |
| 7′ | **Zoom ≥ 1:** canvas inteiro: C++ → `py::bytes` (cópia 1) → `QImage.copy()` (cópia 2) | `bind_canvas` + `aladyn.get_qimage` | **5,9 / 34,6 / 114 ms** (1080p / 4K / 6000×4000) |
| 8 | `drawImage` só da região suja | viewport | Repintura inteira em zoom 100%: **7,2 ms** (1080p), **34,4 ms** (4K). Com o documento inteiro na tela: 0,34 / 3,38 ms |

**Leitura.** Em zoom ≥ 100% num documento 4K, mais de 95% do custo da
repintura está na etapa 7′, que não depende do que mudou.
- **Contrato atual:** "me dê o canvas inteiro".
- **Contrato necessário:** "me dê o retângulo que mudou" (ou "atualize estes
  tiles").
- Esse contrato serve ao desenho por CPU agora e a uma textura de GPU depois
  (Seção 10, S1.1).

### 7.2 Exibição e zoom

- Zoom afastado é resolvido pela pirâmide de LOD: 🟢.
- Zoom de trabalho (≥ 100%), que é onde o artista passa a maior parte do
  tempo em detalhe, é o caminho lento: 🔴.
- Troca de documento reaplica ~46 propriedades do pincel na facade do
  documento de destino. É correto (evita perder ajustes) e barato.

### 7.3 Arquivo: salvar, abrir, salvamento automático, importar

**Salvar (`DocumentSerializer.save`)**, tudo na thread da interface:
1. Confere a projeção.
2. Para cada camada, pega o buffer de tela cheia (cópia).
3. Junta todos os buffers num dicionário.
4. Comprime em zip num arquivo temporário.
5. Relê o arquivo para validar.
6. `fsync`, `.bak` e troca atômica.

| Tamanho (10 camadas) | Salvar | Pico de memória |
|---|---:|---:|
| 1920×1080 | 1,14 s | +169 MB |
| 3840×2160 | 4,07 s | +609 MB |

**Abrir `.lmn`** (4K, 10 camadas): 0,41 s para ler e validar, mais 2,64 s para
restaurar no motor. A restauração cola cada camada e depois **relê e compara**
o buffer inteiro, pixel a pixel. Também tudo na thread da interface.

**Salvamento automático** (`recovery_controller`), a cada 60 s:
- Para **cada** documento alterado, em série: troca o contexto do motor e
  chama o mesmo `save` completo, na thread da interface.
- Pula quando o canvas está ocupado (traço em andamento).
- Com um documento 4K/10 camadas: ~4 s de travamento por minuto de trabalho.
  Com três documentos abertos, ~12 s.

**Importar imagem:**
- PNG, JPEG, BMP e WebP viram um documento de uma camada.
- Sem validação própria de tamanho. Quem barra é o decodificador do Qt (limite
  de 256 MB, ~8192×8192), com uma mensagem que culpa o arquivo (D13).

**Exportar:** PNG e JPEG com ICC embutido.

**Selo do fluxo:** 🟢 correção (validação, `.bak`, migração, recuperação), 🔴
desempenho e travamento.

### 7.4 Desfazer

Uma linha do tempo só:
- a transação de camadas em Python (`layer_transaction`);
- o `TileUndoManager` no C++;
- identidades de camada vinculadas por uid.

Um par desfazer+refazer com 20 camadas custa 42 / 73 / 105 ms (1080p / 4K /
6000×4000). Passos estruturais copiam a pilha com copy-on-write. 🟢.
Único resto: o histórico-sombra morto na ponte (D7).

### 7.5 Camadas

Caminho: comando → `LayerCommands` (`layer_transaction`) → `LocalLayerManager`
→ `layer_backend_sync` → backend → facade → `LayerStackOrchestrator`.

- Mudar a opacidade de uma camada com 20 camadas: 15,6–17,4 ms. O motor
  limita a recomposição à área pintada da camada (`LayerDirtyRegion`).
- **Custo estrutural:** propriedade nova de camada = 26–43 arquivos (6.3).

### 7.6 Seleção e transformação

- **Seleção:** motor (máscara de 8 bits) → contornos → formigas desenhadas na
  interface. 🟢
- **Transformação:**
  - O motor extrai a origem.
  - A interface desenha a prévia com `QTransform` (bilinear).
  - A confirmação usa o amostrador do motor (bicúbico por padrão).

  Resultado confirmado pode diferir levemente da prévia (D11). 🟡

### 7.7 Cor: dois pipelines

```
Perfis nativos 0–13 ──► C++ ColorProfileManager (fórmulas aproximadas) ──► tela / exportação
Perfis ICC ≥ 100    ──► Python cms_engine → Pillow ImageCms (LittleCMS) ──► tela / exportação
Prova de cores      ──► LittleCMS; sem perfil de prova → RSWOP.icm do Windows, senão volta ao C++
```

- Dois caminhos que convertem cor, com matemáticas diferentes, escolhidos pelo
  número do perfil.
- É o padrão que a Lei do Rio nº 2 proíbe: algoritmo duplicado, com as duas
  versões divergindo.
- Cobertura: `cms_engine` 44%; cor na ponte 52%.
- 🔴 para quem depende de cor exata.

### 7.8 Idioma, tema e acessibilidade

- **Idioma:** 1020 chaves nos 4 idiomas, 0 faltando. A suíte roda em pt_BR em
  qualquer sistema. 🟢
- **Tema:** 147 cores fixas em 40 arquivos. A catraca impede aumentar. 🟡
- **Acessibilidade:** 66 controles com nome na janela principal. Ainda sem
  nome: os −/+ dos `CompactSlider` (22), a barra flutuante (12), as amostras
  de cores recentes (10) e 9 deslizantes. 🟡

### 7.9 Plugins

Ativação: descoberta → dependências → ativação transacional → `add_panel` no
workspace.
- Plugin de terceiro recebe a janela e o backend inteiros (6.5).
- Painéis `navigator` e `layers` têm contrato declarado e conferido
  (`PANEL_CONTRACTS`).
- 🟠 para terceiros, 🟢 para os embutidos.

### 7.10 Qualidade e entrega

**Testes:**
- 1015 casos coletados (1010 passam, 5 pulados no Linux); 692 funções de
  teste; 63 arquivos com o motor real.
- Caracterização por imagem de traço e composição (`tests/golden/`).
- Cobertura de `ui/`: 81%.

**Catracas:**
- acoplamento: `hasattr` 62, `getattr` literal 62, acesso privado alheio 15,
  `except` silencioso 0, import reverso 0;
- cores fixas: 147;
- idioma dos identificadores;
- documentação por pasta (118 READMEs);
- camadas do C++;
- teto de linhas (0 arquivos na parede);
- lint (0 achados).

**Antes do commit:** gancho de pre-commit (~13 s) e, se o motor mudou,
compilação para Windows com MinGW (69/69 arquivos, `-Werror`).

**Build e distribuição:**
- CI (5 jobs Windows) só à mão.
- Portátil com Nuitka e instalador Inno Setup.
- Sem assinatura de código, sem atualização automática, só Windows.

**Selos:** 🟢 qualidade, 🔴 distribuição comercial.

---

## 8. Catálogo de defeitos e riscos

### 8.1 Defeitos (comportamento errado hoje)

| Id | Defeito | Evidência | Severidade | Raiz ARCcC | Correção |
|---|---|---|---|---|---|
| **D1** ✅ | (corrigido em 2026-10-01: S0.1) A ponta borracha da caneta liga o **Borrar** (Smudge, 6) em vez da **Borracha** (3). O teste `test_eraser_tip_switches_the_engine_only_during_the_stroke` cravou o 6. | `input_router.py:192` com o comentário "EngineType::Eraser" ao lado do 6; `BrushProfile.hpp`: `Eraser = 3`, `Smudge = 6` | **Alta** (uso diário com caneta) | Lei do Rio 4: tipo de motor sem enum em Python; presets e roteador usam números soltos | Enum `EngineType` canônico em `ui/core` espelhando o C++; roteador e presets usam o enum; teste corrigido |
| **D2** ✅ | (corrigido em 2026-10-01: S0.2) Se o motor não cria o contexto de um documento, a falha é engolida: o contexto ativo **continua sendo o documento anterior**, e traços e colagens do documento novo vão para ele. `DocumentViewSync.show_document` não confere o resultado (a troca de geometria confere). | Verificado na ponte: `set_active_document_context("gigante", 30000, 30000)` deixa `"pequeno"` ativo. Pela interface, as dimensões são barradas antes (D13), mas falta de memória num 16384² (dois buffers de 1 GB) cai no mesmo caminho | **Média-alta** (latente; escreve no documento errado) | Falha de contrato engolida (log e segue) | A criação de contexto devolve erro; `show_document` recusa mostrar o documento e avisa o usuário; teste com falha simulada |
| **D3** | Salvar e o salvamento automático travam a interface (4 s em 4K/10 camadas, a cada 60 s por documento alterado); abrir trava 3,1 s | 7.3 | **Alta** (percebida como "engasgo") | Operação longa na thread da interface; ponte sem liberar o GIL | S1.2, S1.3 |
| **D4** ✅ | (corrigido em 2026-10-01: S1.1) Repintura em zoom ≥ 100% copia o canvas inteiro duas vezes. **Zoom de trabalho:** a tela pede a região que pinta (`get_display_image` → `get_display_region`). Medido, mediana, aquisição só da região de 1600×900: 0,52 / 0,46 / 0,62 ms em 1080p / 4K / 6000×4000, contra 7,1 / 37,7 / 122,7 ms do canvas inteiro; região de traço 128×128: 0,01 ms. Repintura a 100% com `drawImage` real (widget raster): 7,3 / 34,0 / 115,0 ms → 0,5 ms nos três. **Zoom afastado: D18, também corrigido** | 7.1 | **Alta** | Contrato de exibição "canvas inteiro" | S1.1 |
| **D5** ✅ | Curvas Bézier da janela de curvas escrevem direto no motor: segundo escritor da dinâmica do pincel; a curva não é salva com o pincel | `curve_window.sync_to_engine` → `backend.set_curve_control_points`; nada em `ui/core/state` | Média | Um escritor por assunto (AGENTS 4.2, caminho 4) | Curvas viram parâmetro do `BrushState` e do preset |
| **D6** | Perfis de cor nativos com nome de padrão e fórmula aproximada; dois pipelines de cor | 4.12, 7.7 | Média (alta para impressão) | Lei do Rio 2 (algoritmo duplicado divergente); promessa da interface | S3.2 |
| **D7** ✅ | Histórico-sombra `_action_stack`/`_redo_stack` escrito e nunca lido; `_is_filling` nunca vira `True` | grep: só escritas | Baixa | Estado morto (segunda cópia de estado) | Remover |
| **D8** ✅ | `compress_inactive_layers` existe na ponte e ninguém chama | grep | Baixa (custo de memória) | Capacidade sem dono | Decidir: política de memória que chame, ou remover |
| **D9** ✅ | `PluginType.BRUSH/FILTER/TOOL/IO` declarados sem ponto de extensão | 0 usos | Baixa (promessa de API) | A interface não promete o que não faz | Remover até existir, ou implementar S2.4 |
| **D10** | O documento do framework ARCcC contradiz o código (zonas 250/300, `plugins/` na raiz, "a UI não pinta pixels") | Apêndice E | Baixa | Documentação como contrato | Atualizar |
| **D11** | Prévia da transformação (bilinear, Qt) diferente do resultado (bicúbico, motor) | 7.6 | Baixa | Lei do Rio 2 (duas implementações da mesma conta) | Prévia pelo motor em baixa resolução, ou mesmo amostrador |
| **D12** | Forma e texto: `QImage` do canvas inteiro por confirmação (96 MB em 6000×4000), sem pincel, sem edição posterior | 6.9 | Média (memória em canvas grande) | Pixel pintado fora do motor e depois colado | Rasterizar só a caixa da forma; forma pelo motor de pincel no futuro |
| **D13** ✅ | (corrigido em 2026-10-01: S0.2) Tamanho máximo de documento sem contrato único: novo documento até 16384; "Tamanho do Canvas" oferece até 32000 e a operação recusa acima de 2 GB; abrir imagem é barrado pelo Qt em 256 MB com mensagem que culpa o arquivo; aritmética do motor em `int` | 4.8, 6.8, 7.3 | Média | Limite sem dono | O motor declara o máximo e os diálogos e ações consultam; `size_t` antes de multiplicar; mensagem certa ao abrir |
| **D14** ✅ | (corrigido em 2026-10-01: S0.7; o parâmetro saiu da interface, dos 8 motores e dos 2 chamadores; as outras 32 células do golden não mudaram, a prova de que a remoção foi neutra) A interface dos motores promete ler a imagem composta e nenhum motor lê: o comentário de `IBrushEngine::renderDab` diz que Desfoque e Borrar leem o `compositeBuffer`; os 8 `renderDab` o recebem como `/*compositeBuffer*/`, e o orquestrador passa `&outputBuffer` mesmo assim | `IBrushEngine.hpp` (comentário do parâmetro e de `usesScratchLayer`); `StrokeOrchestratorSegment.cpp:125`. Achado pelo estudo externo (Apêndice F), conferido no código | Baixa hoje; alta para o próximo motor que acreditar no comentário | Contrato que promete o que não faz (mesmo caso do `gapClosingPx` do balde) | Tirar o parâmetro, ou declarar no contrato que a fonte é a camada ativa |
| **D15** ✅ | (corrigido em 2026-10-01: S0.7; medido: antes, 1781 pixels diferiam ao deslocar a cena 64 px no sentido para cima e para a direita; depois, 0 nos dois sentidos; o rastro lê um `GridSnapshot` tirado antes do dab e as 4 células do Borrar no golden foram regravadas de propósito) O Borrar lê e escreve a mesma camada no mesmo dab: a amostra do rastro (`getTilePixel(tileGrid, ...)`) pode ler um pixel já reescrito naquele dab, e o resultado depende da ordem de varredura. O Desfoque faz certo: copia a área antes | `SmudgeEngine.cpp` (amostra do rastro e `buffer.setPixel` na mesma grade). Achado pelo estudo externo, conferido lendo o código; **não medido** | Média (qualidade do Borrar) | Fonte e destino sem política de leitura | Ler de uma cópia da área tirada antes do dab, como o `BlurEngine` |
| **D18** ✅ | (corrigido em 2026-10-01: S1.1) No zoom afastado (nível LOD), a pirâmide era reconstruída **inteira** a cada repintura depois de qualquer mudança, e a bandeira de sujo do tile da camada ativa nunca era limpa (a interface não chama `clear_dirty_tiles`): depois do primeiro traço, `getDisplayPixelBufferLOD` marcava a pirâmide suja em **toda** chamada, mesmo sem mudança. Medido, mediana, repintura de um traço em nível 1: 2,6 / 10,3 / 12,9 ms em 1080p / 4K / 6000×4000 (reconstrução + cópia para QImage). **Agora:** o `Compositor` registra o retângulo que escreveu (`takeDamage`; toda escrita no buffer de saída passa por ele), a `MipmapPyramid` refaz só essa região em cada nível, `touch()` deixou de invalidar a pirâmide, e a tela pede só a região (`get_display_lod_region`). Medido: repintura depois de uma mudança 0,36 / 0,28 / 0,24 ms contra 1,4 / 5,1 / 11,6 ms da reconstrução inteira de referência (só motor, sem a cópia da QImage). O teste usa um oráculo independente em numpy depois de cada operação e em 40 sequências aleatórias; 4 mutações no código (sem registrar dano, arredondar para baixo, limite fora por um, x0 sem piso) reprovam 82, 11, 2 e 19 testes | `PaintEngineFacadeDisplay.cpp`, `MipmapPyramid.cpp`, `Compositor.cpp`, `DamageRect.hpp`, `aladyn.py` | Alta em documento grande (13 ms de 16,6 de um quadro) | Cache que não guarda (bandeira de sujo sem dono que a limpe) e custo proporcional ao canvas | Pirâmide com região suja, limpa depois da reconstrução. **Resíduo registrado:** com perfil de cor diferente de sRGB, o buffer de exibição inteiro ainda é copiado e convertido a cada leitura do LOD (o nível 0 por região já aplica o perfil só na região) |
| **D16** ✅ | (corrigido em 2026-10-01: S0.7; a viewport cronometra a aquisição à parte (`qt_acquire_image_ms`), o medidor 6 mostra cópia + desenho e o total do paint, e as 6 telas leem a conta única `presentation_ms`; o teste usa uma cópia de 30 ms e confere que as parcelas não passam do total) O medidor "Apresentação Blit Qt" da telemetria cronometra só o `drawImage`. A cópia do canvas (`get_qimage_lod`, o custo do D4: 34 ms em 4K) acontece antes do cronômetro, e `qt_paint_total_ms` é publicado sem medidor que o mostre | `viewport_renderer.py` (cronômetro depois de `get_qimage_lod`), `telemetry_meters.py`, `telemetry_report.py`. Achado pelo estudo externo, conferido no código | Média (o instrumento esconde o maior custo da tela) | Número que não mede o que o nome diz | Medir a aquisição da imagem à parte e mostrar o total do paint |

### 8.2 Riscos estruturais (quebram ao receber feature)

| Id | Risco | Onde | O que dispara |
|---|---|---|---|
| **R1** | Interface do motor com 176 métodos, e consumidores dependendo do todo | `EngineBackend` | Motor alternativo, testes isolados, processo separado, GPU |
| **R2** | Rasterização duplicada em 9 motores (CCN 25–71) | `engines/*`, `DabRenderer` | Qualquer feature transversal de pincel |
| **R3** | Pixel RGBA8 no tipo mais baixo do motor | `utils/ColorRGBA` | 16 bits, HDR, cor exata |
| **R4** | Exibição e memória proporcionais à área inteira do canvas (dois buffers de tela cheia por documento, cópia por repintura) | facade, ponte, viewport | Canvas grande, vários documentos, GPU |
| **R5** | Propriedade de camada espalhada (26–43 arquivos) | documento, ponte, motor, arquivo | Máscara de camada, modos novos, qualquer atributo |
| **R6** | Operações longas na thread da interface; GIL liberado em 1 ponto | ponte, documento, recuperação | Arquivos grandes, filtros pesados, exportação |
| **R7** | Presets e parâmetros de pincel em código, sem formato de arquivo | `brush_plugin/presets` | Biblioteca do usuário, importação, loja |
| **R8** | Ferramentas, filtros e formatos sem registro | `tools.py`, `FilterType`, `document_actions` | Ferramenta nova, filtro novo, PSD/TIFF/ORA |
| **R9** | Plugin com acesso total e sem isolamento | `PluginContext` | Plugins de terceiros |
| **R10** | Distribuição sem assinatura e sem atualização | `scripts` | Qualquer venda |
| **R11** ✅ | (resolvido em 2026-10-01: S0.6) Referência de pixel (golden) só para o motor padrão: `stroke_golden.json` cobre o Pincel; nenhum teste pinta com Borrar ou Desfoque; os outros 6 motores só têm asserções de comportamento ("deixou tinta") | `tests/golden/`, `tests/test_lowlevel_brush_raster.py` | Qualquer mudança em motor de pincel, S2.1, S3.1 |

---

## 9. Prontidão para features

Para cada feature provável: o que ela toca **hoje**, o custo, e a fundação que
falta. "Fundação" é o item da Seção 10 que torna a feature barata e segura.

| Feature | Toca hoje | Custo e risco hoje | Fundação que falta |
|---|---|---|---|
| **Pincel novo (motor)** | `BrushProfile`, fábrica, novo `renderDab` (~150 linhas copiadas), ponte (`def_readwrite`), `.pyi`, dicionário do perfil, presets, painel avançado, traduções | Alto; herda a duplicação R2 | S2.1 núcleo comum de dab; S2.5 parâmetros declarados pelo motor |
| **Biblioteca de pincéis do usuário** | Presets em código, `BrushState` sem curvas | Não há onde salvar | S0.4 curvas no estado; formato de preset em arquivo (S2.5) |
| **Modos de mesclagem novos** (Cor, Luminosidade, Luz Suave...) | `BlendEquations` (CCN 32), enum C++ e Python, arquivo, traduções, combo; Cor/Luminosidade exigem HSL no caminho quente | Médio; risco de regressão de composição | Tabela de modos como dados + golden por modo (S2.2 aplicado à mesclagem) |
| **Máscara de camada** | Camada C++, `LocalLayer`, arquivo (versão do formato), histórico (tiles da máscara), compositor, "pintar na máscara" (o alvo do pincel deixa de ser só a camada), painel | Alto; ~40 arquivos | S2.2 descritor de propriedade; "alvo de pintura" no motor |
| **PSD (abrir e salvar)** | Novo IO sem registro; mapear 13 modos, grupos, recorte (máscaras não existem) | Alto | S2.4 registro de formatos; S1.2 leitura e gravação por tile em lote; máscara de camada para ida e volta fiel |
| **16 bits por canal** | Tudo: `ColorRGBA` → tile → motores → composição → seleção → histórico → ponte → arquivo | Muito alto, e cresce a cada feature em 8 bits | S3.1 (decidir antes de ampliar os motores); S2.1 reduz 9 motores a 1 núcleo |
| **Canvas na GPU** | Exibição; hoje o contrato é "canvas inteiro" | Alto | S1.1 contrato de exibição por tiles alterados |
| **Texto e forma editáveis, camada vetorial** | Rasterizados na hora; tipos de camada fixos (desenho, grupo, filtro) | Alto | Tipo de camada extensível (depois de S2.2) |
| **Animação** | Documento sem eixo de tempo | Muito alto | Decisão de produto antes de qualquer fundação |
| **Ferramenta nova** | `TOOL_META`, `tool_settings`, `input_router`, `ToolManager`, view de opções | Médio | S2.4 registro de ferramentas |
| **Filtro novo** | `FilterType` (7), `vector<float>` sem nomes, diálogo manual | Médio | S2.4 descritor de filtro exposto pelo motor |
| **Plugin de terceiro** | `PluginContext` largo, tipos sem extensão | Alto risco de acoplamento | S2.3 backend segregado; API de plugin estreita e versionada |
| **Painel de histórico** | O motor já expõe ids e descrição dos passos | **Baixo**: quase pronto | — |
| **Degradê, imagem de referência** | Ferramenta nova e painel novo | Médio | S2.4 (ferramenta); nenhuma fundação crítica |

---

## 10. Plano de solidificação

Ordem pensada para que cada fase torne a seguinte mais barata. Esforço:
**P** (até uma sessão), **M** (algumas sessões), **G** (várias sessões, com
decisão de desenho). Cada critério de pronto é um número que um teste ou
script pode conferir.

### S0 — Defeitos achados (P cada; primeiro, porque são baratos e reais)

| Item | O quê | Pronto quando |
|---|---|---|
| S0.1 ✅ | Enum `EngineType` canônico em Python espelhando o C++ (como `LayerBlendMode`); roteador e presets usam o enum; ponta borracha → Borracha (D1) | Teste da ponta borracha espera Borracha; nenhum número solto de motor em `ui/` (catraca) |
| S0.2 ✅ | Falha ao criar contexto vira erro que `show_document` trata (D2). Limite único de documento: o motor declara o máximo, e o diálogo de novo documento, "Tamanho do Canvas" e abrir imagem consultam. `size_t` antes de multiplicar (D13) | Teste com falha simulada de alocação: o documento anterior não recebe nada e o usuário vê o erro; diálogos com o mesmo máximo |
| S0.3 ✅ | Remover histórico-sombra (D7); decidir `compress_inactive_layers` (D8); remover os `PluginType` sem extensão (D9) | Catraca de acoplamento igual ou menor; grep limpo |
| S0.4 ✅ | Curvas Bézier como parâmetros do `BrushState` e do preset, com um escritor (D5) | Trocar de pincel e voltar preserva a curva; `curve_window` não chama o backend |
| S0.5 ✅ | Atualizar `02-arquitetura/01-framework-arccc.md` (D10) | Nenhuma afirmação do Apêndice E continua falsa |
| S0.6 ✅ | **Antes de qualquer outra mudança em motor:** referência de pixel (golden) de traço para os 9 motores, Borrar e Desfoque incluídos (R11) | `stroke_golden.json` com uma célula por motor; o teste falha se um motor mudar um pixel |
| S0.7 ✅ | Contrato do `compositeBuffer` (D14); Borrar lendo de uma cópia (D15); telemetria com a aquisição da imagem e o total do paint (D16) | `IBrushEngine` sem parâmetro que nenhum motor lê (ou comentário que bate com os 8); golden do Borrar regravado com a mudança explicada no commit; medidor da aquisição e teste que confere que as parcelas não passam do total |

### S1 — Desempenho que o usuário sente (M–G)

| Item | O quê | Por quê | Pronto quando |
|---|---|---|---|
| **S1.1** | **Exibição por região alterada.** A facade entrega só o retângulo sujo (ou uma visão sem cópia do buffer, via buffer protocol); a interface mantém um `QImage` persistente e atualiza só o retângulo | D4/R4: 34 ms → proporcional ao que mudou | Repintura em zoom 100%: 4K < 4 ms, 6000×4000 < 6 ms (Linux do agente); teste de desempenho com limite relativo |
| **S1.2** | **Salvar e abrir em segundo plano.** Instantâneo copy-on-write das camadas (o motor já tem COW nos tiles) → compressão e gravação numa thread, com o GIL liberado. Formato por tile (omite tiles vazios) → LMN v3 com migração | D3/R6: 4 s e +609 MB | Nenhum travamento > 50 ms da interface ao salvar 4K/10 camadas; pico de memória < 1 buffer de camada; abrir 4K/10 < 1 s |
| **S1.3** | **Salvamento automático incremental** sem trocar o contexto ativo, só com o que mudou | D3 | Nenhum travamento perceptível durante 10 min de pintura com 3 documentos |
| S1.4 | AVX2 com escolha em tempo de execução | Build distribuído é escalar | Módulo AVX2 carregado quando a CPU suporta; mesma caracterização (golden) |
| S1.5 | Cache das camadas abaixo e acima da ativa durante o traço (medir antes com camadas densas) | Custo do traço cresce com camadas sob o pincel | Traço com 100 camadas densas ≤ 1,5× o de 1 camada |

### S2 — Contratos de extensão (M–G; torna as features baratas)

| Item | O quê | Pronto quando |
|---|---|---|
| **S2.1** | **Núcleo comum de rasterização de dab**: recorte de tiles, pegada, dureza, trava de alfa e seleção num componente; cada motor fornece só o "kernel de pixel" (política) | Cada `renderDab` ≤ 60 NLOC e CCN ≤ 15; caracterização de traço idêntica (golden) |
| **S2.2** | **Descritor único de propriedade de camada** (nome, tipo, padrão, persistência, sincronização) consumido por `LocalLayer`, serializador, histórico e `layer_backend_sync` | Nova propriedade booleana toca ≤ 6 arquivos (hoje 26–43) |
| **S2.3** | **Backend segregado:** cada consumidor recebe o sub-protocolo que usa (injeção); métodos sem chamador removidos | Nenhum consumidor fora da ponte depende de `EngineBackend` inteiro; métodos sem uso = 0 |
| S2.4 | **Registros:** ferramentas (protocolo `Tool` que o roteador consulta), filtros (descritor vindo do motor: nome, parâmetros com limites), formatos de arquivo (importador/exportador) | Ferramenta ou filtro novo sem editar `input_router` nem diálogo manual |
| S2.5 | Parâmetros de cada motor declarados pelo próprio motor e expostos como descritor; painel avançado e preset gerados do descritor; preset em arquivo | Motor novo sem editar a struct comum nem a ponte campo a campo |
| S2.6 | Serializador sem descoberta (`getattr`/`hasattr` → contrato garantido); funções de CCN 27–31 em passos nomeados | `serializer.py` com 0 `getattr` literal e 0 `hasattr`; sem `noqa: C901` |
| S2.7 | Liberar o GIL em operações longas (composição completa, filtros, flood fill, confirmar transformação, buffers de salvar) | Teste: operação longa não bloqueia uma thread Python concorrente |
| S2.8 | Cobertura do caminho do arquivo e da cor | `document_actions` ≥ 85% (hoje 37%), `logging` ≥ 80% (28%), `cms_engine` ≥ 80% (44%) |
| S2.9 | Facade sem getters mutáveis do estado interno (`getLayerStack`, `getBrushProfile`...) fora da ponte de perfil | A ponte só usa a API de operações |

### S3 — Fundação de cor e profundidade (G; decisão do dono antes de codar)

| Item | O quê | Recomendação |
|---|---|---|
| **S3.1** | **Decidir o formato de pixel.** (a) RGBA16 inteiro em todo o motor; (b) formato por documento (8 ou 16) com o núcleo parametrizado pelo tipo de canal; (c) float16/32 | **(b)**, introduzido primeiro no núcleo comum de dab (S2.1) e no compositor, onde a parametrização custa uma vez em vez de nove. Documentos de 8 bits continuam idênticos. Pronto: golden de 8 bits inalterado e caracterização de 16 bits nova |
| **S3.2** | **Um pipeline de cor só:** LittleCMS (lcms2, licença MIT) no motor; os perfis nativos viram ICC reais embutidos; a interface para de converter cor | Pronto: ΔE00 médio < 1 contra a referência ICC num conjunto de cores de teste; nenhum caminho de cor em Python fora da configuração |

### S4 — Distribuição comercial (já na Rota C)

Assinatura de código, atualização automática, relatório de queda com
consentimento, decisão sobre ffmpeg (licença). Detalhe em
`../05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md`.

### Por que esta ordem

| Fase | Razão |
|---|---|
| S0 antes de tudo | Defeitos reais e baratos: D1 afeta todo usuário de caneta hoje, e D2 pode escrever no documento errado. |
| S1 antes de S2 | É o que o artista sente em cinco minutos de uso. S1.1 e S1.2 definem os contratos de dados (retângulo sujo, instantâneo por tile) que PSD, GPU e salvamento em segundo plano vão usar. |
| S2 antes de features | Cada feature da Seção 9 fica 3 a 9 vezes mais barata depois de S2.1, S2.2 e S2.4. |
| S3 depois de S2.1 | Parametrizar o tipo de pixel num núcleo só, e não em nove motores. Precisa decidir **antes** de acrescentar motores ou modos de mesclagem em 8 bits. |

---

## 11. O que preservar

Estes nós estão 🟢 e são a base do resto. Mudanças neles pedem cuidado dobrado:
- **Camadas do motor** (`utils` → `infrastructure` → `core` → `boundary`) com
  `#include` só para baixo e a ponte só pela API pública (catraca
  `test_arccc_cxx_layers.py`).
- **Histórico unificado** (`TileUndoManager` + `layer_transaction`) com
  paginação em disco e injeção de falhas.
- **Documento como fonte única**, com guardas de projeção e identidade por uid.
- **Estado compartilhado** (`ui/core/state`): um escritor por assunto, valor
  igual não emite.
- **Caracterização por imagem** de traço e composição (`tests/golden/`): a rede
  de segurança de S2.1 e S3.1.
- **Catracas e conferência de Windows antes do commit.**
- **Pirâmide de LOD** para zoom afastado.
- **Formato `.lmn`** com validação, `.bak` e migração (S1.2 muda a codificação
  das camadas, não essas garantias).

---

## Apêndice A — medições e comandos

Ambiente: Linux, 4 núcleos, Python 3.11.15, PySide6 6.11.1, Qt offscreen,
motor com g++ `-O2 -fopenmp` escalar, base `bd07511`. Scripts de medição no
rascunho da sessão (não versionados). Mediana de 3 a 10 repetições.

| Medição | Resultado |
|---|---|
| `backend.get_qimage()` (canvas inteiro → `QImage`) | 1920×1080: 5,91 ms · 3840×2160: 34,59 ms · 6000×4000: 114,23 ms |
| `backend.get_qimage_lod(0.25)` | 0,03 · 0,33 · 1,04 ms |
| Traço de 120 amostras, pincel 40 px, 1 camada | 28,5–30,5 ms (≈0,24 ms/amostra) nos três tamanhos |
| Mesmo traço com 20 camadas sobrepostas | 67,0 · 68,8 · 74,4 ms |
| Traço com N camadas esparsas (2560×1440) | 1: 0,146 · 10: 0,134 · 30: 0,197 · 60: 0,225 · 100: 0,274 ms/amostra |
| Mudar opacidade com 20 camadas | 15,6–17,4 ms |
| Par desfazer+refazer com 20 camadas | 42,5 · 73,2 · 105,3 ms |
| Custo por amostra na interface (`handle_pointer_move`, inclui o motor) | 1080p p50 0,068 / p95 0,163 ms · 4K p50 0,241 / p95 0,626 ms |
| Repintura do canvas | Documento inteiro na tela: 0,34 (1080p) · 3,38 ms (4K); zoom 100%: 7,2 · 34,4 ms |
| Abertura até a janela principal | 0,61–0,65 s; 122 MB; documento 4K novo: +76 MB, 0,08 s |
| Salvar `.lmn`, 10 camadas | 1080p: 1,14 s, +169 MB, 0,4 MB · 4K: 4,07 s, +609 MB, 0,6 MB |
| Abrir `.lmn` 4K, 10 camadas | ler e validar 0,41 s + restaurar 2,64 s |
| Contexto 30000×30000 (direto na ponte) | não criado; contexto anterior continua ativo (D2) |
| Limite do decodificador de imagem do Qt | `QImageReader.allocationLimit()` = 256 MB (D13) |
| Suíte | 1015 casos, 1010 passam, 5 pulados (`python -m pytest`) |
| Cobertura de `ui/` | 81% de 27.276 comandos (`coverage run --source=ui -m pytest`) |
| Complexidade | `lizard engine bridge -l cpp`; `lizard ui -l python` |
| Acoplamento | `python -m tests.arccc_coupling_metrics --top 25` |
| Idiomas | 1020 chaves por idioma, 0 faltando (script sobre `assets/locales`) |
| Uso do backend por pacote | Script que cruza os métodos de `EngineBackend` com as chamadas `backend.x(` em `ui/` |

---

## Apêndice B — complexidade

### C++ (lizard; CCN conta também `&&` e `||`)

759 funções, média CCN 4,0, 25 acima de 20:

| Função | NLOC | CCN |
|---|---:|---:|
| `raster::FloodFill::execute` | 221 | 80 |
| `raster::DabRenderer::renderDab` | 273 | 71 |
| `selection::SelectionEngine::generateWandMask` | 168 | 67 |
| `engines::PencilEngine::renderDab` | 188 | 44 |
| `raster::TransformEngine::beginTransform` | 141 | 41 |
| `orchestrator::StrokeOrchestrator::updateStrokeRaw` | 184 | 39 |
| `engines::BlurEngine::renderDab` | 178 | 38 |
| `compression::Lz4Codec::compressBlock` | 104 | 34 |
| `engines::EraserEngine::renderDab` | 137 | 34 |
| `engines::InkerEngine::renderDab` | 152 | 33 |
| `engines::MarkerEngine::renderDab` | 170 | 33 |
| `blending::blendPixel` | 132 | 32 |
| `document::LayerMerger::flattenGroup` | 90 | 32 |
| `engines::SmudgeEngine::renderDab` | 170 | 31 |
| `orchestrator::BufferPasteOrchestrator::paste` | 104 | 31 |
| `engines::OilImpastoEngine::renderDab` | 152 | 30 |
| `history::TileUndoManager::moveStep` | 70 | 30 |
| `orchestrator::renderDabsPipeline` (17 parâmetros) | 129 | 26 |
| `orchestrator::StrokeOrchestrator::endStrokeRaw` | 94 | 26 |
| `engines::WatercolorEngine::renderDab` | 156 | 25 |
| `math::CurvilinearSnapEngine::snap` | 76 | 24 |
| `brush::DynamicMapper::applyJitter` | 67 | 23 |
| `selection::SelectionMask::getContourLoops` | 87 | 23 |
| `compression::Lz4Codec::decompressBlock` | 51 | 22 |
| `raster::DabInterpolator::interpolateSpline` | 125 | 21 |

### Python

- **lizard** (`ui/`): 2.603 funções, média CCN 2,8. Acima de 10: 85; acima
  de 15: 37; acima de 20: 21.
- **ruff (McCabe, a métrica da catraca):** 6 funções acima de 20, todas com
  `noqa` registrado:
  - `get_cached_curvilinear_data` 57;
  - `DocumentSerializer.read`, `_validate_manifest` e `validate_auxiliary` 31
    cada;
  - `DocumentSerializer.save` 27;
  - `restore_document` 24.

  O ruff não conta operadores booleanos, daí a diferença para o lizard. **Três
  das seis estão no caminho do arquivo do usuário.**

---

## Apêndice C — cobertura por pacote

`ui/`, suíte completa, do menor para o maior:

| Pacote | Comandos | Cobertura |
|---|---:|---:|
| `ui/infrastructure/logging` | 158 | 28,5% |
| `ui/infrastructure/runtime_paths.py` | 27 | 51,9% |
| `ui/core/color` | 278 | 62,2% |
| `ui/boundary/orchestrator` | 975 | 65,7% |
| `ui/plugins/panels/layers_plugin` | 1.665 | 67,4% |
| `ui/plugins/panels/brush_plugin` | 1.372 | 68,6% |
| `ui/core/widgets` | 1.806 | 71,2% |
| `ui/plugins/panels/navigator_plugin` | 397 | 74,1% |
| `ui/core/plugins` | 791 | 76,9% |
| `ui/plugins/system/workspace_core` | 6.169 | 80,5% |
| `ui/infrastructure/bridge_client` | 1.404 | 81,1% |
| `ui/infrastructure/i18n` | 116 | 82,8% |
| `ui/core/screens` | 3.042 | 84,3% |
| `ui/plugins/panels/telemetry_plugin` | 302 | 85,4% |
| `ui/infrastructure/theme` | 315 | 85,7% |
| `ui/core/dialogs` | 2.169 | 86,4% |
| `ui/plugins/panels/recording_plugin` | 1.048 | 87,3% |
| `ui/core/document` | 1.750 | 88,1% |
| `ui/infrastructure/config` | 255 | 89,0% |
| `ui/core/components` | 1.138 | 89,7% |
| `ui/plugins/panels/geometry_plugin` | 879 | 92,8% |
| `ui/core/engine` | 474 | 93,0% |
| `ui/core/state` | 303 | 100% |

**Arquivos do caminho crítico:**

| Arquivo | Cobertura |
|---|---:|
| `document_actions.py` | 37% |
| `cms_engine.py` | 44% |
| `aladyn_color_mixin.py` | 52% |
| `recovery_controller.py` | 65% |
| `aladyn_stroke_mixin.py` | 76% |
| `serializer.py` | 83% |
| `input_router.py` | 85% |
| `restore.py` | 86% |
| `history.py` | 87% |
| `canvas_stroke_pipeline.py` | 90% |
| `recovery.py` | 91% |

---

## Apêndice D — acoplamento e dívida medida

**Catraca de acoplamento:**

| Métrica | Valor |
|---|---:|
| `hasattr` | 62 |
| `getattr` literal | 62 |
| Acesso privado alheio | 15 |
| `except` silencioso | 0 |
| Import reverso | 0 |

**Maiores concentrações:**
- `getattr` literal: `serializer.py` 14, `aladyn_stroke_mixin.py` 7,
  `layer_backend_sync.py` 5.
- `hasattr`: `aladyn_buffers.py` 7, `render_settings_components.py` 5,
  `canvas_size_dialog.py` 4.

**Outras medidas:**

| Medida | Valor |
|---|---|
| `except Exception` em `ui/` (não silencioso) | 81 |
| `except BaseException` | 1 (inicialização do motor) |
| `TODO`/`FIXME` | 6 |
| Singletons (`instance()`) | 10: config, tema, idioma, documentos, registro do motor, telemetria, plugins, serviços, CMS, catálogo de cor |
| Cores fixas | 147 em 40 arquivos |
| Pares "subpasta importa a pasta mãe" (Python) | 5 conhecidos, listados em `tests/test_canvas_contracts.py` |
| Propriedade de camada | Máscara de recorte: 26 arquivos em 11 pastas; trava de alfa: 43 arquivos em 15 pastas |

---

## Apêndice E — documentação desatualizada

`../02-arquitetura/01-framework-arccc.md` (o documento do método) afirma:

| Afirmação no documento | Realidade medida |
|---|---|
| Zona verde até 250 linhas, amarela de 251 a 449 | A regra verificada é 300 (`tests/arccc_governance_rules.py`), com parede em 430–449 |
| Plugins em `plugins/` na raiz | Estão em `ui/plugins/` desde 2026-09-25 |
| "A UI não realiza pintura de pixels direta; delega integralmente ao backend" | Forma e texto são rasterizados com `QPainter` na interface e colados no motor (D12) |
| "Um painel complexo é composto por painel base, controladores, **mixins de estado**..." | A seção 4.2 do `AGENTS.md` proíbe mixin que compartilha estado fora do backend e pede colaborador com estado próprio |

O documento é o contrato do método; enquanto contradisser o código, cada
agente novo recebe instruções erradas logo na porta de entrada (S0.5).

**Resolvido em 2026-10-01 (S0.5, D10):** `01-framework-arccc.md` foi
reescrito como "como o ARCcC se aplica ao Lumenia" e o método universal (v1.1.0,
do dono) está em `08-arccc-metodologia-universal.md`.

---

## Apêndice F — estudo externo do motor (avaliado em 2026-09-26)

O dono do projeto trouxe um estudo do motor feito fora desta sessão
(`ESTUDO_MOTOR_C_v1`, fora do repositório): 632 arquivos e 73 mil linhas, com
137 documentos, 40 patches, 315 arquivos C++ (cópias de trechos do motor e
testes isolados), 44 JSON e 58 relatórios de validação. A pergunta era se ele
eleva o motor. Conferido contra o código em `f535371`:

| Pergunta | Resposta medida |
|---|---|
| Sobre qual versão | Uma cópia do projeto de 2026-09-23/24. Os patches apontam para caminhos anteriores à reorganização de 2026-09-25 (`fc08f11`): `engine/boundary/public-api/internal/`, `engine/core/bindings/`, `engine/core/canvas/TileUndoManager.*` |
| Algo chegou ao repositório | Não. `StrokeSample`, `BrushFootprint`, `DabRenderWorkspace`, `FilterSampling`, `PixelSurfaceView`, `SmudgeReservoir`, `TileRuntime`, `RuntimeMemoryBudget`: 0 ocorrências em `engine/` e `bridge/` |
| Como foi validado | Cada incremento sobre o incremento anterior, num ambiente isolado. Os próprios relatórios dizem que o módulo Python não foi compilado ("pybind11 headers are unavailable"); não rodou a suíte do projeto nem a conferência de Windows. O baseline de desempenho é sintético, e o estudo avisa |
| Veredito do próprio estudo | "Current release decision: NOT_READY", com os 8 portões pendentes |
| Tamanho | Os patches acrescentam 11.325 linhas (com repetição entre incrementos empilhados); o motor inteiro tem 17.565 |

**Adotado** (conferido no código de hoje): D14, D15, D16 e R11, com as tarefas
S0.6 e S0.7. O estudo também tem razão em que o Borrar carrega uma cor só
(`m_carriedColor`) e por isso não arrasta textura; corrigir isso é melhorar o
pincel, e entra junto da feature "Borrar profissional", não da base.

**Não adotado como base:**
- O roteiro "Aladyn Engine 2.0" (reservatório espacial do Borrar, umidade,
  aquarela e óleo novos, superfície de cor profunda, estados de residência de
  tile, canais de simulação no histórico). São capacidades novas: entram quando
  uma feature pedir, e aí S2.1 (núcleo comum de dab) e S3.1 (formato de pixel)
  são o lugar delas.
- Portões de release, níveis de confiança, esquemas JSON, SHA256 e matrizes de
  evidência. Seriam um segundo sistema de verificação, paralelo à suíte, às
  catracas, ao golden e à conferência de Windows, sem medir o motor real.

**Não aplicar os patches do estudo:** foram feitos sobre caminhos que não
existem mais, empilhados entre si e sem passar pela suíte do projeto. Uma ideia
dele que valer para uma feature é reescrita sobre o motor atual, com golden
antes.
