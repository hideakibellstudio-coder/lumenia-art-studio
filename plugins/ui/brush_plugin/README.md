# `plugins/ui/brush_plugin/` — plugin de pincel e ferramentas

**Responsabilidade:** o painel da doca esquerda com a coluna de ferramentas, o seletor de presets, a prévia do traço, os parâmetros rápidos e a página de opções da ferramenta ativa; o painel avançado do pincel.

## Porta de entrada

`BrushPlugin` (descoberto pelo `PluginManager`); o painel é `BrushSettingsPanel(brush_state, tool_state)`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `BrushPlugin`: cria o `BrushSettingsPanel` com o estado injetado e o registra na doca esquerda. |
| `brush_dropdown.py` | BrushDropdown — Botão Dropdown de Presets / Ferramentas do ALADYN ENGINE. |
| `brush_selector_popup.py` | BrushSelectorPopup — grade de presets do ALADYN ENGINE aberta pelo BrushDropdown. |
| `panel.py` | BrushSettingsPanel — painel de pincel e ferramentas (plugin BrushPlugin). |
| `presets_data.py` | presets_data — junta as categorias de `presets/` e dá nomes traduzidos a presets e categorias. |
| `stroke_preview.py` | StrokePreview  (Lumenia V2 High-Fidelity Engine Preview). |

## Regras

O painel é view do `BrushState` e do `ToolState`: não fala com o motor sobre cor/tamanho/opacidade (isso é do `BrushEngineSync`) nem com o canvas sobre ferramentas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/brush_plugin/advanced_panel`
- `plugins/ui/brush_plugin/components`
- `plugins/ui/brush_plugin/presets`
- `ui/core`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/state`
- `ui/core/theme`
- `ui/core/widgets`
- `ui/core/widgets/tool_options`
<!-- /arccc:deps -->
