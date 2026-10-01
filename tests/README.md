# `tests/` — suíte automatizada

**Responsabilidade:** provar o comportamento da aplicação e do motor e travar as regras de arquitetura (catracas ARCcC).

## Porta de entrada

`python -m pytest` (suíte completa) ou `python tests/run_all_tests.py` (runner com relatório e `--junit`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote da suíte. |
| `conftest.py` | Keep application preferences and recovery files out of the real user profile; fixture `qapp` único; liga `LUMENIA_DISABLE_OPENGL=1` (a plataforma offscreen não tem OpenGL e o widget GL do canvas virava um no-op de pintura nos testes). |
| `main_window_fixture.py` | Acesso compartilhado à MainWindow dos testes de integração. |
| `qt_windows.py` | Enumeração segura das janelas de topo do Qt nos testes. |
| `run_all_tests.py` | Runner da suíte: executa tudo (ou uma suíte nomeada) com saída UTF-8 no Windows, cobertura e `--junit` para o relatório de testes. |
| `persistence_doubles.py` | Dublês da gravação: um motor que responde o que `capture_document` pergunta (instantâneo com blocos de tiles vazios e válidos), sem o módulo nativo. |
| `recording_doubles.py` | Dublês compartilhados pelos testes do plugin de gravação (canvas, backend, workspace e motor de teste). |
| `arccc_coupling_metrics.py` | Mede, arquivo por arquivo, os padrões de acoplamento que transformaram a UI em espaguete, e mantém a catraca (`arccc_coupling_baseline.json`) usada por `tests/test_arccc_coupling_ratchet.py`. |
| `arccc_identifier_language.py` | Conta identificadores com palavra em português por arquivo e mantém a catraca `arccc_identifier_baseline.json` (seção 14 do ARCcC). |
| `arccc_governance_rules.py` | FONTE ÚNICA das regras quantitativas ARCcC usadas pelos testes de governança. |
| `arccc_package_docs.py` | Documentação por pasta (ARCcC): TODA pasta do repositório tem README.md. |
| `test_accessibility_names.py` | Nomes acessíveis: botão só com ícone e controle deslizante recebem a dica ou o rótulo ligado como nome, acompanham a troca de idioma e não sobrescrevem nome dado à mão; na janela principal nenhum controle com dica fica sem nome. |
| `test_advanced_geometry_dialog.py` | Tests for Phase 3: AdvancedGeometryDialog ARCcC v2 decomposition. |
| `test_app_benchmark_runner.py` | O benchmark de aplicação exporta resultado comparável: formato, comparação e uma rodada rápida (S0.8). |
| `test_app_version.py` | A versão do produto tem fonte única (`ui/infrastructure/app_info.py`): confere `pyproject.toml`, `setup.py`, instalador, README, EULA e a janela "Sobre", e barra versão escrita à mão na interface. |
| `test_arccc_architecture_invariants.py` | Guardrail de Governança Arquitetural ARCcC (Atomic Recursive Componentization by Contract). |
| `test_arccc_coupling_ratchet.py` | Catraca de acoplamento da UI: nenhum arquivo de ui/ (plugins incluídos) pode ganhar mais `hasattr`, `getattr("literal")`, acesso a privado alheio, `except` silencioso, import de `ui.plugins.*` fora dos plugins e do carregador, pedido do motor ao registro global (`get_backend()`) ou importação que contorna a porta do pacote do que já tinha. |
| `test_arccc_cpp_and_docs_governance.py` | Extensao do Guardrail de Governanca ARCcC para a camada nativa (C++). |
| `test_arccc_cxx_layers.py` | Camadas do pilar C++: sem ciclo de pasta, subpasta sem incluir a mãe, inclusão só para baixo (utils → infrastructure → core em ordem → orchestrator → public-api) e a ponte só por `AladynEngine.hpp`. |
| `test_arccc_identifier_language_ratchet.py` | Catraca de idioma: nenhum arquivo ganha identificador com palavra em português. |
| `test_arccc_package_docs.py` | Toda pasta do repositório tem README com arquivos e dependências verdadeiros. |
| `test_arccc_root_layout.py` | Raiz reservada aos pilares (`ui/`, `bridge/`, `engine/`), arquivos de build/entrada e a exceção declarada (`tests/`, `docs/`, `assets/`, `scripts/`, `benchmarks/`); plugins só em `ui/plugins/`. |
| `test_backend_capabilities.py` | Contrato de capacidades reais entre a UI e os backends de pintura. |
| `test_dab_core_native.py` | Roda o harness nativo `tests/native/dab_core_checks.cpp`: o núcleo comum dos motores de pincel (pegada do dab contra uma varredura bruta, permissão de seleção e recorte, alfa over, queda da ponta) e o codec de tiles do arquivo, sem a ponte; mutações do corte de tiles, do intervalo da linha e do recorte o reprovam. |
| `test_blend_pixel_pins.py` | `blendPixel` dá os mesmos pixels em todo modo × gama × profundidade: roda o harness nativo `tests/native/blend_pixel_pins.cpp` (52 combinações de 4096 casos, hashes gravados antes de dividir a função de complexidade 32); mutações da equação Add e do atalho sRGB o reprovam. |
| `test_bridge_gil_policy.py` | A ponte só solta o GIL onde a política (`bridge/README.md`, "Política do GIL") permite: conta as liberações em `core/bindings/` e reprova uma que não esteja listada. |
| `test_bridge_contract_version.py` | O contrato da ponte tem versão: o binário de outra versão, sem versão ou que não importa é recusado com a causa; o registro guarda o motivo; o usuário é avisado na partida; o `.pyi` fica preso à versão (S0.2, D17). |
| `test_bridge_error_policy.py` | Política de erros da ponte: entrada inválida no motor e buffer fora das dimensões viram `ValueError`, sem `try/catch` repetido nos bindings. |
| `test_brush_advanced_panel.py` | Painel avançado do pincel: seções com estado próprio e dois caminhos claros. |
| `test_brush_curves_state.py` | As curvas Bézier do pincel moram no `BrushState` e só o `BrushEngineSync` as escreve no motor: estado, sincronizador (inclui preset e troca de documento), janela de curvas sem motor e trava de segundo escritor (S0.4, D5). |
| `test_brush_engines_characterization.py` | Caracterização de pixel dos 9 motores de pincel (S0.6): 12 variações por motor, 108 pinos (traço simples, trava de alfa, seleção, máscara de recorte; e as formas de pincel que nenhum pino alcançava: texturas, elipse girada, dureza 0 e 1, modos de dab, parâmetros de cada motor); uma tabela diz quais motores ignoram cada variação. |
| `test_brush_panel_structure.py` | BrushSettingsPanel e seus componentes como views do BrushState. |
| `test_brush_param_contract.py` | Contrato dos parâmetros de pincel — o motor define, a interface exibe. |
| `test_brush_presets_catalog.py` | Unit tests for Camada 4 - Fase 1: Modularização do Catálogo de Presets de Pincéis. |
| `test_brush_state.py` | Contrato de ui/core/state: BrushState (fonte única) e BrushEngineSync (único caminho ao motor). |
| `test_bucket_wand_sample_layers.py` | Balde e varinha: "Todas as Camadas" decide se a região vem da composição ou só da camada ativa (o balde ignorava a opção até 2026-09-25). |
| `test_buffer_contract.py` | Snapshots survive native mutations/destruction; malformed inputs never mutate. |
| `test_canonical_enums_contract.py` | Contrato dos enums canonicos de Simetria e Reguas -- o motor define, a interface consome. |
| `test_canvas_contracts.py` | Contratos dos colaboradores do canvas (`RouterCanvas`, `ViewportCanvas`, `StrokeCanvas`, `CursorCanvas`, `TextCanvas`, `ToolCanvas`) cumpridos pelo `RenderWidget`, e catraca "subpasta não importa a mãe" no Python. |
| `test_canvas_cursor_interactions.py` | Testes de Regressão e Contrato para o Sistema de Cursor do Canvas (ARCcC v2) Valida o comportamento dos cursores de viewport, renderizadores de ferramentas, feedback tátil de pan/zoom e sincronização reativa do raio de pincel. |
| `test_canvas_input_router.py` | Entrada da caneta e do teclado no canvas (`CanvasInputRouter`) com o `RenderWidget` e o motor reais: pan, zoom por arraste, conta-gotas, balde, varinha, seleções, laço, formas, transformação, traço (ponta borracha, linha com Shift) e teclas. |
| `test_canvas_limit_contract.py` | Um só limite de canvas, declarado pelo motor: ele recusa acima do limite antes de alocar, os diálogos oferecem exatamente esse valor e abrir imagem grande demais diz o limite (S0.2, D13). |
| `test_canvas_overlay_renderer.py` | Sobreposições do canvas (`OverlayRenderer`) desenhadas num QImage: formigas da seleção, prévias de seleção e laço, alças da transformação e do Distorcer, prévia de formas e lupa do conta-gotas. |
| `test_color_harmony.py` | Harmonias no painel "Cores & Harmonias" -- 2026-09-23. |
| `test_color_management_cms.py` | Test Suite: LittleCMS Professional Color Management, ICC Profiles, Soft-Proofing & LMN Persistence. |
| `test_compositing_characterization.py` | Teste de caracterizacao da composicao: fixa o resultado ATUAL em pixels. |
| `test_config_manager.py` | Unit Tests for ConfigManager (Lumenia V2 / ARCcC) Valida a persistência em arquivo JSON, isolamento em modo de testes (in-memory), atualização atômica, emissão de sinais e migração transparente do QSettings. |
| `test_config_schema.py` | Config migration and preservation across incompatible application versions. |
| `test_default_layer_names.py` | Nome padrão de camada, grupo e documento no idioma da interface (`layers.default_name`, `layers.new_group`, `dialogs.untitled_name`), e a camada inicial do motor com o mesmo nome do documento. |
| `test_dependency_lock_contract.py` | O lock de dependências do Windows fixa cada pacote resolvido, com hash. |
| `test_dev_environment.py` | O ambiente da suíte é o do `requirements-dev`: o pytest-qt precisa estar ativo, senão exceção dentro de slot do Qt passa em silêncio (diferença entre o Linux do agente e o Windows do dono em 2026-09-25). |
| `test_dialogs_i18n.py` | Test Suite: Dialogs & Configuration I18n Retranslation Valida se todos os diálogos de preferências e configurações de sistema acompanham a mudança de idioma em tempo real (pt_BR, en_US, es_ES, ja_JP). |
| `test_dialogs_theme_and_docs.py` | Diálogos principais reagem à troca de tema e de idioma; guia do usuário nos 4 idiomas. |
| `test_dirty_tracking_layers_and_navigator_flip.py` | Sincronização viewport/navegador (incluindo espelhamento) e marcação de alterações nas camadas. |
| `test_dock_system_structure.py` | Comprehensive unit tests for Camada 3 - Fase 3: Dock System Decomposition. |
| `test_document_close_releases_memory.py` | Fechar um documento libera o documento e os widgets da aba. |
| `test_document_actions_saving.py` | Salvar pela interface (S1.2): começa na hora e o documento só fica limpo com o arquivo gravado e conferido; edição feita durante a gravação o mantém sujo; falha mantém o documento aberto e sujo e avisa; "salvar e fechar" só fecha depois do arquivo; sair espera a gravação e não sai por documento não salvo; um segundo Ctrl+S antes do arquivo existir não pede nome de novo; fechar durante a gravação é inofensivo. |
| `test_document_format_fuzz.py` | Deterministic malformed-file fuzzing for the untrusted LMN reader. |
| `test_document_format_v3.py` | O `.lmn` v3 (S1.2): camada = bloco de tiles, abre aos mesmos pixels visíveis e propriedades; v2 com payload cru escrito à mão segue abrindo e salvar de novo vira v3; o arquivo custa o que está pintado (8 camadas 4000×3000 vazias: 24 bytes cada); o leitor recusa payload mentiroso e a restauração recusa bloco que não bate; e a segunda metade de salvar roda em outra thread enquanto se pinta e grava o documento como estava na captura. |
| `test_document_history_integration.py` | Exercise native pixels and document UIDs in the same history timeline. |
| `test_document_open_actions.py` | As ações que abrem documentos: abrir `.lmn` funciona (quebrado de 24/09 a 01/10 por um argumento removido) e o que o motor não consegue hospedar é recusado sem tocar o documento aberto (S0.2, D2). |
| `test_document_pixel_fidelity.py` | Abrir um documento salvo reproduz os pixels gravados: colar sobre camada vazia é exato e o restore ignora o RGB de pixel transparente. |
| `test_document_profile_and_dpi.py` | Perfil de cor por documento, DPI no Document e o fluxo "Novo documento". |
| `test_document_loader.py` | Abrir sem travar a interface (S1.2): os pixels que saem são os que entraram, atravessando a thread; o trabalhador não precisa de documento nem de contexto do motor; arquivo ilegível avisa e não abre nada; o laço de eventos segue durante uma leitura lenta; arquivo v1/v2 ainda abre e a ação termina no mesmo documento que o artista salvou. |
| `test_document_saver.py` | A gravação em segundo plano (S1.2): callback na thread da interface e escrita noutra, uma por vez e em ordem, o laço de eventos não para durante uma escrita lenta (maior intervalo < 50 ms), falha chega a quem pediu, callback com defeito não derruba a fila, `wait_idle`. |
| `test_document_serializer_integrity.py` | Regressões de integridade do formato editável .lmn. |
| `test_document_v2.py` | Native LMN v2 persistence, migrations and recovery failure regressions. |
| `test_display_region.py` | A tela pede ao motor o retângulo que pinta, não o canvas inteiro (S1.1, D4): a região é o mesmo recorte do buffer inteiro (com e sem perfil de cor), fora do canvas é recusada, e a repintura da viewport (zoom inteiro e fracionado, com rotação, tela cheia ou parcial) desenha os mesmos pixels que o canvas inteiro desenhava, sem copiá-lo. |
| `test_engine_backend_protocols.py` | Prova, em runtime, que os Protocols de ui.core.engine.backend_protocols sao cortes fieis de EngineBackend E que o backend concreto (AladynBackend) implementa de fato cada papel. |
| `test_engine_benchmark_runner.py` | O runner de benchmarks do motor exporta a linha de base em formato legível por máquina. |
| `test_engine_boundary_color_and_signals.py` | Test Engine Boundary Round 11 — Validação da Fronteira Nativa C++ / Python. |
| `test_engine_document_boundary.py` | Fronteira motor ↔ documento: um caminho só, sem o motor conhecer o modelo. |
| `test_engine_type_contract.py` | `EngineType` é o enum canônico do motor de pincel: mesmos membros e valores do nativo, e nenhum número solto de motor em `ui/` (S0.1, D1). |
| `test_floating_toolbar_structure.py` | Testes de Regressão e Contrato para a Decomposição da Fase 2 da Camada 5 (ARCcC v2) Valida o desacoplamento de ToolbarLivePreview, ToolToggleCard e FloatingToolbarSettingsDialog. |
| `test_fullscreen_mode.py` | Tela cheia pelo F11 e pelo menu: entrar, sair e restaurar o estado anterior da janela. |
| `test_geometry_c35_native_anchor.py` | Regressao Fase C3.5 (refinamento) -- ver claude/fase-c3-consolidacao-snap-nativo.md no projeto Lumenia (Projects tool) para o diagnostico completo. |
| `test_geometry_d0_snap_foundation.py` | Regressao Fase D0 (redesign do motor de snap) -- ver claude/proposta-redesign-motor-snap-guias.md no projeto Lumenia (Projects tool) para o diagnostico e desenho completos. |
| `test_geometry_history.py` | Geometry must keep earlier native history, selection and MDI isolation. |
| `test_geometry_state.py` | GeometryState: guias e simetria com uma cópia só (painel, diálogo e canvas são views). |
| `test_geometry_structure.py` | Comprehensive unit tests for Camada 3 - Fase 1: Geometric Decomposition. |
| `test_geometry_symmetry.py` | Modos de simetria, espelho vertical no traço, snap de régua reta e curvilínea, diálogos de geometria. |
| `test_giant_brush_smoothness_and_throughput.py` | Pincéis gigantes: suavidade do falloff analítico e vazão do `LargeBrushOptimizer`. |
| `test_hardcoded_colors_ratchet.py` | Catraca da Lei 5 (zero hardcode de cores). |
| `test_history_io_failures.py` | Real C++ I/O, codec and multi-tile history failure scenarios (no Python mocks). |
| `test_i18n_keys_exist.py` | Toda chave literal passada a tr(...) ou Text(...) em ui/ (plugins incluídos) existe nos 4 locales. |
| `test_i18n_localization.py` | Testes Unitários da Infraestrutura de Internacionalização (i18n) — Lumenia V2 (ARCcC). |
| `test_i18n_system.py` | Unit Tests for I18nManager & Internationalization System (Lumenia V2 / ARCcC) Valida a detecção automática do idioma do SO, fallback universal para en_US, interpolação dinâmica de parâmetros e hot-swap em tempo real sem restart. |
| `test_known_panel_contracts.py` | Painéis que o workspace liga pelo id (`navigator`, `layers`): os reais cumprem `PANEL_CONTRACTS` e `add_panel` recusa um widget que não cumpre, sem desregistrar o anterior. |
| `test_lasso_anti_alias.py` | Laço: o Anti-Alias da barra suaviza a borda (cobertura de área igual à do polígono) e, sem ele, o quadrado seleciona exatamente os seus pixels. |
| `test_layer_blend_mode_contract.py` | Contrato do enum canonico de modo de mesclagem de camadas -- o motor define, a interface consome. |
| `test_layer_drop_plan.py` | Arrastar e soltar na árvore de camadas: onde as camadas movidas ficam. |
| `test_layer_manager_history.py` | Histórico estrutural do gerenciador de camadas: renomear/reordenar preservam uids; camada 0 nunca vira máscara de recorte. |
| `test_layer_projection_divergence.py` | Deteccao de ordem divergente entre Document e motor (Achado #5). |
| `test_layer_property_registry.py` | Contrato da tabela de propriedades de camada (S2.2): uma propriedade acrescentada só em `layer_properties.TABLE` nasce com o padrão, é lida do registro, chega ao motor e a quem escuta, é herdada ao duplicar, volta pelo histórico, vai para o arquivo, é validada e é reenviada ao motor ao confirmar a transação; tirar a propriedade de qualquer consumidor (os oito, medido um a um) reprova ao menos um teste. |
| `test_layer_merge_pixels.py` | Mesclar para baixo e achatar grupo dão os mesmos pixels de antes da divisão de `LayerMerger` (CCN 32 e 19): opacidade e modo da camada de cima, máscara de recorte, camada de filtro rasterizada e grupo com subgrupo, filho oculto e grupo oculto; resumos gravados com o binário anterior, e mutações do recorte e da regra do grupo oculto os reprovam. |
| `test_layers_basic_operations.py` | Suite de Testes Padrão Ouro — Fase 1: Operações Básicas de Camadas Testa adição, exclusão, reordenação Drag & Drop C++, Alpha Lock, Clipping Mask e Merge Down. |
| `test_layers_groups_hierarchy.py` | Suite de Testes Padrão Ouro — Fase 2: Grupos de Camadas e Estrutura Hierárquica Testa criação de grupos, aninhamento de sub-grupos, modo Atravessar (Pass-Through) e opacidade/visibilidade efetiva recursivas. |
| `test_layers_plugin_structure.py` | Tests for Phase 4: Layers Plugin (paper & panel) ARCcC v2 decomposition. |
| `test_lowlevel_blend_modes.py` | Precisão numérica dos modos de mesclagem, do Alpha Lock e da máscara de recorte. |
| `test_lowlevel_brush_raster.py` | Mini-motores de pincel rasterizam na camada ativa: interpolação contínua, curvas de pressão, borracha. |
| `test_lowlevel_color_dynamics.py` | Mesclagem em sRGB linear e dinâmicas estendidas da caneta. |
| `test_lowlevel_color_profiles.py` | Low-Level Test Suite: Color Profiles, Display Buffer & Daltonism Proofing Math Validates C++ ColorProfile matrix calculations, display pixel buffers, and soft-proofing. |
| `test_lowlevel_giant_brushes_simd.py` | Pincéis gigantes, mesclagem SIMD (AVX2) de trechos e LOD adaptativo. |
| `test_lowlevel_memory_scalability.py` | Escala de formato e memória (canvas grande, 600 DPI). |
| `test_lowlevel_render_options.py` | Verifica que os flags do pipeline alteram o processamento nativo. |
| `test_lowlevel_selection_transform.py` | Low-Level Test Suite: Selection Bitmask, Flood Fill & Bicubic Transformation Math Validates SelectionEngine clipping, Magic Wand contouring, and TransformEngine affine matrix accuracy. |
| `test_lowlevel_telemetry_diagnostics.py` | Telemetria nativa: captura sem custo, ligar/desligar, latência em µs, memória de tiles e do histórico. |
| `test_lowlevel_undo_tile_stress.py` | Low-Level Test Suite: Tile Boundary Crossing, Multi-Step Undo/Redo & Memory Stress Validates dirty tile tracking across 64x64 boundaries, undo snapshot accuracy, and memory limits. |
| `test_lowlevel_viewport_lod_antialiasing.py` | Nível de detalhe (LOD) do viewport e antisserrilhamento por filtro de caixa. |
| `test_lowlevel_viewport_pipeline.py` | Pipeline do viewport para 120 FPS e aceleração de hardware. |
| `test_layer_tile_codec.py` | A camada como bloco de tiles do `.lmn` v3 (S1.2): cada pixel visível sobrevive (9 motores, tamanhos de borda, ruído opaco byte a byte), só os tiles pintados entram e em ordem, o instantâneo não muda com o que se pinta depois (nem de outra thread), tile comprimido na memória não sai em branco, 23 blocos malformados são recusados sem tocar a camada, e a composição em lote compõe uma vez no fim com a mesma imagem. |
| `test_lod_pyramid_damage.py` | A pirâmide de LOD refaz só onde o canvas mudou e nunca mostra pixel velho (D18): oráculo independente em numpy conferido depois de cada operação (traços de 9 motores lidos amostra a amostra, colar, balde, seleção, transformação, desfazer, camadas, filtros com alcance e pixelate, perfil de cor, redimensionar) e em 40 sequências aleatórias com mudanças acumuladas entre leituras; região de um nível; níveis e retângulos inválidos recusados. |
| `test_main_window_actions.py` | Contrato da casca: colaboradores da MainWindow e a porta do workspace. |
| `test_mdi_multidoc_lifecycle.py` | Test MDI Multi-Document Lifecycle & C++ Facade Isolation. |
| `test_menu_bar_complete_wiring.py` | Test Menu Bar Complete Wiring & Dialogs — Validação de Todas as Ações do Menu. |
| `test_native_build_contract.py` | Os metadados de build do módulo nativo descrevem o binário realmente carregado. |
| `test_native_core_invariants_and_rivers.py` | Invariantes do núcleo C++ e as 5 Leis do Leito do Rio de ponta a ponta. |
| `test_native_crash_log.py` | Queda nativa de verdade (processo filho) grava a pilha em `native_crash.log`; a abertura seguinte guarda o registro e avisa; só os 5 últimos ficam. |
| `test_new_document_dialog.py` | Unit tests for NewDocumentDialog, PresetCatalog and memory estimation. |
| `test_persistence_failures.py` | Failure injection and native round-trip regression coverage. |
| `test_plugin_installation.py` | Instalação de plugin: exige manifesto, recusa path traversal, id repetido e manifesto incompleto. |
| `test_plugin_lifecycle.py` | Ciclo de vida de plugins: ordem por dependência, limpeza em falha, conexões de painel removidas. |
| `test_portable_build_contract.py` | Build portátil: inclui motor, dados, plugins e avisos de terceiros; textos de licença copiados dos pacotes; manifesto com hash de cada arquivo; caminho do instalador. |
| `test_pre_commit_hook.py` | O gancho `.githooks/pre-commit` chama `scripts/pre_commit.py`, a lista rápida só tem testes que existem e o gancho é executável no índice. |
| `test_pyi_contract_matches_binary.py` | Regressao para F-024/3.3: garante que bridge/boundary/contracts/aladyn_engine_native.pyi descreve exatamente a superficie do modulo nativo compilado, nas duas direcoes. |
| `test_pyi_signatures_match_binary.py` | Cada método do `.pyi` recebe o que o binário recebe: quantidade e tipo dos argumentos, lidos da assinatura que o pybind11 publica (achou 11 divergências em 192 métodos). |
| `test_plugin_context_contract.py` | A superfície do `PluginContext` (só `service_registry`, `main_window` e `attach_main_window`; sem o motor) e que nenhum plugin lê outro membro: o contexto já não entrega o `EngineBackend` inteiro a plugins de terceiros (R9). |
| `test_python_lint.py` | Linter Python: zero achados do ruff com as regras de `[tool.ruff]` do `pyproject.toml` (pula se o ruff não estiver instalado). |
| `test_recording_contracts.py` | Contratos do plugin de gravação: quadro vem do documento ativo e do motor; barra flutuante só emite sinais. |
| `test_recording_engine.py` | Motor de gravação: ciclo da sessão, captura assíncrona, exportação ZIP, marca d'água e guias na captura. |
| `test_recording_plugin.py` | Plugin de gravação: painel, ativação no `WorkspaceService`, FPS, barra flutuante (inclusive soltar o canvas ao desativar), fluxo de parada e zero imports entre plugins. |
| `test_recovery_async.py` | A cópia de recuperação fora da thread da interface (S1.3): documento com gravação em andamento não é capturado de novo, a revisão só conta depois do arquivo, falha não é registrada, e a cópia que sai depois de o documento ser salvo ou fechado é apagada. |
| `test_regressions_ui_layout_items.py` | Testes unitários abrangentes para validação dos 8 itens de observação e estabilidade. |
| `test_regressions_undo_shortcuts_cursor.py` | Test suite for the 5 User Observations Audit and Verification in Lumenia V2. |
| `test_render_options_and_native_dirty_tracking.py` | Opções de renderização e marcação nativa de regiões alteradas. |
| `test_render_widget_structure.py` | Comprehensive unit tests for Camada 3 - Fase 2: RenderWidget Decomposition. |
| `test_river_ratchets.py` | Catracas das Leis do Leito do Rio: a contagem pode cair, nunca subir sem que alguém decida conscientemente (editando a lista abaixo, com motivo). |
| `test_runner_coverage_contract.py` | O runner grava a cobertura da fronteira de documento. |
| `test_runner_suite_selection.py` | As suítes nomeadas do runner apontam para arquivos de teste existentes e únicos. |
| `test_runtime_paths.py` | Raiz de recursos em desenvolvimento (repositório) e empacotado (pasta do executável). |
| `test_secondary_toolbar_structure.py` | Contrato da barra secundária (ui/plugins/system/workspace_core/workspace/secondary_tool_bar). |
| `test_selection_modify.py` | Seleção -> Modificar (Expandir, Contrair, Suavizar Borda) -- 2026-09-23. |
| `test_shape_paths.py` | Geometria da ferramenta Formas (`shape_paths.py`): Shift e Alt no retângulo, na elipse e na linha; vértices do polígono e da estrela; forma pequena ou desconhecida sem caminho. |
| `test_shortcut_registry.py` | Registro de atalhos: remapear/desativar/conflito atômicos, contexto do editor de texto e do canvas. |
| `test_smudge_source_snapshot.py` | O rastro do Borrar lê a camada como ela estava ao chegar o dab: o mesmo traço, com a cena deslocada para cruzar outras fronteiras de tile, dá a mesma imagem (D15). Roda o harness nativo `tests/native/smudge_source_snapshot.cpp` nos dois sentidos de movimento. |
| `test_state_links.py` | Regras entre estados (ui/core/state/state_links.py). |
| `test_stroke_characterization.py` | Caracterização do traço — fixa o comportamento ANTES de mexer no motor. |
| `test_stroke_pipeline_integrity.py` | Pipeline do traço do canvas: toque isolado, atualização contínua, inclinação/rotação da caneta, direções variadas. |
| `test_stroke_preview_native.py` | Prévia nativa do pincel (render_stroke_preview) -- regressão de 2026-08-25. |
| `test_telemetry_contract.py` | Contrato da telemetria com o motor nativo e o "Limpar Undo" de verdade. |
| `test_telemetry_views.py` | Telas de telemetria (cockpit, painel, diagnóstico) como views do `TelemetryTracker`. |
| `test_test_report_measured.py` | Relatório de testes com números medidos (JUnit XML), não fixos. |
| `test_theme_system.py` | Temas: arquivos válidos e completos, QSS sem tokens pendentes, resolução de cores e aliases. |
| `test_theme_tweaks.py` | Ajustes finos do tema: raio dos cantos e fonte de verdade; filtro em qualquer idioma. |
| `test_tool_lifecycles_and_paper.py` | Testes de Integridade dos Subsistemas Satélites — Rodada 10 (ARCcC v2) Validações de: - Cor do Balde de Tinta (do_flood_fill) e garantia de simetria de sinais via try/finally. |
| `test_tool_settings_contract.py` | Contract tests for canonical canvas-tool settings and their workspace route. |
| `test_tool_state.py` | Contrato do ToolState: ferramenta ativa e opções de ferramenta (fonte única). |
| `test_toolbars_geometry_i18n.py` | Test Suite: Toolbars & Geometry I18n Retranslation Valida se as opcoes da barra de ferramentas secundaria e dos paineis/dialogos de geometria acompanham a mudanca de idioma em tempo real (pt_BR, en_US, es_ES, ja_JP). |
| `test_tools_signal_symmetry_and_flip.py` | Testes automatizados cobrindo a integridade dos subsistemas satélites (Rodada 9). |
| `test_transform_distort.py` | Transformar -> Distorcer -- 2026-09-23. |
| `test_viewport_paint_telemetry.py` | O medidor "Blit" conta a cópia do canvas, não só o `drawImage` (D16): a viewport real cronometra a aquisição da imagem à parte, as parcelas não passam do total do paint, pintura sem imagem não herda tempo antigo e todas as telas leem `presentation_ms`. |
| `test_window_menu_panels.py` | Menu Janela: cada item abre o painel registrado com o mesmo PanelId. |
| `test_windows_portability.py` | Portabilidade para o Windows, conferida em qualquer sistema: caixa de nomes, nomes inválidos, caminhos longos, UTF-8 sem texto corrompido e `encoding=` em todo texto lido/gravado. |

## Regras

- Teste novo entra nesta tabela; mensagem de interface é comparada com `tr(...)`, nunca com o texto em português (o idioma do sistema muda o texto).
- Catracas (acoplamento, cores, rios, documentação por pasta) só podem cair; subiu, você acoplou.
- Nada de arquivo gerado aqui: saídas temporárias vão para `tmp_path` ou para o diretório de build fora da árvore.

## Dívida conhecida (medida em 2026-09-24)

O ARCcC prevê testes junto de cada pasta (`testes/`); aqui a suíte é central. Três arquivos de teste têm nome de fase em vez de assunto (`test_regressions_*`, `test_tools_signal_symmetry_and_flip.py`) e muitos nomes de função de teste estão em português.
