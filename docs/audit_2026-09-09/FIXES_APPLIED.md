# Correções aplicadas — 2026-09-09

Esta rodada transformou os achados críticos da auditoria em código verificável.

## Integridade de documentos

- O modelo central agora é o único dono do estado das camadas e expõe sinais de conteúdo/estrutura para dirty tracking.
- Operações estruturais resolvem camadas por UID; índices só são usados nas APIs que explicitamente representam posição.
- Salvamento `.lmn` versionado usa manifesto JSON, payloads RGBA por camada, escrita temporária e `os.replace` atômico.
- Abertura, Save, Save As e fechamento de múltiplos documentos respeitam estado sujo e cancelamento do usuário.
- Redimensionamento nativo preserva pixels e metadados; resize, crop com offset e image-resize com reamostragem agora são passos transacionais do mesmo histórico nativo. Undo/redo restaura dimensões, pixels, seleção e metadados sem trocar a instância do motor nem perder passos anteriores.

## Motor e ponte

- A ponte expõe snapshots independentes por camada para exportação/persistência.
- QImage é desacoplada dos buffers nativos reutilizáveis.
- LOD é calculado sobre o buffer de exibição efetivo, incluindo perfis de cor.
- Alterações estruturais fora de transações limpam histórico nativo baseado em índices; operações integradas ao DocumentHistory preservam a sequência de passos. Falhas de leitura do scratch disk preservam o passo de undo/redo.
- `setup.py` declara C++20 e linka sem depender de manifesto de recurso; build validado no MSVC.

## UI, ferramentas e configurações

- Ciclo de vida de docks e conexão do brush dock são idempotentes.
- Bucket normaliza `expansion`/`expand_px` e usa a cor ativa real; eyedropper respeita amostragem da camada ativa ou composição.
- Atalhos de exportação e mesclagem não colidem (`Ctrl+E` e `Ctrl+Shift+E`).
- Preferências de docks gravam IDs canônicos independentes de idioma; aliases legados de perfil sRGB são migrados para IDs nativos.
- Limites de memória e quantidade de passos do histórico são aplicados ao backend ao abrir e alterar o diálogo de renderização.
- Os flags `low_latency`, `linear_gamma` e `deep_color` atravessam contrato, backend, PyBind11 e `PaintEngineFacade`: baixa latência remove o atraso do estabilizador, gama linear seleciona a equação física de mistura e Deep Color usa cálculo de precisão estendida antes da quantização final.
- Instalação de plugins rejeita caminhos absolutos e traversal de ZIP; remoção valida `commonpath`.
- O runner executivo usa pytest para incluir testes unittest e testes standalone.

## Validação

```text
python tests/run_all_tests.py
222 passed in 123.62s (baseline anterior)
```

## Fase adicional — geração global e empacotamento

- `PaintEngineFacade` agora expõe `get_document_generation()` e incrementa uma geração monotônica em mutações que alteram pixels, composição, camadas, canvas, transformações e traços.
- A mesma transação marca o `MipmapPyramid` como dirty, evitando LOD derivado de conteúdo antigo.
- O contrato `EngineBackend` e o binding PyBind11 foram estendidos sem vazar o motor nativo para camadas superiores.
- O `pyproject.toml` restringe o wheel às extensões declaradas pelo `setup.py`, evitando descoberta acidental de `assets`, `logs` e `scratch`.
- Teste nativo dedicado cobre a progressão da geração após alteração estrutural e escrita de pixels; suíte executiva completa concluída sem falhas.

## Fase seguinte — schema e migração de documentos

- O manifesto `.lmn` passa a persistir `guide_state` e `sym_state`, mantendo estados de edição específicos do documento.
- O leitor valida esses blocos e rejeita tipos inválidos antes de construir o documento.
- Manifestos legados sem campo `version` são migrados para a versão atual com defaults determinísticos de papel e câmera.
- Suíte executiva novamente concluída sem falhas após a migração.

## Estabilidade de encerramento

- `RecoveryStore` libera o `QLockFile` também durante destruição tardia do objeto, evitando locks órfãos em encerramento do Qt e falhas de limpeza em CI.
- A suíte executiva foi repetida após a correção e terminou sem erros de teardown.

## Histórico estrutural integrado — implementação efetiva

- O protótipo de histórico separado no LocalLayerManager foi substituído pelo DocumentHistory, que associa metadados por UID aos IDs dos passos reais do TileUndoManager.
- Transações de camadas armazenam snapshots nativos antes/depois, com buffers copy-on-write, tipos concretos de filtros, parâmetros e relações de parentesco reconstruídas.
- Pinceladas e operações estruturais coexistem na mesma sequência. Desfazer/refazer do canvas atualiza pixels nativos e a projeção local, sem repetir a reordenação através dos sinais do painel.
- Menus e painel usam transações para criação, duplicação, remoção, propriedades, reordenação, filtros, mesclagem e achatamento. A falha de uma operação restaura a pilha anterior; falha na restauração do modelo compensa o movimento do histórico nativo.
- Corrigidas duplicação de filtros, remoção recursiva de grupos, validação atômica de permutações/hierarquias e índices inválidos na mesclagem envolvendo grupos.
- IDs de passos não se repetem ao trocar/recriar contextos. O histórico estrutural respeita os limites de passos e contabiliza memória conservadoramente; snapshots estruturais são podados, ainda não paginados para scratch.
- Testes de integração cobrem sequência pixels/estrutura/geometria/redo, rollback, grupos aninhados, filtros, achatamento, ramificação após undo, limites, MDI, menus e painel reais.
- Removida a supressão de PermissionError na limpeza do perfil de testes: o encerramento volta a falhar explicitamente se restarem arquivos bloqueados.

Limites deste bloco: comandos de plugins que chamem diretamente APIs estruturais do backend precisam aderir à transação do DocumentHistory. A integração não implementa ICC, distribuição ou os demais achados da auditoria.

Validação final: extensão C++ recompilada, 32 testes focados de geometria/histórico/persistência aprovados, invariantes ARCcC aprovados e suíte executiva completa com 245 testes aprovada, incluindo teardown. `git diff --check` sem erros de whitespace.

## Contrato de buffers — 2026-09-10

- Todos os buffers exportados pelos bindings (pixels, display, LOD, camada, miniatura, seleção, transformação e prévias de textura) são snapshots `bytes` imutáveis com proprietário Python. Continuam válidos após mutação, resize, troca de textura e destruição da fachada.
- `get_brush_profile`, `get_canvas_texture` e `get_stabilizer` mantêm a fachada viva enquanto a referência ao membro existir. A liberação posterior também é testada.
- O contrato EngineBackend documenta snapshots de pixels independentes; imagens Qt de seleção e transformação são desacopladas do motor, como as de display e LOD.
- Entradas RGBA e de textura exigem tamanho exato, dimensões positivas e produto dentro dos limites de indexação nativa. Colagem rejeita overflow de coordenadas; miniaturas validam o tamanho antes da alocação. Rejeições preservam os pixels, as texturas e o histórico existentes.
- A ponte agora devolve a rejeição real da colagem nativa, inclusive em camadas bloqueadas. `refresh_display` atualiza o display sem criar um snapshot Python que seria descartado por `render`.
- A importação de textura da UI envia RGBA, enquanto a API nativa recebe um canal. A ponte agora converte luminância multiplicada pelo alfa, preservando linhas de largura ímpar e zerando contribuição de pixels transparentes. O carregamento anterior interpretava apenas os primeiros bytes RGBA como intensidades.
- 36 testes novos cobrem esses contratos. A primeira validação focada teve 43 testes aprovados (buffers + geometria); a validação após a correção de formato teve 39 aprovados (buffers + importação de textura).

Limite de desempenho: snapshots retidos consomem memória proporcional ao buffer; este bloco prioriza ownership definido. Medições de viewport e memória em documentos grandes continuam no F-015.

Validação final em 10/09: extensão recompilada com MSVC/C++20; suíte executiva com **281 testes aprovados**, incluindo invariantes ARCcC e teardown; `git diff --check` sem erros de whitespace. A suíte precisou da permissão de testes fora do sandbox para acesso à pasta temporária do pytest.

Build nativo validado com:

```text
call "...\\VsDevCmd.bat" -arch=x64
python setup.py build_ext --inplace
```

O workflow de CI e as dependências de desenvolvimento cobrem o build C++/PyBind11; `tests/test_lowlevel_render_options.py` verifica que os três flags alteram o processamento nativo e não apenas a persistência.

As correções posteriores de persistência, recuperação, smudge, pressão e atalhos
estão detalhadas em `FIX_STATUS.md`, junto das pendências ainda abertas.

## Projeção estrutural e identidade — F-002 + F-003 + F-005 — 2026-09-10

- `DocumentHistory` valida a assinatura estrutural antes de abrir uma transação e
  depois de aplicar metadados/pais. A assinatura compara quantidade, grupo/filtro
  e `parent_index` nativo. Salvamento também rejeita uma divergência já criada
  por mutação direta do modelo.
- `LocalLayerManager` aceita identidade somente como UID inteiro positivo; `bool`,
  índice e UID inexistente não são convertidos silenciosamente. A validação de
  integridade percorre todos os pais, rejeita ciclos, pais não-grupo, UID
  duplicado e camada ativa inexistente.
- `flatten_group` e `flatten_image` retornam `bool` e validam o resultado. O
  comando de achatar grupos tem guarda de progresso e confirma que cada merge
  reduziu a pilha; uma falha aborta a transação inteira.
- A ponte nativa publica `parent_index` em `get_layer_info`; o contrato Python e
  `EngineBackend` acompanham o método canônico.
- Todos os comandos de camadas do menu, painel, delegate e drop passam pelo
  mesmo `DocumentHistory.transaction`. Previews de criação/edição de filtro
  mantêm a operação nativa aberta até aceitar; cancelar restaura o snapshot
  inteiro sem registrar passo fantasma.
- A edição direta de nomes pelo `QAbstractItemModel` foi bloqueada; a única
  entrada de renomeação é o popup do painel, que atualiza modelo e motor numa
  única transação. O cancelamento explícito agora é tratado como rollback
  silencioso.
- Testes adicionais cobrem mutação somente local detectada antes do próximo
  comando, rejeição de `True` como UID, hierarquia inválida e achatar como um
  único passo reversível, além de cancelamento interativo sem novo passo. O
  lote estrutural direcionado passou com 56 testes; a matriz de menus, painel,
  drop, filtros e rollback foi validada pela suíte executiva.

F-002, F-003 e F-005 estão fechados no escopo definido pelo relatório. Os
limites de ICC/alta profundidade e os gates de benchmark/distribuição continuam
nos achados F-006 e F-015/F-016.

## Perfis de cor efetivos — F-006 — 2026-09-10

- Os IDs públicos 2 (Adobe RGB) e 3 (Rec. 2020), antes aceitos pelo catálogo
  mas sem ramo no rasterizador, agora alteram o buffer de exibição com alfa
  preservado. A pirâmide LOD é construída a partir desse mesmo buffer já
  transformado, mantendo a prova de cor consistente ao afastar o zoom.
- O setter nativo e o backend rejeitam IDs fora da faixa pública 0–13 em vez de
  aceitar um estado sem semântica.
- `ColorProfileType`/`ColorProfileManager` é agora a fonte única do catálogo,
  da transformação e dos metadados. A ponte PyBind11 publica IDs, nome,
  categoria, descrição, gamut, white point e transferência; o backend e a
  prévia do diálogo consomem somente esse contrato. Foram removidos os
  catálogos e transformadores Python/raster duplicados.
- `transform_rgba_for_profile` aplica exatamente o mesmo transformador nativo
  usado pelo display. O teste verifica os 14 perfis, os metadados obrigatórios,
  rejeição de entrada inválida e equivalência byte a byte entre a prévia e o
  buffer exibido.

Este bloco ainda está aberto para infraestrutura profissional: perfis ICC
arbitrários incorporados/externos com intents de renderização, e armazenamento
RGBA16/float durante toda a vida do documento. O RGBA8 atual tem composição em
precisão estendida quando Deep Color está ativo, mas a quantização e a
persistência continuam em 8 bits.

## Capacidades verificáveis do backend — F-010 — 2026-09-10

- `EngineBackend` declara uma matriz segura de capacidades e expõe consulta
  canônica por recurso. `AladynBackend` preenche essa matriz examinando a
  fachada ativa, sem vazar atributos privados para UI ou plugins.
- Exportação, diálogo de renderização e diagnóstico deixam de inferir suporte
  por `hasattr`: eles consultam o contrato. Controles indisponíveis são
  desativados, a exportação informa falha real, e os diagnósticos exibem formato
  de pixel, precisão e suporte ICC efetivos.
- O contrato distingue o que está disponível hoje (`RGBA8`, composição de
  precisão estendida, catálogo/prova nativa) do que ainda não existe (ICC
  incorporado e documento RGBA16), evitando que preferências persistidas virem
  promessas falsas na interface.
- Testes verificam a matriz Aladyn, exportação PNG concreta e habilitação dos
  controles conforme as capacidades recebidas.

## Contrato de ferramentas e presets — F-011 — 2026-09-10

- `ui.core.tool_settings` centraliza defaults, chaves, tipos e faixas para
  balde, conta-gotas, seleções, transformação, smudge, formas e texto. Os
  valores legados são normalizados no limite e não retornam pelo fluxo de UI.
- Os dois caminhos de interface passaram a emitir as mesmas chaves canônicas.
  O painel de pincéis agora conecta varinha, seleção e transformação ao
  workspace; balde, formas e texto chegam aos controladores que os consomem.
- A matriz de presets percorre todas as 33 receitas e compara tipo de motor e
  propriedades do perfil nativo. Inclui mínimos de tamanho/opacidade, antes
  ausentes da aplicação de preset, e confirma a alteração real da LUT de
  pressão.
- Testes de contrato observam chamadas de backend para balde, conta-gotas,
  varinha, seleção e transformação, além dos sinais dos componentes Qt.

## Histórico paginado e scratch disk — 2026-09-10

- `ScratchDiskManager::writeBlock` passa a retornar offset opcional, permitindo offset zero válido e falha explícita. Blocos gravados guardam tamanho e checksum em memória para rejeitar truncamento, corrupção e leitura de offset desconhecido.
- Desativar scratch disk bloqueia novas escritas, mas preserva arquivo e metadados necessários aos passos já paginados. `purge()` continua removendo todos os registros temporários.
- A paginação do `TileUndoManager` grava todos os buffers antes/depois antes de liberar qualquer buffer em RAM. Se uma gravação falha, o passo permanece íntegro em memória ou é podado como unidade completa pela política de limite, sem snapshots pela metade.
- Undo/redo prepara todos os tiles ou snapshots estruturais fora do estado vivo e só publica a alteração depois que leitura, descompressão e alocação preparatória terminam. Falhas preservam pixels, IDs de undo/redo e contabilização de memória, com código recuperável em `get_history_error()`.
- A ponte expõe o erro pelo contrato canônico `EngineBackend`, pelo stub `aladyn_engine_native.pyi` e pelo `PaintEngineFacade`. O workspace mostra mensagem de falha de histórico preservando o documento, em vez de reportar pilha vazia.
- O harness nativo `tests/native/history_faults.cpp` cobre falha de leitura em undo/redo, snapshot corrompido, primeira/terceira escrita falhando, scratch desativado, arquivo real truncado, arquivo real corrompido e purge. No Windows, o harness desativa o diálogo modal de fault do sistema para que crashes apareçam como falha de teste.

Limite deste bloco: scratch disk não é formato persistente de recuperação após encerramento abrupto do processo. Esse cenário permanece no eixo de persistência/recovery F-001 + F-013.

Validação em 10/09: `python -m pytest tests/test_history_io_failures.py -q -o addopts=''` com 11 testes aprovados e `python tests/run_all_tests.py` aprovado sem falhas.

## Persistência, recursos e migração — F-001 + F-013 — 2026-09-10

- LMN v2 inclui a seleção com cobertura de 8 bits, o bitmap do papel, escala,
  contraste, inversão, habilitação e LUT da curva, além do ID do perfil atual.
  Leitura/restauração conferem dimensões e conteúdo; salvar o contexto de outra
  aba é rejeitado antes de gravar.
- Pontos de guia usam pares JSON e voltam a QPointF. Guias e simetria são
  restauradas na UI e aplicadas ao motor; defaults são resetados ao trocar de aba.
- O painel de papel atualiza todos os campos do Document e o estado alterado.
  Carregar o painel é uma atualização de view sem regenerar a textura. Ajustar
  cor/visibilidade mantém a textura incorporada; só trocar o preset a substitui.
- Alterações de seleção/perfil invalidam a revisão para recovery. A recuperação
  valida candidatos, escolhe backup quando necessário e remove as duas gerações
  antigas apenas após criar uma nova cópia durável. Teste em subprocesso verifica
  recuperação depois de os._exit, sem destrutores ou liberação explícita do lock.
- Schema LMN com migrações explícitas v0 → v1 → v2. Validação inclui tipos de
  versão/dimensões, limite de indexação do motor, câmera, flags, pontos e recursos.
- Configuração tem schema_version independente da versão do produto, migração
  de aliases de perfil/velocidade/atraso e rejeição de atualizações inválidas de
  render antes da mutação. Schema futuro impede sobrescrita do arquivo original.
- O contrato canônico EngineBackend, a ponte Aladyn e o stub nativo acompanham
  os novos métodos. A extensão foi recompilada com MSVC/C++20.

Contrato e limites: [DOCUMENT_FORMAT_V2.md](DOCUMENT_FORMAT_V2.md). O ID de perfil
persistido ainda identifica o catálogo existente; não equivale a ICC incorporado.
Pixels continuam RGBA8. Histórico entre sessões e máscaras de camada não são
implementados por este formato. O bloco F-006 continua aberto.

## Ciclo de vida e instalação de plugins — F-012 — 2026-09-11

- `BasePlugin` tem o gancho final `dispose`; `PluginLifecycle` executa
  `initialize → activate` de forma transacional e compensa falhas com
  `deactivate → shutdown → dispose`. No desligamento todos os hooks são
  tentados, mesmo se um deles falhar, e a instância não permanece marcada como
  ativa.
- Dependências declaradas são resolvidas antes da ativação, com detecção de
  ciclo durante a recursão. Atualizar a janela principal não reinicializa nem
  reativa plugins já ativos, evitando painéis duplicados.
- Pacotes externos exigem manifesto SemVer com API mínima, dependências,
  permissões declaradas e `__init__.py` explícito. Uma seção opcional de
  integridade confere SHA-256 dos arquivos listados; metadados do plugin
  carregado precisam corresponder a ID e dependências do manifesto.
- A extração continua isolada em staging, agora rejeita entradas duplicadas e
  só promove um pacote que exponha `BasePlugin`. Falhas depois da promoção são
  movidas para `.plugin-quarantine`, que é excluída da descoberta.
- `WorkspaceContainer` registra cada painel e suas conexões Qt pelo
  `panel_id`, desconecta os slots antes da remoção e limpa referências por
  identidade. Brush, Properties, Navigator e Color usam esse registro; os
  plugins não acessam mais os atributos privados do workspace para reconectar
  sinais. Geometry passa pela remoção de doca em vez de destruir só o widget.

Limite explícito: hashes fornecidos pelo próprio pacote comprovam integridade,
não autoria. Assinaturas ancoradas em chave confiável e isolamento de execução
de Python externo dependem do fluxo de empacotamento/distribuição F-016.

Validação em 11/09: `tests/test_plugin_installation.py`,
`tests/test_plugin_lifecycle.py` e a invariável ARCcC passaram com **16 testes**;
`python tests/run_all_tests.py` foi aprovado integralmente após a alteração.

## Contexto efetivo de atalhos — F-014 — 2026-09-11

- O catálogo classifica comandos de janela e de canvas. `ShortcutRegistry`
  instala um guard de `ShortcutOverride`: qualquer editor de texto recebe a
  tecla antes de ações/atalhos da janela; atalhos de canvas não atuam quando o
  foco está fora da superfície de pintura.
- Com o canvas focado, transformação e comandos de seleção ficam sob o
  roteador local, evitando que `QAction` global capture o gesto primeiro e
  deixe de atualizar estado visual específico do canvas.
- `ShortcutBindings` guarda o mapa efetivo validado. O `InputRouter` consulta
  esse mapa, por isso remapear ou desativar transformação/seleções altera a
  entrada local de verdade, sem manter os antigos valores hard-coded.
- Os testes pressionam teclas reais em `QTextEdit` e canvas: `B` e `Ctrl+S`
  continuam no editor, enquanto seleção local não aciona a ação global. Também
  verificam um remapeamento para `Ctrl+Alt+A` até o mapa consumido pelo canvas.

Validação em 11/09: **18 testes** direcionados de atalhos, MainWindow, canvas e
ARCcC passaram; `python tests/run_all_tests.py` foi aprovado integralmente após
a alteração.

## Malha de qualidade e build auditável — F-015 + F-016 — 2026-09-11

- `tests/run_all_tests.py` continua com `full` como padrão, que coleta toda a
  árvore Pytest, e agora aceita `--suite smoke`, `contract`, `integration` ou
  `stress`. As listas são explícitas, verificadas por teste e permitem feedback
  curto sem fazer a suíte completa parecer menor do que é.
- `benchmarks/run_engine_benchmarks.py` grava JSON versionado para uma carga
  nativa real: importação em interpretador novo, criação da fachada, traço,
  composição/display, reconstrução LOD, memória de tiles e tamanho dos
  snapshots. Ele informa percentis, mas não impõe números de uma máquina como
  gate universal.
- `tests/test_document_format_fuzz.py` gera de forma determinística arquivos
  não-ZIP, truncamentos em posições variadas do seed válido e mutações de tipos
  em campos estruturais do manifesto. Todos precisam terminar como
  `DocumentFormatError`; erros de ZIP, recursão e I/O no leitor também são
  normalizados para esse contrato. O lote de persistência/fuzz passou com 60
  testes.
- O runner aceita `--coverage` e grava o relatório por ramos de
  `ui/core/document` em `build/coverage/document.json`. A primeira execução
  integral mediu 81,35%; o CI exige 80% e publica o JSON com o benchmark para
  revisão por versão de Python.
- O CI Windows passou a cobrir Python 3.11, 3.12 e 3.13. Cada job configura o
  MSVC x64, compila a variante scalar, registra o benchmark e publica seu JSON
  como artefato antes da suíte completa.
- O build nativo foi alinhado com C++20. `scripts/build_native.py` localiza o
  ambiente MSVC quando necessário, usa scalar por padrão, aceita AVX2 somente
  por escolha explícita e grava `build/native-build.json` com ABI, versão das
  ferramentas, variante e SHA-256 do `.pyd` produzido. O código escalar não
  inclui intrínsecos AVX2.
- `ui.core.runtime_paths` resolve assets e dados graváveis pelo diretório do
  executável no bundle, com fallback a `%APPDATA%` quando a instalação não for
  gravável. Ícone, splash, idiomas, guia, feedback e logs passaram a consumir
  esse contrato em vez de subir caminhos a partir de `__file__`.
- `scripts/build_portable.py` descreve e executa o bundle Nuitka com motor,
  interface, plugins, temas, assets, feedback e licença. A validação posterior
  confere os itens indispensáveis e grava um manifesto SHA-256. O instalador
  Inno recebe paths relativos e diretórios alternativos por definição de build.
- `requirements-dev.txt` fixa as versões testadas de PySide, PyBind11, NumPy,
  Pillow, Pytest e ferramentas de build. `requirements-dev.lock` contém a
  resolução Windows x64 para Python 3.11–3.13 com hash SHA-256 de cada roda
  aceita, incluindo os transitivos de Pytest. A instalação seca CPython 3.13
  confirmou o arquivo com `--require-hashes`. `BUILD.md` e README passaram a
  descrever o pipeline realmente executado, sem caminhos absolutos antigos.

Limite explícito: o lock cobre o alvo Windows x64/Python 3.11–3.13 da matriz de
CI; outros sistemas e versões exigem resolução própria. A distribuição ainda
precisa executar um release limpo, assinar wheel/instalador e selecionar
automaticamente o artefato SIMD após detecção de CPU. Também continuam abertos cobertura/mutação, um corpus
maior de fuzzing `.lmn` e limites de regressão de benchmark baseados em
ambientes controlados.

Validação direcionada em 11/09: benchmark, seleção de suites, render nativo e
invariantes ARCcC passaram com **13 testes**. `scripts/build_native.py --simd
scalar --force` gerou o artefato com MSVC 14.44 sem `/arch:AVX2`; a suíte
executiva completa foi aprovada integralmente em seguida sobre esse binário.
