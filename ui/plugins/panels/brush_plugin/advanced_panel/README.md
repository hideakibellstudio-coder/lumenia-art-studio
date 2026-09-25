# `ui/plugins/panels/brush_plugin/advanced_panel/` — painel avançado do pincel

**Responsabilidade:** a janela de ajustes avançados (ponta, jitter, textura, espaçamento, parâmetros por motor de pincel). Parâmetros rápidos vão ao `BrushState`; os avançados, que nenhuma outra tela mostra, vão direto ao motor.

## Porta de entrada

`from .advanced_panel import AdvancedPanel` (`AdvancedPanel(brush_state, canvas_area)`), aberto pelo `BrushSettingsPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `AdvancedPanel`, `DynamicEngineParamsWidget` e `NonScrollComboBox`. |
| `engine_params_widget.py` | Dynamic Engine Parameters Widget for ALADYN engines. |
| `panel.py` | `AdvancedPanel`: janela com as abas "Pincel" (seções) e "Dinâmica por Motor"; abre ao lado do canvas (`FloatingPanelWindow`). |

## Regras

- Parâmetro avançado que ganhar uma segunda tela passa a morar no `BrushState` (ver `ui/core/state/README.md`, regra 3).
- O painel não guarda widget de seção nem escreve no motor: cada seção é dona dos seus controles e escreve pelo `BrushEngineWriter`.

## Dívida conhecida (medida em 2026-09-24)

`engine_params_widget.py` (242 linhas) monta os parâmetros por motor a partir de uma tabela própria; não tem teste.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/dialogs`
- `ui/core/engine`
- `ui/core/state`
- `ui/core/widgets/slider`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
- `ui/plugins/panels/brush_plugin/advanced_panel/sections`
<!-- /arccc:deps -->
