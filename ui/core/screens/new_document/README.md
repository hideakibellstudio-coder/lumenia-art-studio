# `ui/core/screens/new_document/` — peças do diálogo Novo Documento

**Responsabilidade:** o catálogo de presets de documento (tamanhos, papéis, perfis) com a estimativa de memória, e o cartão visual de cada preset.

## Porta de entrada

`from ui.core.screens.new_document import PresetCard, PRESET_CATEGORIES, estimate_ram_usage_mb, ...` (reexportados).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | New Document Dialog package. |
| `preset_card.py` | PresetCard — Interactive visual card representing a canvas dimension preset. |
| `preset_catalog.py` | Catalog of document presets, paper properties, and memory estimators for Lumenia. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/theme`
<!-- /arccc:deps -->
