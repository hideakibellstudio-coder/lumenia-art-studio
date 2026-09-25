# `ui/core/screens/filters/` — filtros e camadas de ajuste

**Responsabilidade:** a galeria de filtros (camadas de ajuste), o inspetor de parâmetros e o popup de reedição de um filtro existente.

## Porta de entrada

`from ui.core.screens.filters import FilterAdjustmentDialog, FilterEditPopup, FILTER_DEFINITIONS`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta os diálogos e o catálogo de filtros. |
| `filter_adjustment_dialog.py` | FilterAdjustmentDialog — Diálogo Principal de Criação de Camadas de Filtro & Ajuste. |
| `filter_card.py` | filter_card.py — Card Atômico de Apresentação de Filtro. |
| `filter_definitions.py` | filter_definitions.py — Catálogo de Metadados e Parâmetros dos Filtros do Motor ALADYN. |
| `filter_edit_popup.py` | FilterEditPopup — Popup/Inspector de Re-Edição de Parâmetros de Filtro. |
| `filter_inspector.py` | filter_inspector.py — Painel Inspetor Dinâmico de Parâmetros de Filtros. |

## Regras

Os limites de cada parâmetro vêm de `filter_definitions.py` e espelham o motor. A prévia ao vivo e a criação da camada são do fluxo do painel de camadas (`FilterLayerFlow`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/dialogs`
- `ui/core/widgets/slider`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
