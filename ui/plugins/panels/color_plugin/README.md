# `ui/plugins/panels/color_plugin/` — plugin de cores

**Responsabilidade:** o painel da roda de cores (HSV, harmonias, recentes) na doca esquerda.

## Porta de entrada

`ColorPlugin` (descoberto pelo `PluginManager`); o painel é `ColorWheelPanel(brush_state)`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `ColorPlugin`: registra o `ColorWheelPanel` com o `BrushState` injetado. |
| `panel.py` | ColorWheelPanel — Painel Isolado da Roda de Cores. |

## Regras

View do `BrushState`: a cor escolhida vai para `BrushState.set_color`; qualquer mudança de cor (conta-gotas, outro painel, troca de documento) volta pelo sinal do estado.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/plugins`
- `ui/core/state`
- `ui/core/widgets`
- `ui/core/widgets/color_picker`
<!-- /arccc:deps -->
