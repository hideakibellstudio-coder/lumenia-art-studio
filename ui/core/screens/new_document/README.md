# `ui/core/screens/new_document/` — peças do diálogo Novo Documento

**Responsabilidade:** o catálogo de presets de documento (tamanhos, papéis, perfis) com a estimativa de memória, o cartão visual de cada preset e a galeria de presets do diálogo.

## Porta de entrada

`from ui.core.screens.new_document import PresetGallery, PresetCard, PRESET_CATEGORIES, estimate_ram_usage_mb, ...` (reexportados).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | New Document Dialog package. |
| `preset_card.py` | PresetCard — Interactive visual card representing a canvas dimension preset. |
| `preset_catalog.py` | Catalog of document presets, paper properties, and memory estimators for Lumenia. |
| `preset_gallery.py` | `PresetGallery`: abas de categoria e cards; emite `presetChosen(w, h, dpi)` e marca o card das medidas digitadas (`match`). |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/i18n`
- `ui/core/theme`
<!-- /arccc:deps -->
