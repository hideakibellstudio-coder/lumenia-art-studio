# Pendências atuais da fase de correção da base

> Documento vivo. Sintetiza e substitui `historico/estado-da-base-2026-09-15.md`
> e a parte ainda acionável de `historico/auditoria-f017-f031-endurecimento-navigator.md`.
> Atualizado com verificação ao vivo no terminal em 2026-09-24 (não é estimativa
> nem cópia do relatório anterior). Toda mudança de status aqui deve vir com uma
> linha correspondente em `../README.md`.

**Regra de ouro desta fase:** nenhuma feature nova. Cada item abaixo remove
código, remove ambiguidade, ou adiciona verificação. Nada aqui é estético.

---

## 🏁 Linha de chegada da base (decisão do dono, 2026-09-26)

**Por que existe:** o trabalho de organização parecia infinito. Toda análise
acha coisas (`07-analise-arccc-decomposta.md` achou 16 defeitos e 11 riscos);
se o critério for "não sobrou nada para melhorar", nunca acaba. O critério
passa a ser: **o que prejudica o usuário hoje ou impede a próxima feature.**

**A base está pronta quando estes quatro grupos estiverem feitos.** A lista é
fechada: só diminui.

1. **S0.1–S0.5** (relatório, Seção 10):
   - ~~S0.1: ponta borracha da caneta liga o Borrar (D1); enum `EngineType` em
     Python.~~ *(feito em 2026-10-01: `ui/core/engine/engine_type.py`; roteador, 9
     categorias de preset, painel de parâmetros e pré-visualização usam o enum;
     `tests/test_engine_type_contract.py` confere o enum com o nativo e barra
     número solto de motor em `ui/`; o teste da ponta borracha agora espera a
     Borracha.)*
   - S0.2: falha ao criar contexto do motor é engolida (D2); limite único de
     documento (D13).
   - ~~S0.3: histórico-sombra, compressão sem chamador, `PluginType` sem
     extensão (D7–D9).~~ *(feito em 2026-10-01: D7 `_action_stack`, `_redo_stack` e
     `_is_filling` saíram do backend (eram escritos e nunca lidos); D9 os tipos
     BRUSH, FILTER, TOOL e IO saíram de `PluginType`; D8 `compress_inactive_layers`
     é capacidade do motor com teste e fica sem chamador de produção de propósito,
     registrado em `bridge/README.md`: a política de quando comprimir só entra com
     benchmark.)*
   - ~~S0.4: curvas Bézier fora do `BrushState` (D5).~~ *(feito em 2026-10-01:
     `ui/core/state/brush_curves.py` (`BrushCurve`, `CurveSetting`); o `BrushState`
     guarda as curvas editadas, o `BrushEngineSync` é o único escritor no motor (inclui
     a troca de documento e a seleção de preset, que não apaga mais a curva do
     usuário) e a `CurveWindow` só edita e mostra o estado, sem conhecer o motor.
     Abrir a janela deixou de empurrar os padrões dela para o motor. Colocar a
     curva dentro de um preset em arquivo fica para a feature de biblioteca de
     pincéis (ponto de extensão registrado no relatório 08).)*
   - ~~S0.5: documento do framework ARCcC desatualizado (D10).~~ *(feito em
     2026-10-01: `01-framework-arccc.md` reescrito; método universal v1.1.0 em
     `08-arccc-metodologia-universal.md`; ciclo de construção no `AGENTS.md`,
     seção 5.0; assunto de commit em inglês desde esta data.)*
2. ~~**S0.7 — três achados do estudo externo** (Apêndice F do relatório),
   conferidos no código.~~ *(feito em 2026-10-01.)*
   - ~~D14: a interface dos motores promete ler a imagem composta
     (`compositeBuffer`) e nenhum dos 8 motores lê.~~ *(o parâmetro saiu da
     interface, dos 8 motores e dos 2 chamadores; `IBrushEngine` agora diz que a
     grade é a fonte e o destino. As 32 células do golden que não são do Borrar
     ficaram iguais.)*
   - ~~D15: o Borrar lê e escreve a mesma camada no mesmo dab (resultado depende
     da ordem de varredura).~~ *(o rastro lê um `GridSnapshot` tirado antes do
     dab. Medido com o harness `tests/native/smudge_source_snapshot.cpp`: antes,
     1781 pixels diferiam ao deslocar a cena 64 px; depois, 0, nos dois sentidos de
     movimento. As 4 células do Borrar no golden foram regravadas de propósito.)*
   - ~~D16: o medidor "Blit" da telemetria não conta a cópia do canvas, o maior
     custo da repintura.~~ *(a viewport cronometra a aquisição da imagem à parte;
     o medidor 6 é cópia + `drawImage` e mostra o total do paint;
     `presentation_ms` é a conta única das 6 telas. Teste:
     `tests/test_viewport_paint_telemetry.py`.)*
3. ~~**S0.6 — referência de pixel (golden) para os 9 motores de pincel** (R11).~~
   *(feito em 2026-10-01: `tests/test_brush_engines_characterization.py`, 36
   pinos em `tests/golden/engines_golden.json` = 9 motores × 4 variações (simples,
   trava de alfa, seleção, máscara de recorte); determinísticos entre processos.
   Vem antes de qualquer mudança em motor, S0.7 incluída.)*
4. **S1.1–S1.3:** repintar só a região alterada (D4, feito); salvar e abrir sem
   travar (D3); salvamento automático sem travar.
   - ~~S1.2 e S1.3: salvar e salvar automático sem travar (D3).~~ *(feito em
     2026-10-01: `.lmn` v3 (camada = bloco de tiles LZ4, v1 e v2 seguem abrindo),
     instantâneo copy-on-write das camadas, `DocumentSaver` numa thread, abrir
     numa única composição. 4K com dez camadas: a interface para 0,8 ms (esparso)
     ou 2,2 ms (todas pintadas) para capturar, e nunca mais de 12,6 ms sem tratar
     evento durante a gravação; gravar 3,34 s → 0,02 s esparso; pico de memória
     +692 MB → +2,3 MB esparso e +67 MB denso; abrir 2,0 s → 0,06 s esparso e
     1,2 s denso. Resíduo: abrir um documento denso segue na thread da interface.)*
   - ~~S1.1: repintar só a região alterada (D4).~~ *(feito em 2026-10-01:
     `get_display_image` → `get_display_region` (zoom de trabalho) e
     `get_display_lod_region` (zoom afastado); contrato do módulo nativo na versão
     4. Repintura a 100% com `drawImage` real: 7,3 / 34,0 / 115,0 ms → 0,5 ms em
     1080p / 4K / 6000×4000. Zoom afastado (D18, achado pelo caminho): a pirâmide
     refaz só o retângulo que o compositor escreveu; repintura depois de uma
     mudança 0,36 / 0,28 / 0,24 ms contra 1,4 / 5,1 / 11,6 ms. Resíduo: com perfil
     de cor ≠ sRGB o buffer de exibição inteiro ainda é convertido a cada leitura do
     LOD.)*

Os grupos 1 a 3 são pequenos (até uma sessão cada); o grupo 4 é médio a
grande.

**Achado novo depois de hoje** só entra nesta lista se for defeito que o
usuário sente hoje: comportamento errado, perda de dado ou travamento.
Melhoria, abstração nova ou verificação extra vai para "puxado por feature".

**Puxado por feature (fora da base):** S1.4–S1.5, S2, S3 e o roteiro "Aladyn
Engine 2.0" do estudo externo. Cada item entra junto da feature que precisar
dele. Exemplo: o "Borrar profissional" traz S2.1 (núcleo comum de dab) e o
reservatório espacial do estudo, protegido pelo golden do grupo 3. As catracas
impedem que o que já foi arrumado volte a bagunçar, então não há rodada de
"reorganizar de novo".

**Estado:** registrado; **nada implementado ainda** (o dono pediu para parar
no registro). Quando liberar, a ordem é S0.6 (golden) e depois S0.1.

**Aprovada em 2026-10-01 e em execução** (decisão do dono: aplicar tudo e
fechar os selos do `08-analise-arccc-v1-1-e-forma-de-trabalho.md`):
- D17 (falha ao carregar o motor chega à tela; o módulo expõe a versão do
  contrato) entra em S0.2.
- ~~S0.8 — benchmark versionado.~~ *(feito em 2026-10-01: `benchmarks/`
  ganhou `run_app_benchmarks.py` com os cenários `engine`, `ui` e `files`, um
  processo por cenário, JSON comparável e `--compare` com tolerância e piso de
  ruído; o ramo Windows da leitura de memória não rodou no Linux do agente.
  Linha de base do Linux, 4 núcleos: cópia do canvas 4K 36,6 ms, repintura a
  100% em 4K 40,5 ms, salvar 4K com 10 camadas 3,3 s e +692 MB.)*
- **Defeito achado pelo S0.8 e corrigido** (2026-10-01): abrir um arquivo
  salvo não reproduzia os pixels gravados. `paste_rgba_buffer_on_active_layer`
  truncava em vez de arredondar (azul 14 com alfa 227 voltava 13) e o
  `restore_document` exigia igualdade byte a byte, inclusive no RGB de pixel
  com alfa 0 (que as bordas de pincel suave deixam e o motor não cola). Um
  documento com traço suave na cor padrão não abria ("restauração de pixels
  não corresponde ao arquivo"). Agora colar sobre pixel vazio copia a origem
  exata, a mesclagem arredonda, e o restore ignora o RGB de pixel totalmente
  transparente. `tests/test_document_pixel_fidelity.py`.
- **Defeito achado pelo S0.2 e corrigido** (2026-10-01): abrir um `.lmn`
  pela interface dava `TypeError` desde 2026-09-24. O commit `23c503a` tirou
  `paper_texture_id` de `DocumentManager.new_document` e `open_native_document`
  continuou passando o argumento; o teste do serializador e o do restore rodavam
  separados, e nenhum passava pela ação "Abrir". Mesma lição do item anterior: o
  caminho inteiro precisa de um teste de ponta a ponta
  (`tests/test_document_open_actions.py`).
- ~~D2~~ *(feito em 2026-10-01: a falha ao criar o contexto vira
  `EngineContextError`; a vista recusa e fecha o documento depois da emissão do
  sinal, avisa o usuário com a causa, e as ações de novo documento, abrir
  imagem e abrir `.lmn` só seguem se o contexto ativo do motor é o do
  documento novo. Antes, abrir uma imagem colava os pixels na camada do documento
  aberto e abrir um `.lmn` removia as camadas dele.)* 
- ~~D13~~ *(feito em 2026-10-01: o motor declara o maior lado de canvas
  (`engine/core/canvas/CanvasLimits.hpp`, 16384 px: uma camada cheia são 1 GiB e
  o índice de pixel ainda cabe em 32 bits), recusa com `ValueError` antes de
  alocar (construtor e `resize_canvas`), e o `PixelBuffer` multiplica em
  `size_t`; antes, 32000×32000 estourava `int` (comportamento indefinido).
  "Novo documento", "Tamanho do Canvas", a troca de geometria e "Abrir imagem"
  perguntam o valor ao motor (`ui/core/engine/limits.py`); abrir imagem grande
  demais diz o limite em vez de culpar o arquivo, e o Qt deixa de recusar imagem
  acima de 256 MB que o motor aceita. Mudança visível: "Tamanho do Canvas"
  oferecia até 32000 px e agora oferece 16384; acima de ~23000 px por lado a
  operação já falhava.)*
- ~~D17~~ *(feito em 2026-10-01: o módulo nativo expõe `CONTRACT_VERSION`
  (`bridge/infrastructure/ContractVersion.hpp`); o `AladynBackend` confere com
  `EXPECTED_CONTRACT_VERSION` ao carregar e recusa binário ausente, sem versão
  ou de outra versão, guardando a causa em `load_error` (log de erro, não INFO);
  o `EngineRegistry` guarda o motivo e o `app_runner` mostra um diálogo na
  partida (`report_engine_failure`). O `.pyi` fica preso à versão por
  `tests/golden/bridge_contract.json`: mudar o contrato sem subir a versão
  reprova o teste. Consequência: quem tem um `.pyd` anterior a esta mudança vê o
  aviso e precisa recompilar. Os caminhos de `native_fallback.py`, que toleravam
  binário antigo método a método, deixam de ser alcançáveis com binário real:
  candidatos à remoção.)* **S0.2 completo (D2, D13, D17).**
- **Defeito achado no S0.4 e corrigido** (2026-10-01): o `.pyi` mentia sobre 11
  assinaturas (de 192 métodos). `BezierCurve.set_control_points` aceita 4 `Point2D` e o
  stub dizia 4 `float`; `commit_transform`, `DynamicStabilizer.reset/update/flush/
  get_taper_points`, `end_stroke_raw`, `apply_prepared_geometry` e três métodos do
  `ViewportTransform` tinham argumentos a mais ou a menos. O teste de contrato só
  comparava nomes. `tests/test_pyi_signatures_match_binary.py` lê a assinatura que o
  pybind11 publica e compara quantidade e tipo dos argumentos; o contrato subiu para a
  versão 2.
- Ordem: S0.6 ✅, S0.8 ✅, S0.1–S0.5 e S0.7, S1.
- Os 4 pontos de decisão da Seção 8 do documento 08 foram aplicados: ciclo no
  `AGENTS.md` (5.0), assunto de commit em inglês, limiar de complexidade 20
  com alerta 10, ARCcC v1.1.0 em `02-arquitetura/`.

**Itens ainda abertos da lista de 2026-09-25 (abaixo) ficam fora da linha de
chegada:**
- 13 (147 cores fixas) e 14 (6 funções acima de 20): têm catraca que impede
  piorar e caem quando alguém mexer no arquivo. As funções do serializador
  estão em S2.6. A duplicação da perspectiva curvilínea (Lei do Rio 2) entra
  com a próxima feature de perspectiva.
- 16 (medir a latência com mesa no Windows): medição na máquina do dono.
- 17 (controles sem nome acessível): melhoria contínua.
- 19 (Prova de Cores por documento, gavetas lembradas): decisões de produto
  do dono.

O dono pode puxar qualquer um deles para dentro da linha.

---

## 🔜 Próximas tasks — profissionalizar a base sem feature (registradas em 2026-09-25)

Origem: relatório de estado do projeto pedido pelo usuário em 2026-09-25
(ARCcC e prontidão como produto). Tudo medido no Linux nesta data, na base
`9038c9c`: 925 testes (920 passam, 5 pulados), cobertura de `ui/` 78%. O que
é feature ou decisão de produto (PSD, assinatura, atualização automática,
licença de venda) está na "Rota C" de
`../05-visao-e-futuro/03-benchmark-competitivo-e-rotas-de-produto.md`.
Ordem = ordem recomendada.

1. ~~**Build com o MSVC verificado.**~~ *(feito em 2026-09-25, na máquina do
   dono: motor compilado com o MSVC e suíte com 933 passando, 6 pulados e 1
   falha fora do motor (item 18). O teste do laço, que só passa com o motor
   novo, passou lá.)*
2. ~~**Versão única do produto.**~~ *(feito em 2026-09-25: o app mostrava
   três versões inventadas — título "Lumenia Brush Engine 2.0", splash
   "v2.0", "Sobre" "2.5.0 (Build 2026.08)" — com o produto em 0.2.0. Fonte
   única `ui/infrastructure/app_info.py`; `tests/test_app_version.py` confere
   `pyproject.toml`, `setup.py`, instalador, README, EULA e o "Sobre", e barra
   versão escrita à mão na interface.)*
3. ~~**Avisos de licença de terceiros.**~~ *(feito em 2026-09-25:
   `assets/legal/` com `THIRD_PARTY_NOTICES.txt` (Qt/PySide6, Python, Pillow,
   NumPy, SciPy, pybind11, runtime do MSVC, ícones Lucide/Feather) e os textos
   integrais da LGPLv3 e da GPLv3, que o PySide6 não traz no pacote; o build
   portátil copia os avisos para a raiz da distribuição e os textos de licença
   dos pacotes embutidos para `licenses/`; EULA com a seção 7 nas duas
   línguas. Achado junto: `tests/test_portable_build_contract.py`, que só roda
   no Windows, ainda pedia `--include-package=plugins` depois da mudança para
   `ui/plugins` — corrigido, com uma versão que roda em qualquer sistema.
   Falta a revisão do dono do projeto: o arquivo não é parecer jurídico.)*
4. ~~**Queda do motor deixa rastro.**~~ *(feito em 2026-09-25:
   `ui/infrastructure/logging/crash_log.py` liga o `faulthandler` em
   `logs/native_crash.log`; na abertura seguinte o registro é guardado com
   data (os 5 últimos ficam) e o log principal avisa que a sessão anterior
   caiu. `tests/test_native_crash_log.py` derruba um processo filho de
   verdade.)* Resta, e é decisão (Rota C3): enviar o registro, com
   consentimento, e o minidump do Windows.
5. ~~**Linter Python.**~~ *(feito em 2026-09-25: `[tool.ruff]` no
   `pyproject.toml` (pyflakes e erros de sintaxe), ruff fixado no
   `requirements-dev`, `tests/test_python_lint.py`. Os 237 achados zerados:
   215 imports sem uso, 17 variáveis sem uso — cinco eram cores do tema
   buscadas e não usadas; numa delas a barrinha de arraste
   (`pill_handle.py`) diz seguir o tema e usa cores fixas (fica na
   pendência 13) — e um
   `__init__` duplicado no `.pyi` do `BrushProfile`.)*
6. ~~**Motor sem avisos do compilador.**~~ *(feito em 2026-09-25: os 18
   avisos de `-Wall -Wextra` zerados e `scripts/check_windows_build.py`
   compila com `-Werror` (escalar e AVX2, 68 de 68). Parâmetros que nada
   usavam saíram de `LayerMerger::mergeLayerDown`, da cadeia do
   `cancelTransform` e de `LargeBrushOptimizer::computeAdaptiveStep`, cujo
   comentário prometia "modulação por velocidade" que nunca existiu.)*
   *(Depois, no mesmo dia: `gapClosingPx` e `antiAliasing` do balde, que
   nenhuma tela oferecia e o motor não usava, saíram do contrato inteiro —
   motor, ponte, `.pyi`, backend Python e configurações da ferramenta; uma
   configuração salva com essas chaves é ignorada pelo normalizador. No
   caminho apareceu um terceiro parâmetro ignorado, esse visível: a caixa
   "Todas as Camadas" do balde. O balde lia sempre a imagem composta; agora
   ele e a varinha leem pelo mesmo `LayerSampleSource`
   (`engine/boundary/orchestrator`). `tests/test_bucket_wand_sample_layers.py`
   reprovava no motor antigo.)*
7. ~~**Laço ignora o Anti-Alias.**~~ *(feito em 2026-09-25: cobertura de
   área no motor, 4 linhas de varredura por pixel com a parte horizontal
   exata; sem suavização, o fim de cada trecho deixou de ser inclusivo — o
   laço ganhava uma coluna à direita. `tests/test_lasso_anti_alias.py`.)*
8. ~~**Conferência antes do commit sem depender da memória do agente.**~~
   *(feito em 2026-09-25: `.githooks/pre-commit` chama `scripts/pre_commit.py`,
   que roda em ~13 s as catracas e os testes de governança e, se o commit toca
   o motor, a compilação para Windows. Ativar uma vez por clone:
   `git config core.hooksPath .githooks`. `tests/test_pre_commit_hook.py`.)*
9. ~~**Cobertura da entrada da caneta.**~~ *(feito em 2026-09-25:
   `tests/test_canvas_input_router.py` (23 testes, canvas e motor reais) e
   `tests/test_canvas_overlay_renderer.py` (15). Cobertura medida só com eles:
   `input_router.py` 29% → 84%, `overlay_renderer.py` 7% → 95%.)*
10. ~~**`StrokeOrchestrator.cpp` na parede (447 linhas).**~~ *(feito em
    2026-09-25: o desenho de um segmento (interpolação, histórico,
    rasterização, composição) foi para `StrokeOrchestratorSegment.cpp`; o
    `StrokeOrchestrator.cpp` ficou com a entrada da caneta (236 linhas). Os
    testes de teto passaram a barrar a parede (430–449) em Python e C++, e
    acharam mais um: `tests/test_recording_plugin.py` (434), dividido em motor
    e painel.)*
11. ~~**`RenderWidget` grande demais.**~~ *(feito em 2026-09-25: cada
    colaborador do canvas declara no próprio arquivo o contrato que usa —
    `RouterCanvas` (34 membros), `KeyCanvas` (14), `ViewportCanvas` (16),
    `StrokeCanvas` (11), `CursorCanvas` (11), `TextCanvas` (5), `ToolCanvas` (5)
    — e nenhum importa mais o `RenderWidget`: 0 ciclos entre pastas Python do
    canvas. Com o contrato, o roteador chegou a 443 linhas (parede) e o gancho
    de pre-commit barrou o commit: o teclado foi para `key_router.py`.
    `tests/test_canvas_contracts.py` confere que o `RenderWidget` cumpre os seis
    e é a catraca "subpasta não importa a mãe" do Python; restam 5 pares de
    módulo solto na pasta mãe (`ui/core/tools.py`, `ui/infrastructure/runtime_paths.py`
    e afins), listados no teste. Sete `hasattr` de sinal saíram (205 → 198).)*
    Resta: o contrato do roteador é largo; estreitá-lo é dividir o
    `RenderWidget` por responsabilidade.
12. ~~**`hasattr` em telas e diálogos (205 no total).**~~ *(feito em
    2026-09-25: 205 → 62. Saíram as guardas que nenhum caminho precisava:
    21 sobre o backend nas ferramentas e diálogos (o `EngineBackend` declara
    todos os métodos perguntados), 13 sobre sinais do canvas (garantidos
    pelos contratos do item 11), 9 sobre a API de plugin
    (`IPlugin`/`PluginMetadata` garantem)
    e 100 `hasattr(self, "widget")` em `retranslate_ui`/`_apply_theme`, que só
    saíram onde uma análise do código prova que o widget já existe antes da
    primeira chamada — criação dentro de `if` não conta, e o pytest-qt pegou o
    único caso que a primeira versão da análise errou.)* Restam 62: 24 guardas
    de widget criado condicionalmente ou pela classe base, duck typing de cor
    na ponte, `sys.stdout.reconfigure` e o que os dublês de teste do documento
    ainda não implementam (`get_layer_info`).
13. **Cores fixas: 189 em 42 arquivos** (Lei 5). *Iniciado em 2026-09-25:
    as 42 de `perspective_grid_renderer.py` e `overlay_renderer.py` são cores
    de conteúdo (desenhadas sobre a arte, iguais em todo tema) e foram para
    `ui/infrastructure/theme/overlay_palette.py` com nome
    (`OverlayPalette.HORIZON`, `ANTS_DARK`...). Catraca: 189 → 147 em 40
    arquivos.* Próximos: amostras do seletor de cor (20), `shape_dropdown` (9),
    diálogo de render (8), cursor (7).
14. **Complexidade acima de 20.** *(Iniciado em 2026-09-25. Medida agora
    pelo linter (McCabe, regra C901 do ruff): eram 9 funções acima de 20 (os
    "23" vinham de outra ferramenta, que também conta operadores booleanos).
    Saíram 3 — `handle_pointer_press` (26) e `handle_key_press` (24) em passos
    nomeados, `calculate_path` (22) para `shape_paths.py` (1.440 arrastos
    comparados, idênticos) — e o linter reprova função nova acima de 20.)*
    Restam 6, marcadas `# noqa: C901`: `get_cached_curvilinear_data` (57),
    `DocumentSerializer.read`, `_validate_manifest` e `validate_auxiliary`
    (31 cada), `DocumentSerializer.save` (27), `restore_document` (24).
    **Achado (Lei do Rio 2):** `canvas/math/camera_3d_projector.py` refaz em
    Python `rotate3DBackward`, `curveFromNormal` e `curvilinearCameraRadius`,
    que o `CurvilinearSnapEngine` nativo já tem. Corrigir: expor a malha da
    perspectiva curvilínea pelo motor (uma função que devolve as curvas) e o
    `curvilinear_mesh_builder.py` só desenhar — some a duplicação e a função
    de complexidade 57 junto.
15. ~~**`bridge/infrastructure/`**~~ *(feito em 2026-09-25: a camada existe com
    o `BufferContract.hpp` (validação e cópia de buffers, que morava entre os
    bindings) e a política de erros escrita no README — o motor só lança
    `std::invalid_argument`, que vira `ValueError`; o `try/catch` que repetia
    isso em `transform_rgba_for_profile` saiu. A catraca de camadas do C++
    ganhou a ordem interna da ponte (`infrastructure` → `core` → `boundary`);
    `tests/test_bridge_error_policy.py`.)*
16. ~~**Números sem medição no documento de visão.**~~ *(feito em 2026-09-25:
    o texto agora diz o que foi medido no Linux — traço de 120 amostras em
    19 ms no motor (~0,16 ms por amostra), abertura em ~1 s, 998 testes,
    repositório de 8,6 MB — e diz que a latência com mesa no Windows não foi
    medida.)* Resta medir no Windows com mesa digitalizadora.
17. **Acessibilidade.** *(Iniciado em 2026-09-25: eram 2 widgets com nome
    acessível na janela principal; agora 66. `ui/infrastructure/accessibility.py`
    dá a cada controle sem texto visível a dica traduzida como nome (ou o
    rótulo ligado por `setBuddy`, que os helpers das barras de opções passaram
    a usar), ao montar a janela, ao trocar de idioma e ao abrir cada diálogo.
    `tests/test_accessibility_names.py`.)* Restam sem nome, por não terem dica
    nem rótulo ligado: os botões −/+ dos `CompactSlider` (22), os da barra
    flutuante (12), as amostras de cores recentes (10) e 9 dos 27 deslizantes
    (opções do balde e da varinha).
18. ~~**Teste que só falhava na máquina do dono.**~~ *(feito em 2026-09-25:
    no Windows, `test_recording_plugin_activation` falhava com "Exceptions
    caught in Qt event loop"; no Linux do agente passava. O pytest-qt, instalado
    só lá, reprova exceção levantada dentro de um slot do Qt. O teste usava um
    canvas falso que não era widget, contra o contrato
    (`WorkspaceService.canvas` é `QWidget`). Com o teste corrigido apareceu uma
    queda de verdade: a barra flutuante da gravação deixava o filtro de eventos
    no canvas depois de destruída, e desativar o plugin com o canvas vivo podia
    derrubar o app. Agora a barra solta o canvas quando o painel é desligado;
    o pytest-qt entrou no `requirements-dev` e `tests/test_dev_environment.py`
    falha se ele faltar.)*
19. **Restos já conhecidos.** *(2026-09-25: três feitos; o resto é decisão
    do usuário.)*
    - ~~Gravação sem tradução.~~ 71 chaves `recording.*` nos 4 idiomas; painel
      e barra flutuante se refazem ao trocar o idioma. Os combos guardavam o
      valor no texto (o motor procurava "1080p" no rótulo, a exportação
      procurava "MP4"); agora no dado do item. A suíte passou a pôr cada teste
      em pt_BR (`tests/conftest.py`): sem preferência salva o idioma segue o
      sistema, e os testes que conferem texto reprovavam num sistema em
      inglês (o Linux do agente, um runner do CI).
    - ~~Nome padrão em português.~~ Camada, grupo e documento sem nome vêm de
      `layers.default_name`, `layers.new_group` e `dialogs.untitled_name`
      (`default_layer_name` em `ui/core/document/local_layer.py`). O motor
      cria a camada inicial com o nome fixo "Camada 1" (C++); a ponte dá a ela
      o mesmo nome do documento, sem sujá-lo.
    - ~~`add_panel` conhece os ids `navigator`/`layers`.~~ Continua ligando os
      dois pelo id (levar a ligação aos plugins alargaria o `WorkspaceService`
      em ~10 membros por dois painéis), mas o que eles precisam ter está
      declarado em `PANEL_CONTRACTS` (`ui/core/plugins/panel_ids.py`) e
      `add_panel` recusa, antes de registrar, um widget que não cumpre.
      `tests/test_known_panel_contracts.py`.
    - **Decisão do usuário** (muda o produto ou o formato do arquivo): Prova
      de Cores por documento e salva no arquivo (hoje é uma só, global); lembrar
      as gavetas abertas entre sessões.

---

## ✅ 2026-09-24 — Espaguete desfeito por contrato (sessão Claude Code)

Medido no Linux (Python 3.11, offscreen): 835 testes passam, 5 pulados. CI do
GitHub verde nos 5 jobs no commit `5046cec`. Detalhe e bugs corrigidos nas
mensagens de commit do branch `claude/zealous-galileo-38k67d`; regras novas em
`AGENTS.md` seção 4.2 e `../02-arquitetura/06-contratos-entre-componentes.md`.

**Feito:** estado compartilhado (`ui/core/state`) no lugar de seis cópias da
cor e dos parâmetros do pincel e de quatro caminhos para a ferramenta ativa;
camadas com um caminho só até o motor; canvas, barra secundária e páginas de
opções sem acesso a privados alheios; catraca de acoplamento; README com
dependências medidas nas 62 pastas de código; CI verde.

**Pendências de arquitetura, em ordem de retorno** (números de
`python -m tests.arccc_coupling_metrics --top 8`):

1. ~~**Mixins que se leem por `self`** na `MainWindow` e no
   `WorkspaceContainer`.~~ *Feito em 2026-09-24:* seis colaboradores na casca
   (porta `workspace_port.py`) e quatro no workspace (`WorkspaceLayout`,
   `DocumentViewSync`, `PanelConnections`); papel com fonte única no
   `Document`. Resta: `add_panel` conhece os ids `navigator`/`layers` (o de
   `geometry` saiu com a pendência 11).
2. ~~**Painel avançado do pincel**~~ *(feito em 2026-09-24: cinco seções
   com estado próprio sobre `AdvancedSection`, `BrushEngineWriter` no lugar
   do mixin; comportamento caracterizado nos 23 controles antes e depois,
   idêntico; `tests/test_brush_advanced_panel.py`.)*
3. ~~**Docas**~~ *(feito em 2026-09-24: nenhum acesso a privado entre doca,
   animador, sidebar e gaveta; a doca recebe o widget onde flutua).* Resta:
   a persistência do estado das gavetas existe (`DockStateStore`) mas não
   está ligada ao app (decisão do usuário). *(Os dois painéis avançados agora
   abrem pela `FloatingPanelWindow` com `WorkspaceService.canvas_area_rect`.)*
4. ~~**Menus**~~ *(feito em 2026-09-24: `menu_bar.py` sem `hasattr`,
   `SettingsMenu` extraído; ids canônicos `PanelId` — o menu Janela pedia ids
   que nenhum plugin registrava e 4 dos 5 itens não faziam nada.)*
5. ~~**Telemetria**~~ *(feito em 2026-09-24: `TelemetryTracker` é a fonte
   única; cockpit, painel e diagnóstico são views dele; os 20 medidores e o
   relatório existem uma vez (`telemetry_meters.py`, `telemetry_report.py`);
   o DTO lê a struct nativa sem valor padrão, com teste de contrato. Bugs
   medidos e corrigidos: "Limpar Undo" esvaziava listas privadas e dizia
   "limpa" com a RAM do histórico intacta (agora `clearHistory` nativo via
   `DocumentHistory.clear`); a tela afirmava "AVX2 / SSE2 Ativo" no build
   escalar padrão; o relatório mostrava sempre o motor padrão; o benchmark
   pintava 1000 carimbos na camada do usuário; o painel mostrava o estado do
   quadro anterior.)*
6. ~~**Segundo caminho até o motor**~~ *(feito em 2026-09-24: saíram o
   `BridgeClient`, os comandos em dataclass, `contracts.py`,
   `aladyn_dispatch.py` e `dispatch` do contrato — nenhum chamador em
   produção. O backend avisa `EngineRegistry.notify_document_modified` e o
   `DocumentManager` suja o documento, sem o backend importar o modelo. O
   contexto nativo provisório do boot (`default_doc`) passou a ser liberado
   quando o primeiro documento abre; antes ficava alocado a sessão toda.)*
7. ~~**Arquivos na parede dos 450**~~ *(feito em 2026-09-24: os 5 divididos
   por responsabilidade — gravação (`RecordingActions`, fonte de quadros do
   documento, barra flutuante só com sinais), novo documento
   (`PresetGallery`), temas (`InterfaceTweaksGroup`; raio e fonte agora
   funcionam; filtro Escuros/Claros funciona fora do pt-BR), geometria
   (`NativeGeometrySnap`, `geometry_engine_sync`, `Document.store_*_state`) e
   relatório de testes (mostra o resultado medido da execução em vez de
   "110 testes / 100% / APROVADO" fixos). Censo: 0 na parede.)*
8. ~~**Textos sem `tr()`**~~ *(feito em 2026-09-24: os títulos e rótulos das
   views da barra secundária nascem traduzíveis com `Text(chave, padrão)` e
   trocam com o idioma (28 chaves `secondary_bar.*`; o combo de presets do
   smudge também); as mensagens de status da casca (`ui/boundary/orchestrator`),
   dos comandos de camada, das camadas de ajuste e da barra de status passaram
   por `tr` (69 chaves `status.*` novas). O teste de chaves agora confere
   `tr(...)` e `Text(...)` nos 4 idiomas.)* Resta: nome padrão de camada nova
   ("Camada N", "Novo Grupo") é dado do documento e continua em português.
9. ~~**Pastas sem porta de entrada**~~ *(feito em 2026-09-24: `__init__.py` em
   `ui/core/geometry`, `canvas/renderers`, `canvas/tools`, `canvas/viewport`,
   `dock` e mais 4; saíram `ui/utils` (sem consumidor) e
   `ui/boundary/public_api` (vazia).)*
10. ~~**Papel, DPI e perfil do documento novo**~~ *(feito em 2026-09-24: a
   ação "Novo documento" escrevia o papel direto no motor (segundo escritor,
   além da ativação) e limpava a tela nova — o documento nascia sujo e fechá-lo
   sem mexer pedia para salvar. Agora a ativação leva o papel, o relevo vai
   por `Document.set_paper` e o resultado é o estado inicial. O DPI é campo do
   `Document` e vai no `.lmn` (opcional; arquivo antigo abre com 300). Bug
   medido e corrigido: o backend guardava um perfil de cor só para todos os
   documentos — voltar ao documento A depois de configurar o B mostrava e
   gravava o perfil do B; agora o perfil é por contexto. Abrir o diálogo de
   renderização aplicava o último perfil das preferências ao documento em
   sRGB; agora só mostra. `tests/test_document_profile_and_dpi.py`.)*
   Resta: a Prova de Cores é uma só para todos os documentos e não vai no
   arquivo. *(Diálogos de arquivo e caixas de mensagem: traduzidos em
   2026-09-24, 47 chaves `file_dialogs.*`/`messages.*`; falta o plugin de
   gravação, que não tem nenhuma tradução — ~70 textos.)*
11. ~~**Painel de geometria com cópia própria do estado**~~ *(feito em
   2026-09-24: guias e simetria moram no `GeometryState` (`ui/core/state`);
   canvas, menu, painel e diálogo avançado são views dele, e o controlador do
   canvas é o escritor único no motor e no documento. O painel não recebe mais
   o canvas (`set_render_widget` e 7 `hasattr` saíram) e o diálogo publica só
   o campo editado. Defeitos medidos e corrigidos: a simetria do documento A
   vazava para o B ao escolher uma régua no B; o painel mostrava o documento
   anterior; mudar os segmentos no diálogo desfazia o ângulo arrastado no
   canvas (30° → 90°); ângulo 0 no diálogo era ignorado; quando o diálogo
   ligava a simetria radial e a perspectiva 6P, o painel continuava dizendo
   "Selecione um modo...". `tests/test_geometry_state.py`, 12 testes.)*

---

## ✅ 2026-09-23 — Decisões do usuário aplicadas (sessão Claude/Cowork)

Relatório: `claude/correcoes-e-decisoes-2026-09-22.md` (Claude Project).
Medido no Windows: suíte completa verde (796 testes), `navigator_verify`
com 0 `confirmed_violation`.

- **Promessas falsas viraram funções reais** (decisão: "deixar de prometer e
  desenvolver a função real"):
  - Seleção → Modificar (Expandir, Contrair, Suavizar Borda) no motor
    (`SelectionMorphology.cpp`), com Desfazer.
  - Transformar → Distorcer (4 cantos, homografia no motor; prévia e commit
    coincidem) no painel e na barra secundária.
  - Harmonias na roda de cores (5 regras, marcas no anel, amostras clicáveis).
- **Guardas `hasattr` do grupo A** (11, funções que já existem no binário):
  o plano B continua, mas registra um aviso no log (`native_fallback.nativo_tem`)
  em vez de ficar calado. Grupos B (traço raw vs legado, 3) e C (detector de
  capacidades, 1) mantidos. Travados em `tests/test_river_ratchets.py`.
- Anotações de tipo que o Navigator pedia (`layer`, `doc`).
- `backend_protocols.py` (434, na parede dos 450) dividido: o papel
  SelectionTransform foi para `backend_protocols_selection.py`.
- **Adiado por decisão:** pipeline de cor 16-bit (mexe em tile, compositor,
  desfazer e formato de arquivo).

**Ainda com decisão do usuário:** `Ctrl+E`, ffmpeg no instalador, critério do
gate de sessão longa, processos antigos do Antigravity, `.venv`, remoto do
Navigator.

---

## ✅ 2026-09-22 — Análise completa + correções (sessão Claude/Cowork)

Relatório: `claude/analise-completa-projeto-2026-09-22.md` (Claude Project).
Medido no Windows ao fim da sessão: suíte completa verde (762 testes), `navigator_verify`
com 0 `confirmed_violation` e 0 arquivos na Zona Vermelha.

**Afirmações anteriores corrigidas** (estavam neste documento e no benchmark):
- "100% dos arquivos na Zona Verde (< 450)": falso até hoje -- havia 3 C++ ≥ 450
  sob exceção e ~95 arquivos entre 251 e 449. Os 3 foram divididos hoje.
- "Zero vazamentos" pelo gate P4: `scripts/run_soak_test.py` roda sem nenhum
  widget, um documento, traços de 40 px e desfazer limitado a 30 passos -- o
  platô de memória é garantido pelo próprio anel de desfazer. Continua útil
  como smoke test do motor; o gate de sessão real é
  `scripts/soak_full_session.py` (MainWindow real, camadas, salvar .lmn, MDI).
- Contagens de teste "725"/"659"/"670+": a medida real hoje é a do pytest.

**Corrigido nesta sessão:**
- Binário `.pyd` de 2026-09-05 esquecido em `ui/infrastructure/bridge_client/` (138 vs 185
  atributos) movido para `../build/obsoleto/`.
- `WgpuRustBackend` removido (adaptador de um motor Rust inexistente); teste
  dos Protocols passou a exigir implementação real fora de `EngineBackend`.
- Teste com caminho absoluto `z:\...\.agents\...` (falhava fora desta máquina).
- `render_stroke_preview` restaurado (sumiu do motor em 2026-08-25; o painel
  de pincel mostrava aproximação vetorial) + a prévia agora copia o perfil em
  vez de alterar o pincel em uso.
- 5 varreduras `topLevelWidgets()` → `ui/core/plugins/canvas_access.py`.
- 5 lambdas em sinais de singletons (vazamento + "C++ object already deleted").
- Guardas `hasattr` sobre o motor: 19 → 16 pontos (15 entradas nomeadas) em
  `tests/test_river_ratchets.py` (guarda nova falha o teste).
- 25 chaves de tradução ausentes nos 4 idiomas + teste que impede regressão.
- `except Exception: pass` que escondiam falha de plugin agora registram log.
- CI com Python 3.14 (versão da máquina de desenvolvimento).
- C++ Zona Vermelha: `StrokeOrchestrator.cpp`, `TransformEngine.cpp`,
  `SelectionEngine.cpp` divididos por método; exceções de LOC removidas.
- Suíte: janelas órfãs descartadas entre módulos (≈369 s → ≈110 s).
- Navigator: `verifier.py` (777), `python_semantic.py` (752) e `context.py`
  (512) divididos sem mudar saída (relatório byte a byte idêntico); bump do
  extrator para `xl-contracts-v10` (faltou no commit `f1fa359`).

**Abertos, com decisão do usuário** (ver o relatório no Project):
promessas falsas da interface (Modificar Seleção, "Distorcer", "Harmonias"),
lista final de guardas `hasattr`, faixa amarela 251 vs 300, `Ctrl+E`,
ffmpeg no instalador, execução do gate de sessão longa com artista.
*(Promessas falsas e guardas `hasattr` resolvidas em 2026-09-23, acima.)*

---

## ✅ Resolvido nesta sessão (2026-09-21, rodadas 6 a 14)

Itens de auditoria vertical, código morto, integridade de traço, cursor, fronteira C++ e subsistemas satélites concluídos e homologados:

- **Auditoria Orbital Concêntrica de Subsistemas Satélites (Rodadas 9 a 14)**:
  - Criação e expansão da skill `lumenia-satellite-audit` e documento metodológico `06-auditoria-orbital-decomposta.md` para o modelo de 6 camadas concêntricas e verificação ascendente dos 5 Rios.
  - *Rodada 14 (Descida ao Núcleo C++ e Laço Ascendente dos 5 Rios)*: validação de `BufferContract.hpp` (`checkedRasterBytes`, `validateRasterInput`, `pixelSnapshot`), `DocumentContext::touch()` monótono, invariantes de `TileGrid`, `TileUndoManager`, `Compositor` e `DabRenderer` SIMD. Homologação do fechamento ascendente completo nos 5 Rios (Traço, Câmera/Viewport, Camadas/Histórico, Seleção/Transformação e Cor/Perfis). Suíte dedicada `tests/test_native_core_invariants_and_rivers.py` (9/9 testes verdes).
  - *Rodada 13 (Sincronização Viewport/Navigator e Dirty Tracking de Camadas)*: alinhamento dos ícones SVG de flip no painel Navigator (`flip-vertical` / `flip-horizontal`), emissão idempotente de `cameraChanged` nos setters `flip_x`/`flip_y` de `canvas_compat.py` para sincronização bidirecional, e cobertura completa de dirty tracking (`_mark_document_dirty`) nas 18 operações de camada de `AladynLayerMixin`, geometria, transações e recursos. Suíte dedicada `tests/test_dirty_tracking_layers_and_navigator_flip.py` (7/7 testes verdes).
  - *Rodada 12 (Saneamento dos Botões de Flip e Fronteira Primordial C++)*: alinhamento 1:1 de `btn_fliph`/`btn_flipv` $\to$ `flipHRequested`/`flipVRequested` no Navigator, guard defensivo resiliente em MDI com `hasattr(facade, "set_render_options")` e fallbacks granulares, e dirty tracking em operações nativas (`clear_canvas`, `clear_layer`, `undo`, `redo`, `flood_fill`, `fill_area`, `end_stroke`). Suíte dedicada `tests/test_render_options_and_native_dirty_tracking.py` (6/6 testes verdes).
  - *Rodada 11 (Borda Primordial C++ e Paridade de Menu)*: função canônica `to_native_color_rgba` para coerção polimórfica resiliente de cores, marcação dirty em mutações de raster (fill, delete, transform, paste, flip, rotate), paridade de sinais `strokeStarted`/`strokeFinished` no menu principal com helper `_emit_stroke_wrap` e resolução canônica de cor. Suíte dedicada `tests/test_engine_boundary_color_and_signals.py` (4/4 testes verdes).
  - *Rodadas 9 e 10 (Subsistemas Satélites, Ferramentas e Docks)*: balde de tinta com `active_color` e paridade de sinais `try ... finally`, ciclo de vida simétrico do `TextToolController`, sincronização de previews em Delete e `clear_canvas`, desacoplamento de `PaperLayerWidget` com sinal `paperChanged`, réguas/grade com alias `geometry_controller`, marching ants dinâmicas unificadas no `SelectionToolController` e eliminação do shim `color_wheel.py`.
  - *Salvaguarda ARCcC Invariants*: 100% de conformidade com o teto de 450 LOC por arquivo (Zona Verde) em todos os arquivos modificados. 100% de testes verdes em toda a base (**725 testes passando** com zero falhas).

- **Auditoria de Código Morto & Sombra de Empacotamento (Níveis 1, 2 e 3)**:
  - Nível 1: Remoção de 4 arquivos mortos isolados com zero chamadores (`color_wheel.py`, `dialog.py`, `flood_fill.py`, `IRenderContext.hpp` — commit `c217811`).
  - Nível 2 e 3: Eliminação de sombras geradas por subpacotes com `__init__.py` duplicando módulos de mesmo nome (`icon_svg_catalog`, `dialogs`, `presets` — commit `4d3f254`). Modernização dos inicializadores desktop `Launch_Lumenia.bat` e `Launch_Lumenia_Silent.vbs` para `main.py` (commit `db2b80f`) e remoção segura de shims legados (commit `3cba060`).
- **Desacoplamento de Arquitetura do Viewport (Nível 4)**:
  - Rastreamento pelo "curso do rio" revelou dependência do `OverlayRenderer` em atributos privados de `CanvasCompatMixin` (`_selection_path`, `_shape_preview_points`).
  - Refatorado para propriedades públicas limpas, prevenindo a quebra do desenho de seleções e formas na tela e eliminando o acoplamento espúrio (commit `f9980ae`).
- **Saneamento do Sistema de Pincéis**:
  - Eliminação de duplo despacho concorrente entre `BrushSettingsController`, backend e viewport widgets. Estado canônico centralizado no `EngineBackend` com propagação reativa unidirecional.
  - Correção na escala linear de textura/relevo (`set_brush_grain_contrast`) para o motor nativo (commit `215646f`).
- **Preservação de Buffer na Ferramenta de Texto**:
  - Correção de ciclo de vida do `QImage` temporário em `_apply_rendered_text`, retendo a referência durante o dump de bytes RGBA para evitar use-after-free/corrupção de raster (commit `b0a83fe`).
- **Saneamento Completo do Sistema de Cursor**:
  - `RenderWidget.brush_size` como `@property` reativa: recalcula `_cached_brush_radius` e emite dirty rect imediato, redimensionando o anel sob o ponteiro sem requerer clique.
  - Hotspot exato e alias do conta-gotas (`"eyedropper": "eyedrop"`, hotspot `(2, 22)`).
  - Suporte ao anel geométrico na ferramenta borrador (`"smudge"`).
  - Cursores especializados para formas (`CrossCursor`) e texto (`IBeamCursor`).
  - Feedback tátil em Pan (`ClosedHandCursor`) e Zoom Drag (`SizeVerCursor`) com restauração via `invalidate_cursor_cache()`.
  - Homologado em `tests/test_canvas_cursor_interactions.py` (5/5 passed, commit `7b59079`).
- **Saneamento Profundo do Sistema de Traço (Stroke Pipeline)**:
  - Rastreamento ponta a ponta: hardware $\to$ `InputRouter` $\to$ `CanvasStrokePipeline` $\to$ `AladynStrokeMixin` $\to$ Facade/Orchestrator C++ $\to$ `TileGrid` $\to$ Viewport.
  - *Tap isolado (single-click sem arrasto / sarda)*: fallback analítico de bounding box em `end_stroke` quando `totalCatchupDirty` for vazio, garantindo renderização instantânea do ponto.
  - *Ghosting de cursor*: atualização contínua de `widget._last_rendered_cursor_rect = cur_cursor_rect` frame a frame em `paint_stroke`.
  - *Tilt e Twist*: propagação completa de inclinação (`xTilt`, `yTilt`) e rotação da caneta física até o motor C++.
  - Validação de estabilizador WMA (0% a 98%), 8 direções cardeais e reversão brusca de 180° (U-turns).
  - Homologado em `tests/test_stroke_pipeline_integrity.py` (5/5 passed), preservando 100% dos testes dourados de caracterização (`test_stroke_characterization.py`, 31/31 passed). Commit `f69be00`. Suíte global em **659 testes passando**.

## ✅ Resolvido em sessões anteriores (2026-09-20, rodadas 1 a 5)

Estes três itens estavam listados como P0/P1 até esta rodada. Detalhes de
cada implementação estão no changelog do `../README.md`.

- **CI restaurada** — `.github/workflows/ci.yml` criado, com jobs `windows`
  (matriz 3.11/3.12/3.13, build `--simd scalar`) e `windows-avx2` (F-020,
  build `--simd avx2` com verificação explícita de carregamento do módulo).
- **Teste de regressão `.pyi` × binário compilado** —
  `tests/test_pyi_contract_matches_binary.py` criado, baseado em `ast`
  (não regex), comparando bidirecionalmente o contrato declarado com o
  módulo compilado. Aproveitado para remover 2 declarações mortas do
  `.pyi` (`get_pixel_data_size`, `get_display_pixel_data_size`).
- **`EngineBackend` dividido em protocolos por papel** —
  `ui/core/engine/backend_protocols.py` criado, com 11 `Protocol`s
  (`CoreLifecycleProtocol`, `StrokeProtocol`, `BrushProtocol`,
  `CanvasResourceProtocol`, `LayerProtocol`, `SelectionTransformProtocol`,
  `GeometryProtocol`, `TelemetryProtocol`, `ColorProtocol`,
  `RenderPipelineProtocol`, `HistoryProtocol`) cobrindo os 178 métodos de
  `EngineBackend`, gerados via `ast` a partir da classe real (não
  transcritos à mão) e verificados por `tests/test_engine_backend_protocols.py`
  (`isinstance()` de `AladynBackend` e `WgpuRustBackend` contra os 11
  papeis). **Importante:** isto é aditivo — `EngineBackend` continua
  existindo como contrato universal, sem nenhum método removido ou
  movido. O ganho é permitir testar/implementar um papel isoladamente
  sem precisar de um backend inteiro; não reduz, por si só, o tamanho de
  `EngineBackend` nem os `hasattr` do adaptador (ver P1 abaixo).

## 🟡 P1 — alto retorno, esforço baixo/médio

### Guardas `hasattr(self._facade, ...)` — investigados, fechados como não aplicável
107 → 12 entre 2026-09-15 e 2026-09-20 (queda de 89%). Os 12 restantes foram
investigados individualmente em 2026-09-20 (terceira rodada) e **não são dívida
de código defensivo por desconfiança de contrato** — são fallback deliberado
e documentado para quando o `.pyd` compilado está desatualizado (não tem os
métodos mais novos ainda). Prova: o próprio docstring de
`tests/test_stroke_characterization.py` descreve o caminho `facade` legado
(`begin_stroke`/`update_stroke`/`end_stroke`) como "fallback para builds
nativas antigas", e o teste mede os dois caminhos (`raw` e `facade`) de
propósito porque uma correção no estabilizador precisa tocar
`StrokeOrchestrator.cpp` **e** `PaintEngineFacade.cpp`. Os outros 8
(`get_display_pixel_buffer`/`get_best_lod_level` em `aladyn.py`, 5 métodos
de curvilinear/perspective em `aladyn_geometry_mixin.py`) seguem o mesmo
formato: recursos mais novos que degradam graciosamente se o binário ainda
não foi recompilado. O teste `.pyi`×binário (ver acima) garante que o
*contrato declarado* bate com o binário *no momento do teste* — não impede
rodar código novo contra um `.pyd` ainda não recompilado, que é exatamente o
cenário que esses guards protegem. **Decisão do usuário (2026-09-20):**
manter o código como está; fechar este item como investigado, não como
removido. `02-simplificacao-da-ponte.md` (passo 4) foi corrigido para
refletir isso.

> **Correção (2026-09-20, quarta rodada):** um dos 12, `get_nearest_primary_grid_curve`,
> não era de fato um fallback ativo — investigação mais profunda (ver item
> abaixo) mostrou que `GeometryToolController` sempre usa a versão pura-Python
> (`GeometrySnappingEngine.find_nearest_primary_grid_curve`) para o hover do
> grid curvilinear, e nunca chama a versão nativa. Diferente dos outros 11
> (que são exercitados de verdade pelo caminho `_snap_use_native_*`), este
> era órfão puro. Foi removido junto com os outros 5 métodos mortos abaixo.
> Restam 11 guards legítimos, não 12.

### `EngineBackend` — 178 → 172 métodos, 6 mortos removidos (2026-09-20, quarta rodada)
A divisão em protocolos (ver acima) nomeia o recorte natural, mas por si só
não reduz `EngineBackend`. A frase original aqui ("avaliar se as
implementações concretas podem delegar a papeis internamente") era
tecnicamente incoerente — `Protocol` do `typing` é tipagem estrutural pura,
sem implementação para delegar a. Corrigido: o usuário pediu investigar
duplicatas/mortos reais antes de decidir qualquer coisa.

**Método:** `navigator_references` (`calls`) no arquivo inteiro só achou 14
relações para uma classe de 178 métodos muito usada — limitação conhecida do
resolvedor Python do Navigator para `self.atributo.metodo(...)` quando o tipo
do atributo não é inferido estaticamente. Abandonado em favor de varredura
direta por regex nos 178 nomes contra `ui/`, `plugins/` e `tests/` (excluindo
os arquivos de definição e `ui/infrastructure/bridge_client/`), com verificação manual de
cada candidato antes de confirmar — inclusive dois falsos positivos do
próprio script (`available` é `@property`, acessado sem parênteses; `flood_fill`
é chamado internamente por `fill_area`) e um bug de regex (`-SimpleMatch` do
PowerShell tratando `|` como caractere literal, escondendo os chamadores reais
de `snap_perspective`/`set_curvilinear_guide_config`/`get_curvilinear_candidates`).

**6 métodos removidos** de `backend.py`, `backend_protocols.py` e do mixin
correspondente (nada tocado no `.pyd` nativo — a Lei de Isolamento do Binário
C++ continua intacta; o binário pode manter os símbolos, só a superfície
Python some), todos com 0 chamadores em `ui/`, `plugins/` ou `tests/`:

- `set_group_pass_through` — duplicata: o modo de blend "Pass Through" de
  grupo já é aplicado via `set_layer_blend_mode` (valor 7), o caminho
  genérico usado por `layers_plugin/header.py`. O setter dedicado nunca era
  chamado por nada.
- `set_canvas_grain_enabled` — duplicata: o "enabled" real do grain de
  papel/canvas já viaja como parâmetro de `set_canvas_paper_state(...)`
  (chamado por `layers_plugin/paper.py`); o setter dedicado nunca era chamado.
- `set_brush_grain_invert` — duplicata: o checkbox "Inverter Topografia" da
  UI (`brush_texture_section.py`) está ligado a `invertHeightChanged` →
  `_on_brush_invert` → `backend.set_brush_invert_height(...)` (outro método,
  em uso). A própria implementação antiga fazia
  `self._facade.get_brush_profile().brush_grain_invert = bool(invert)` —
  exatamente o que `apply_brush_preset_dict` (tabela única, ver Passo 2 de
  `02-simplificacao-da-ponte.md`) já faz via `setattr` genérico no perfil
  nativo. Redundante desde a unificação da tabela.
- `get_selection_contour_segments` — órfão: implementado, delegava pro
  facade, mas nenhum chamador em nenhum lugar.
- `replace_document_context` — órfão: peça de um fluxo MDI de "preparar
  documento em background e trocar atomicamente" (`uid`/`prepared_uid`) que
  nunca foi conectado — nada no repositório cria um `prepared_uid`.
- `get_nearest_primary_grid_curve` — órfão (ver correção acima): o guard
  `hasattr` existia mas nunca era exercitado, porque `GeometryToolController`
  sempre usa a versão Python pura (`GeometrySnappingEngine.find_nearest_primary_grid_curve`).

**Não removido, cluster relacionado mas fora de escopo:** `get_redo_count`,
`can_redo`, `get_undo_count`, `can_undo`, `get_undo_memory_limit_mb`,
`get_undo_max_steps` — implementados e testados no nível do motor
(`get_redo_count` inclusive tem um chamador interno real, `can_redo()` no
próprio mixin), mas os itens de menu Undo/Redo nunca usam esses métodos
para habilitar/desabilitar — ficam sempre habilitados, e `undo()`/`redo()`
só retornam `False` em silêncio quando não há o que fazer. Não é código
morto (há cobertura de teste real para a maioria), é uma decisão de
produto/UX (mostrar ou não o estado do histórico na UI) que não foi tomada
nesta rodada.

**Validado:** `ast.parse` nos 7 arquivos tocados, `test_engine_backend_protocols.py` + `test_pyi_contract_matches_binary.py` +
`test_brush_param_contract.py` isolados e a suíte completa, todos verdes no
Windows do usuário após a remoção.

## 🟢 P2 — menor urgência — Triagem concluída e fechada (2026-09-20, quinta rodada)

- **Triagem completa dos ~184 achados `suspicious` do Navigator**:
  - **Causa raiz diagnosticada:** O extrator AST do Navigator (`python_semantic.py:165-184`) extrai arestas `annotates` unicamente dos argumentos de funções (`node.args.args`). Ele descarta variáveis locais anotadas (`ast.AnnAssign`, ex: `w: "RenderWidget" = self.widget`, `layer: LocalLayer = ...`) e subscritos (`Optional[T]`, `list[T]`).
  - **Estado real do código Lumenia:** A grande maioria dos pontos sinalizados (como `input_router.py:136`, `layer_manager.py:207,214`, `history.py:43`, `serializer.py:59`, `shortcut_registry.py:14`) **já possuía anotação estática correta** no código-fonte.
  - **Anotações estritas aplicadas:** Nos locais de produção legítimos identificados com 100% de pertinência a uma única classe (`aladyn_brush_mixin.py`: `prof: "BrushProfile"`, `c_tex: "CanvasTexture"`; `aladyn_resources_mixin.py`: `canvas: "CanvasTexture"`; `main_window_recovery.py`: `document: Document`; `ui/core/document/manager.py`: `doc: Document`), as anotações foram devidamente inseridas respeitando o protocolo estrito.
  - **Conclusão:** Seguindo expressamente o `03-protocolo-do-navigator.md`, nenhum comportamento de runtime foi alterado para mascarar limitações estáticas do analisador. O item P2 está formalmente triado, documentado e encerrado.

## ⚪ P4 — cobertura que nunca existiu — Gate formalizado e validado (2026-09-20, quinta rodada)

- **Portão de Teste de Sessão Longa e Detecção de Vazamentos formalizado e aprovado**:
  - **Critérios formais estabelecidos:** Embasados na literatura de engenharia desktop do Krita e Blender, definidos em `04-testes-e-qualidade.md`:
    1. $\Delta \text{GDI} == 0$ (tolerância zero para vazamentos de GDI handles no Windows).
    2. $\Delta \text{Handles} \le 5$ (estabilidade de handles do SO).
    3. $\text{Drift} \le 0.05 \text{ MB} / 100 \text{ ciclos}$ na fase de platô (após aquecimento do anel de Undo e cache de tiles).
  - **Harness de estresse headless criado:** `scripts/run_soak_test.py` simula centenas de ciclos de pintura interpolada, variações de dinâmica e transações de histórico em modo offscreen com medição direta via `user32.dll!GetGuiResources` e `psapi.dll!GetProcessMemoryInfo`.
  - **Resultado da validação:** Bateria de 350 ciclos (180 warmup + 170 platô) executada e **100% APROVADA**: $\Delta \text{GDI} = 0$, $\Delta \text{Handles} = 0$, Drift de Memória Privada = $+0.0000 \text{ MB} / 100 \text{ ciclos}$.
  - **Monitor de sessão com artista integrado:** `scripts/monitor_session.ps1` recebeu parâmetro `-Analyze <csv>` para processamento pós-sessão de desenho humano e emissão automática do laudo do Gate.

---

## Como este documento se relaciona com os outros

- `02-simplificacao-da-ponte.md` — o *como* dos itens P1 acima (guardas e
  protocolos por papel).
- `03-protocolo-do-navigator.md` — leitura obrigatória antes de interpretar
  qualquer número de `suspicious`/`confirmed_violation` citado aqui.
- `04-testes-e-qualidade.md` — como rodar a suíte que valida qualquer mudança
  feita a partir deste documento.
- `05-fluxo-lumenia-navigator.md` — o método geral de trabalhar com o Navigator
  ao longo de uma sessão de correção.
- `../historico/` — auditorias fechadas que geraram os números-base citados
  aqui (F-001 a F-031). Não são pendência; são proveniência.
