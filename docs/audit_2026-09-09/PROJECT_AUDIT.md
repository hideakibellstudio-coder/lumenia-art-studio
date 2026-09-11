# Auditoria completa do projeto Lumenia / Aladyn

**Data:** 09/09/2026  
**Escopo:** repositório inteiro (`ui/`, `plugins/`, `engine/`, `bridge/`, `tests/`, documentação, build e artefatos distribuíveis).  
**Objetivo:** avaliar se a base pode evoluir para um software de pintura competitivo, sólido e previsível em suas configurações e interações.

## Veredito executivo

O projeto tem uma base técnica promissora: separação explícita entre PySide6 e C++, registro de backend, motor nativo com tiles esparsos, múltiplos motores de pincel, seleção, transformação, simetria, perspectiva, temas, localização e uma suíte de testes relevante. O trabalho de interface já cobre uma superfície de produto maior do que a de um protótipo comum.

O núcleo transacional ainda está em estado Alpha. Salvar um documento não serializa nada, “Salvar como” está conectado à exportação raster, fechar com a opção **Salvar** descarta o documento e fechar a janela não trata documentos sujos. A lista de camadas da UI e a pilha nativa podem divergir; operações de índice podem atingir a camada errada; “achatar imagem” pode entrar em loop infinito; redimensionar o canvas apaga pixels; e o undo usa índices mutáveis. Esses problemas tornam possível perder ou alterar trabalho do usuário mesmo com os testes verdes.

Minha recomendação é congelar a expansão de funcionalidades e fazer uma fase de confiabilidade do documento, comandos e motor. Com os P0 corrigidos, a proposta de baixo atraso, pincéis nativos, simetria e perspectiva pode ser uma diferenciação real. Sem essa etapa, novas ferramentas aumentarão a superfície de estados inconsistentes.

## Evidências e método

Foram usados leitura estrutural, busca AST/`rg`, inspeção dos contratos de arquitetura, execução do binário nativo disponível e probes de comportamento em Qt e C++. Os artefatos desta auditoria estão nesta pasta:

- `graphify_detect.json`: inventário do corpus completo. A detecção encontrou aproximadamente 755 arquivos, 352.862 palavras, 483 arquivos de código, 42 documentos e 230 imagens; não encontrou vídeo.
- `inventory.json`: contagem dos módulos principais e identificação dos testes Pytest fora do runner executivo.
- `executive_tests.log`: execução de `tests/run_all_tests.py`.
- `pytest_full.log`: execução de `python -m pytest -q tests`.

O corpus ultrapassa o limite de 200 arquivos do extrator semântico do Graphify. Por isso, a conclusão abaixo usa extração determinística, análise manual e probes executáveis; não apresenta um grafo semântico como se ele tivesse sido calculado.

### Tamanho observado

| Área | Arquivos | Linhas |
|---|---:|---:|
| `ui/` | 141 | 20.138 |
| `plugins/` | 126 | 19.109 |
| `engine/` | 105 | 13.480 |
| `bridge/` | 7 | 707 |
| `tests/` | 41 | 5.552 |

### Qualidade observada

- `python tests/run_all_tests.py`: **178 testes, OK, 111,843 s**.
- `python -m pytest -q tests`: **197 testes, 197 passaram, 141,66 s**.
- O runner executivo não coleta seis arquivos com funções `test_*` independentes; são 19 testes adicionais. O Pytest coleta os dois grupos.
- Durante a suíte executiva houve vários erros reais de persistência de configuração em `%APPDATA%/Lumenia/config.json` por permissão negada. Os testes continuaram verdes porque esses retornos não são tratados como falha.
- Os testes verificam muitos contratos, widgets, sinais e métodos, porém ainda faltam testes de round-trip de arquivo, consistência UI/native após cada comando, falha de I/O, invalidação de caches, identidade de camada e matriz de idioma/configuração.

## Pontos fortes que devem ser preservados

1. A intenção ARCcC é clara e os testes de invariantes detectam imports nativos fora do backend, vazamentos de atributos privados, imports cruzados entre plugins e módulos Python acima do teto de LOC.
2. `EngineRegistry` e `EngineBackend` fornecem uma fronteira útil entre a UI e o motor. O `AladynBackend` concentra o acesso ao PyBind11.
3. O motor possui uma divisão razoável entre `LayerStack`, compositor, rasterização, interpolação, seleção, transformação, textura, compressão, undo e telemetria.
4. Tiles esparsos, LZ4, cópia sob escrita, scratch disk, culling e LOD são boas escolhas para telas grandes e devem ser mantidos após a correção de invalidação.
5. Temas e i18n são tratados como sistemas centrais e há cobertura de re-tradução de vários diálogos.
6. O projeto já tem uma superfície de produto diferenciada: resposta de pincel, mídias naturais, simetria radial, réguas e perspectiva.

## Achados críticos (P0)

### F-001 — O ciclo de salvar/fechar causa perda de trabalho

**Evidência:** `ui/boundary/orchestrator/main_window_menu_actions.py:262-267` apenas exibe “Documento salvo”. `:269-279` implementa exportação PNG/JPEG. `ui/boundary/orchestrator/main_window_menu_builder.py:16-18` liga **Salvar como** e **Exportar** ao mesmo método. `main_window.py:67-68` chama apenas `super().closeEvent(event)`. `main_window.py:320-333` aceita a escolha **Salvar**, mostra uma mensagem e fecha o documento.

**Impacto:** não existe arquivo nativo, caminho associado, serialização, tratamento de erro, marcação de salvo ou recuperação. O usuário pode confirmar “Salvar” e perder camadas, configurações e pixels ao fechar.

**Correção necessária:** criar um `DocumentSerializer` versionado, adicionar `path`, `format_version`, `last_saved_hash` e `dirty_reason` ao documento; separar `save`, `save_as` e `export`; fazer gravação atômica com arquivo temporário, backup e recuperação; bloquear fechamento até todas as decisões de dirty state serem concluídas; testar salvar, reabrir, falhar no disco e cancelar.

### F-002 — A fonte única de verdade das camadas não é respeitada

**Evidência:** `Document`/`LocalLayerManager` vivem em `ui/core/document`, mas `main_window_menu_actions.py:99-206` cria, agrupa, duplica, remove, mescla e achata somente a lista local. O painel de camadas possui sincronização própria em `plugins/ui/layers_plugin/panel_sync.py`, enquanto `panel.py:163-164` deixa `_on_layer_added` vazio. `workspace_document_sync.py:70-210` restaura câmera, papel e guias, mas não reconcilia o stack nativo inteiro.

**Probe:** depois de criar uma camada pelo menu, a UI passou de 1 para 2 camadas, o nativo permaneceu com 1 e `is_dirty` continuou falso.

**Impacto:** o painel pode mostrar uma estrutura diferente do canvas; salvar/exportar/undo pode operar em outra camada; trocar de documento pode deixar estado residual.

**Correção necessária:** escolher um modelo canônico. Recomendo `Document` como modelo semântico e o motor nativo como projeção raster. Toda mutação deve ser um comando transacional que atualiza o modelo, aplica a operação ao backend, confirma o resultado e emite um único evento. Remover mutações diretas da lista a partir de menus e widgets.

### F-003 — Índice e UID de camada são ambíguos; “achatar” pode travar a UI

**Evidência:** `ui/core/document/layer_manager.py:147-151` interpreta um `int` como índice somente quando não há uma camada cujo UID seja aquele número. Como o primeiro UID é 1, o índice 1 e o UID 1 colidem. `main_window_menu_actions.py:198-206` executa `while len(lm.layers)>1: lm.merge_down(len(lm.layers)-1)`.

**Probe:** com camadas UID 1 e 2, `remove_layer(1)` removeu a primeira camada; `merge_down(1)` retornou `False`. Repetir `merge_down(len(layers)-1)` manteve duas camadas e nunca terminou.

**Impacto:** remoção/mesclagem pode atingir o item errado e o comando de achatar pode congelar a janela.

**Correção necessária:** eliminar APIs polimórficas. Usar `LayerId`/UUID estável para identidade e `LayerIndex` apenas em adaptadores explícitos; rejeitar tipos errados; fazer `merge_down(layer_id)` retornar um resultado tipado; substituir loops por uma operação única que garante progresso.

### F-004 — Redimensionar ou recortar o canvas apaga o conteúdo nativo

**Evidência:** `engine/core/document/LayerStack.cpp:18-40` recria as grades no `resize`, preservando apenas nome, opacidade, visibilidade e blend mode. Pixels, grupos, filtros, locks e hierarquia não são transferidos. `PaintEngineFacade.cpp:199-207` chama esse caminho. `main_window_menu_actions.py:304-335` usa o mesmo resize para resize e crop; o deslocamento da seleção/âncora não é aplicado.

**Probe:** um pixel vermelho em 8×8 ficou transparente após `resize_canvas(16,16)`.

**Impacto:** uma operação comum destrói o desenho sem confirmação ou undo confiável.

**Correção necessária:** separar `canvas_resize` de `image_resize`; definir âncora e offset; mover/copiar tiles com recorte/expansão; aplicar o resampler somente no image resize; preservar metadados, grupos e filtros; registrar tudo como comando undoável.

### F-005 — Undo/redo usa posição mutável em vez de identidade de camada

**Evidência:** `engine/core/canvas/TileUndoManager.hpp:17-24,36-54` grava `layerIndex`; `TileUndoManager.cpp:210-233,248-270` restaura por índice. Operações estruturais de `PaintEngineFacade` não remapeiam nem invalidam o histórico.

**Probe:** pintar vermelho na camada 0, azul na camada 1, reordenar e desfazer fez o undo restaurar a camada errada.

**Impacto:** o histórico deixa de representar a ação do usuário após reordenação, duplicação, merge ou exclusão.

**Correção necessária:** snapshots devem usar UUID da camada, geração do documento e coordenadas de tile. Operações estruturais devem ser comandos no mesmo histórico, com undo próprio, ou limpar explicitamente o histórico quando a operação não puder ser revertida. Adicionar testes de permutação, merge, duplicate e close/reopen.

### F-006 — O pipeline de cor tem catálogos e semânticas incompatíveis

**Evidência:** `ui/core/engine/color_profiles_catalog.py:3-138` anuncia IDs para sRGB, P3, Adobe RGB, Rec.2020, CMYK, acessibilidade, Linear e ACES. `engine/core/raster/ColorProfileManager.hpp:20-146` implementa outra tabela; `engine/core/color/ColorProfile.hpp/.cpp` usa uma terceira convenção. Os IDs 2 e 3 são efetivamente no-op no caminho raster. `PaintEngineFacade.cpp:454-462` aplica perfil ao buffer completo, mas `getDisplayPixelBufferLOD` entrega dados de mipmap por outro caminho.

**Probe:** para vermelho 1×1, perfis 0–3 retornaram `[255,0,0]`; CMYK e acessibilidade aplicaram transformações heurísticas. Com perfil grayscale, o buffer completo ficou `[53,53,53]`, enquanto LOD1 permaneceu `[255,0,0]`.

**Impacto:** o usuário recebe uma prévia diferente dependendo do zoom e pode acreditar que trabalha em Adobe RGB/P3/CMYK quando a transformação não existe ou não é consistente. Isso inviabiliza confiança para impressão.

**Correção necessária:** definir um catálogo único com enum/metadata compartilhado; separar espaço de trabalho, espaço de armazenamento e transform de display; usar LittleCMS ou equivalente para ICC; aplicar o mesmo transform e intenção de renderização a todos os níveis de resolução e exportação; testar valores de referência e round-trip.

## Achados de alta prioridade (P1)

### F-007 — Buffers expostos ao Qt não têm proprietário seguro

`bridge/core/bindings/bind_canvas.cpp:15-21,81-88` cria `memoryview` sobre ponteiros internos sem capsule/proprietário. `ui/engine_backends/aladyn.py:133-152` cria `QImage` diretamente sobre esses ponteiros. Resize, troca de documento ou reallocation pode invalidar a memória enquanto a imagem ainda existe.

Use um objeto buffer dono, cópia explícita para exportação ou um wrapper que mantenha a facade viva e invalide imagens antigas por geração.

### F-008 — Invalidação de compositor, dirty tiles e LOD é incompleta

`PaintEngineFacade.hpp:218-239` acompanha dirty tiles apenas do ativo e a atualização do mipmap depende desse estado. `Compositor.cpp` deixa o output anterior quando a lista recebida está vazia e preenche transparente quando não há fundo visível. Probes mostraram LOD desatualizado depois de limpar dirty state e depois de ocultar camada.

Use uma geração global de composição por documento, dirty regions por camada, invalidação em visibilidade/opacidade/blend/papel e cache LOD por geração. “Nenhuma camada visível” deve ter semântica explícita: transparente ou cor de papel, de acordo com o documento.

### F-009 — Falhas do scratch disk podem ser reportadas como undo bem-sucedido

`TileUndoManager.cpp:198-206` chama `restoreStepFromDisk(step)` e ignora o `bool`. O método de restauração retorna falso quando a leitura falha (`:176-184`), mas o undo move o passo para redo e retorna `true` mesmo sem restaurar todos os snapshots.

Propague o erro, preserve o passo no stack quando a leitura falhar, registre diagnóstico e teste disco cheio, arquivo removido, leitura truncada e encerramento inesperado.

### F-010 — O contrato do backend permite no-ops silenciosos

`ui/core/engine/backend.py` possui vários defaults vazios. `ui/engine_backends/aladyn.py:107-109,113-114,163-164` deixa `render`, `update_view` e `dispatch` como `pass`. O teste arquitetural verifica que o método foi sobrescrito, mas não que ele produza efeito.

Troque defaults silenciosos por `CapabilityUnavailable`/resultado explícito, defina capabilities no backend e faça o canvas consumir uma única API de renderização. Cada método canônico precisa de teste de efeito observável.

### F-011 — Várias configurações visíveis não chegam ao comportamento real

- `aladyn_brush_mixin.py:383-392`: `set_pressure_curve_power` é no-op.
- O handler de smudge procura `get_brush_profile`, mas `AladynBackend` expõe `get_brush_profile_dict`; os controles de smudge não chegam ao motor.
- `tool_manager.py:93-107` procura `widget.brush_color`, enquanto a cor ativa é mantida como `_active_draw_color` por `workspace_brush_adapter.py:52-59`; o balde tende a usar preto.
- O toolbar envia `expansion` (`brush_fill_toolbar_handlers.py:145-153`), mas o consumidor lê `expand_px` (`tool_manager.py:104`); o slider de expansão não tem efeito.
- `eyedrop_tool_controller.py:21-62` sempre amostra `get_canvas_image()`, ignorando `sample_all=False` embora a UI ofereça a opção.

Centralize o schema de cada ferramenta, valide chaves e tipos, e faça um teste de contrato por controle: alterar o widget, observar a chamada do backend e observar o pixel/estado resultante.

### F-012 — Wiring de plugins é frágil e a instalação não é segura

`workspace_container.py:234-274` faz wiring por `hasattr`. O plugin de pincel adiciona o painel e também chama `connect_brush_dock`, duplicando conexões já feitas por `add_panel`. `remove_panel` não limpa referências nem desconecta sinais; objetos Qt removidos podem continuar referenciados.

`ui/core/plugins/manager.py:335-343` usa `ZipFile.extractall` sem validar caminhos, manifesto, versão de API, assinatura ou rollback. `:359-421` usa comparação `startswith` para validar a pasta de remoção, que não é uma checagem de caminho segura.

Adote manifesto (`id`, versão, API mínima, dependências, permissões), extração com `commonpath`, staging temporário, hash/assinatura opcional, quarentena e rollback. Faça lifecycle idempotente (`initialize/activate/deactivate/dispose`) e registre conexões para desconexão determinística.

### F-013 — Configuração persistida falha e valores dependem do idioma

`ConfigManager` tem gravação atômica (`ui/core/config/manager.py:186-202`), mas chamadas ignoram a falha e a suíte gerou repetidamente `Permission denied` para `config.json.tmp`. O aplicativo não oferece fallback ao diretório do usuário, diagnóstico acionável ou restauração do último arquivo válido.

`DockBarsSettingsDialog._collect_config` (`ui/core/screens/dock_settings_dialog.py:293-300`) salva `currentText()` em vez de `itemData()` canônico. O layout interpreta rótulos em português (`workspace_layout_manager.py:189-199`); ao trocar para inglês, a configuração pode persistir “Fast” e ser interpretada como valor desconhecido.

`render_settings_components.py` salva `profile_id`, `deep_color`, `linear_gamma` e `low_latency`, mas o apply do diálogo (`render_settings_dialog.py:330-351`) só troca o perfil no backend. As outras opções não são aplicadas ao renderer; limites de undo são aplicados de forma oportunista, não como restauração completa no boot.

Há ainda uma incompatibilidade de tipo: `DEFAULT_CONFIG` inicia `render.profile_id` como a string `"srgb"`, enquanto `load_render_settings` (`render_settings_components.py:23-30`) só aceita número e converte esse valor para 0. O catálogo da UI usa IDs inteiros. O schema precisa escolher uma representação única e migrar configurações antigas.

Defina schema tipado com IDs estáveis, validação, migração, valores canônicos independentes de idioma, gravação com backup e recuperação, e uma fase de aplicação no startup que configure cada backend/facade.

### F-014 — Atalhos têm conflito e remapeamento parcial

`ui/core/components/menu_bar/file_menu.py:54` usa `Ctrl+E` para exportar e `ui/core/components/menu_bar/layer_menu.py:58` usa o mesmo atalho para mesclar. A tela de atalhos (`keyboard_shortcuts_dialog.py:149-166,315-343`) salva um mapa genérico, enquanto os menus e `QShortcut`s são construídos com valores fixos em vários pontos.

Crie um `CommandRegistry` único com ID, contexto, prioridade, gesto e validação de colisões. Reaplique os atalhos no boot e após salvar; mostre conflitos e permita desabilitar uma ação.

### F-015 — O processo de teste não mede a qualidade que o produto precisa

O fato de 178/197 testes passarem é positivo, porém não cobre os fluxos mais perigosos. O runner executivo não coleta testes Pytest standalone e não falha em erro de persistência. A duração de 111–142 s é incompatível com uma malha de feedback frequente, e não há cobertura, property-based testing, fuzzing de arquivos ou matriz automatizada de DPI/escala/idiomas.

Unifique o runner em Pytest, falhe em logs de erro e I/O não esperado, separe smoke/contract/integration/stress, adicione cobertura de linhas e de mutação para o modelo de documento, e crie fixtures de arquivos temporários. Mantenha benchmarks separados para pintura, composição, LOD, memória e startup.

### F-016 — Build e distribuição não são reproduzíveis

`setup.py` compila como C++17 com `/arch:AVX2`, enquanto `AGENTS.md` descreve C++20. `BUILD.md` contém caminhos absolutos de uma árvore antiga. `ui/requirements.txt` lista somente PySide6 e maturin, mas o build usa PyBind11 e o código/testes dependem também de NumPy/Pillow em diversos pontos.

O `.pyd` está presente localmente, mas `git ls-files` não o rastreia; um clone limpo não é executável sem um build externo. Não há `pyproject.toml`, lockfile, workflow de CI ou matriz de Python/Windows. AVX2 obrigatório sem detecção limita hardware suportado.

Defina um build reprodutível, dependências e hashes versionados, CI Windows que compile o `.pyd`, testes contra o artefato recém-construído, wheel/instalador assinado e fallback SSE2/feature detection. Atualize README e BUILD a partir do pipeline real.

## Análise por subsistema

### Documento, camadas e MDI

`Document` (`ui/core/document/document.py:8-43`) guarda dimensões, câmera, cor, papel e flags, mas não guarda caminho, formato, versão, metadados, referências de assets, histórico semântico ou snapshot serializável. `DocumentManager` cria e fecha documentos (`manager.py:23-89`) sem persistência. O MDI nativo (`aladyn_mdi_mixin.py:13-73`) isola facades por UID, o que é correto como isolamento de runtime, mas cada documento permanece em memória integral e não há política de descarregamento ou reconciliação de camadas.

O alvo deve ser um `DocumentModel` versionado, com IDs estáveis e comandos. O backend deve ser uma projeção materializada desse modelo; trocar a aba deve ativar uma sessão documentada, validar geração e restaurar todas as propriedades, não apenas câmera/papel.

### Motor nativo e raster

Tiles 64×64, engines de pincel, interpolação, seleção, transformação, composição e compressão formam uma boa fundação de performance. O problema não é falta de algoritmo, mas semântica de estado: resize destrutivo, undo indexado, múltiplos catálogos de cor, LOD sem transform, dirty tracking parcial e buffers sem ownership.

Antes de otimizar mais, estabeleça invariantes: toda operação altera uma geração; toda leitura de display informa a geração; todo cache inclui a geração; toda ação tem resultado de sucesso/erro; toda imagem exposta tem proprietário válido; e um documento salvo e reaberto produz o mesmo hash de pixels/metadados.

### UI, workspace e interações

`MainWindow` coordena menus, documentos, plugins e status (`main_window.py:27-124`), enquanto `WorkspaceContainer` mistura layout, câmera, documento, brush e conexão de docks. O wiring por introspecção torna a ativação simples, mas difícil de auditar e fácil de duplicar. Menus operam diretamente no modelo local, painéis têm sincronização própria e o canvas usa o backend nativo; essa triangulação é a principal fonte de divergência.

Substitua o acoplamento por comandos/eventos: `CommandRegistry`, `DocumentSession`, `LayerService`, `ToolStateStore` e `RenderInvalidationBus`. Widgets devem emitir intenção; serviços validam e executam; views apenas refletem o estado.

### Configurações e preferências

O JSON único é uma direção melhor do que configurações espalhadas, mas precisa de schema, migração, atomicidade comprovada, lock, fallback e aplicação completa no startup. Configurações de performance devem ser propriedade do documento quando afetam o resultado (perfil, profundidade e intenção de cor) ou da aplicação quando afetam somente execução (latência, limite de memória). A distinção deve ser explícita.

### Segurança e extensibilidade

Plugins Python são código com os mesmos privilégios do processo, portanto instalação é uma fronteira de confiança. O atual carregamento dinâmico e extração de ZIP não têm validação suficiente para uma galeria ou marketplace. Também faltam versão de contrato, compatibilidade de dependências, permissões declaradas, logs de instalação e desinstalação transacional.

### UX, acessibilidade e localização

Há boa cobertura de tema e quatro localidades, mas alguns valores de configuração usam rótulos traduzidos, o que quebra persistência entre idiomas. O conflito `Ctrl+E`, mensagens de sucesso para operações que não salvaram e ausência de feedback de falha de configuração são problemas de confiança. Acessibilidade deve incluir navegação por teclado, foco visível, nomes acessíveis dos ícones, contraste por tema e comportamento de alta escala/DPI em execução real.

## Lacunas de produto para competir

O README marca como roadmap o formato nativo `.lmn`, formas vetoriais e texto editável. A implementação atual abre imagem raster e exporta PNG/JPEG; não há um formato editável confiável. Também não foi encontrada uma estratégia completa de autosave/recovery, importação/exportação de camadas, perfis ICC, ajustes não destrutivos, biblioteca de assets/pincéis, histórico semântico, relatórios de crash ou atualização segura. Essas são lacunas de produto, não apenas tarefas de acabamento.

Depois do núcleo confiável, a ordem de maior retorno é:

1. `.lmn` versionado com thumbnail, camadas, grupos, máscaras, filtros, perfil ICC e assets referenciados.
2. Compatibilidade de entrada/saída escolhida por público-alvo, começando por PNG/TIFF/PSD ou outro formato com demanda comprovada.
3. Texto e formas como entidades editáveis, com rasterização apenas na exportação.
4. Ajustes e filtros não destrutivos, máscaras e presets de pincel portáveis.
5. Tablet real (Wacom/Huion/XP-Pen), pressão/tilt, baixa latência medida e recuperação após desconexão.
6. Autosave, recovery, crash reporter opt-in, telemetria local e diagnóstico sem expor conteúdo do usuário.

## Arquitetura alvo

```text
UI/View
  -> CommandRegistry / ToolStateStore
  -> DocumentSession + DocumentModel (SSOT, IDs estáveis, dirty, undo semântico)
  -> BackendContract (Result, Capability, geração, buffer ownership)
  -> AladynBackend (único acesso ao PyBind11)
  -> PaintEngineFacade / LayerStack / Compositor / TileStore
```

O arquivo `.lmn` deve ser um pacote versionado com manifesto, metadados, chunks de tiles, ordem/hierarquia, ICC, thumbnail e checksums. Salvar deve escrever para staging, validar, substituir atomicamente e manter `.bak`/recovery. O documento deve ter um hash de conteúdo para dirty state; câmera e preferências de view podem ser separados do conteúdo.

Cada comando deve expor `can_execute`, `execute`, `undo`, descrição, impacto de dirty e eventos afetados. IDs de camada devem sobreviver a reordenação; índices devem existir somente na borda nativa. O backend deve retornar erro estruturado e declarar capabilities, evitando `pass` silencioso.

O render deve trabalhar com uma única política de cor e geração. Buffer de display e LOD precisam compartilhar transform, ownership e invalidação. Operações de camada, resize, crop, perfil e papel devem atualizar a mesma geração e entrar no histórico quando alterarem o conteúdo.

## Roteiro recomendado

### Fase 0 — bloqueio de regressões (P0)

Corrigir F-001 a F-006 antes de novas ferramentas. Critério de saída: criar, pintar, reordenar, mesclar, redimensionar, fechar, salvar, reabrir e desfazer preserva pixels e metadados; nenhuma operação de menu pode divergir UI/native; achatar sempre termina ou retorna erro.

### Fase 1 — documento e persistência

Implementar modelo versionado, IDs, serializer `.lmn`, dirty state, autosave/recovery, export separado e comandos semânticos. Criar fixtures de documentos pequenos, grandes, com grupos, filtros, transparência, perfis e assets ausentes.

### Fase 2 — motor determinístico

Corrigir ownership de buffers, resize/crop, undo por ID, scratch error handling, composição/LOD e catálogo de cor. Medir p95 de latência, FPS de viewport, memória por megapixel, tempo de abertura e tempo de save.

### Fase 3 — integração de UI e configuração

Unificar tool state, layer service, atalhos e eventos. Remover wiring duplicado, limpar lifecycle de plugins, aplicar todas as preferências no boot e testar cada configuração nos quatro idiomas.

### Fase 4 — release engineering

Criar `pyproject`/lockfile, CI Windows, build do C++ em matriz, artefato versionado, instalador assinado, diagnóstico de crash e atualização da documentação. Validar em máquina sem AVX2, DPI alto, caminhos com Unicode, disco cheio e permissões restritas.

### Fase 5 — vantagem competitiva

Entregar o formato editável e compatibilidade escolhida, texto/formas, filtros não destrutivos, biblioteca de pincéis, tablet completo e recursos de produtividade. Cada recurso deve entrar com benchmark, teste de round-trip e telemetria de falha opt-in.

## Critérios de pronto para uma versão competitiva

- Zero P0 aberto e nenhum caminho de sucesso que apenas mostre uma mensagem sem persistir ou executar.
- Salvar/reabrir mantém pixel hash, ordem/UID de camadas, grupos, opacidade, blend, máscaras, filtros, papel, perfil e assets.
- Undo/redo funciona após qualquer combinação de pintura, reordenação, duplicação, merge, resize, crop e troca de documento.
- Perfil de cor, display completo, LOD e exportação produzem resultados coerentes e testados por referência.
- Configurações são versionadas, independentes de idioma, aplicadas no startup e verificadas por retorno de erro.
- Pytest é o único ponto de entrada, coleta todos os testes, falha em I/O inesperado e publica cobertura e benchmarks.
- Build limpo reproduz o `.pyd` e o instalador em CI, com dependências declaradas e artefatos assinados.
- Testes manuais de tablet, alta escala, múltiplos monitores, documentos grandes, recovery e acessibilidade são parte do release gate.

## Conclusão

O Lumenia já tem material suficiente para se tornar competitivo, mas sua prioridade precisa mudar de “mais ferramentas” para “estado confiável, documento editável e resultado determinístico”. A arquitetura declarada oferece bons limites; a implementação atual ainda os atravessa nas operações de camada, persistência e renderização. Corrigir os P0 e transformar as interações em comandos transacionais dará uma base sólida para aproveitar a performance e os diferenciais do Aladyn sem colocar o trabalho do usuário em risco.
