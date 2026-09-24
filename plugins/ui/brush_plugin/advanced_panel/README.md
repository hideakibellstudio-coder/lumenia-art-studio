# `plugins/ui/brush_plugin/advanced_panel/` — painel avançado do pincel

**Responsabilidade:** a janela de ajustes avançados (ponta, jitter, textura, espaçamento, parâmetros por motor de pincel). Parâmetros rápidos vão ao `BrushState`; os avançados, que nenhuma outra tela mostra, vão direto ao motor.

## Porta de entrada

`from .advanced_panel import AdvancedPanel` (`AdvancedPanel(brush_state)`), aberto pelo `BrushSettingsPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `AdvancedPanel`, `DynamicEngineParamsWidget` e `NonScrollComboBox`. |
| `engine_params_widget.py` | Dynamic Engine Parameters Widget for ALADYN engines. |
| `non_scroll_combo_box.py` | Non-scrollable QComboBox widget. |
| `panel.py` | AdvancedPanel Dialog for Brush Settings and Engine Dynamics. |
| `panel_engine_bridge.py` | PanelEngineBridgeMixin — parâmetros AVANÇADOS do pincel que vão direto ao motor. |
| `panel_thumbnails.py` | Thumbnails rendering helpers for Advanced Panel. |
| `texture_file.py` | Leitura de uma imagem do disco como textura de pincel (RGBA8888). |

## Regras

Parâmetro avançado que ganhar uma segunda tela passa a morar no `BrushState` (ver `ui/core/state/README.md`, regra 3).

## Dívida conhecida (medida em 2026-09-24)

`panel_engine_bridge.py` é um mixin que escreve no motor pelo painel; as seções (`sections/`) são funções que recebem o painel e penduram widgets nele.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/brush_plugin/advanced_panel/sections`
- `ui/core`
- `ui/core/dialogs`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/state`
- `ui/core/theme`
- `ui/core/widgets/slider`
<!-- /arccc:deps -->
