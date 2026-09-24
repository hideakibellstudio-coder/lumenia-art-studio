# `plugins/ui/layers_plugin/` — plugin de camadas

**Responsabilidade:** o painel de camadas: árvore (modelo, view, delegate), opacidade e modo de mesclagem, barras de ações, papel e textura, camadas de filtro.

## Porta de entrada

`LayersPlugin` (descoberto pelo `PluginManager`); o painel é `LayersPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `LayersPlugin`: registra o `LayersPanel` na doca direita. |
| `delegate.py` | `LayerItemDelegate`: desenha cada linha da árvore (visibilidade, miniatura, nome, modo, trava) e devolve cliques como ações. |
| `filter_layer_flow.py` | FilterLayerFlow — criar e editar camadas de ajuste com prévia ao vivo. |
| `grid.py` | Barras de botões de ação do painel (nova camada, grupo, duplicar, apagar, máscaras...). |
| `header.py` | `LayersHeader`: opacidade e modo de mesclagem da camada ativa. |
| `layer_commands.py` | LayerCommands — comandos que o painel de camadas dispara sobre o documento ativo. |
| `model.py` | `LayerModel`: modelo Qt da árvore sobre o `LocalLayerManager`; `setData` delega ao gerenciador (nunca escreve na camada). |
| `panel.py` | LayersPanel — painel de camadas do Lumenia. |
| `panel_filter_dialogs.py` | panel_filter_dialogs — Diálogos de Seleção e Configuração de Filtros de Camada. |
| `panel_rename_popup.py` | panel_rename_popup — Popup flutuante de renomeação de camadas. |
| `panel_theme.py` | LayersPanelTheme — Aplicação de Temas e Ícones no Painel de Camadas. |
| `paper.py` | `PaperLayerWidget` e botões de cor/textura do papel do documento. |
| `paper_texture_dialog.py` | TexturePopup — Diálogo popup para configuração de relevo e textura do papel. |
| `view.py` | `LayerTreeView`: a árvore com arrastar-e-soltar para reordenar e reparentar. |

## Regras

- O painel é view do `LocalLayerManager` do documento ativo: não sincroniza
  o motor (quem sincroniza é `ui/core/document/layer_backend_sync.py`).
- Comandos de camada passam por `LayerCommands` (cada um é uma
  `layer_transaction`); filtros com prévia ao vivo por `FilterLayerFlow`.

## Dívida conhecida (medida em 2026-09-24)

`model.py` está perto da parede dos 450 linhas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/screens/filters`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
