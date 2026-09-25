# `ui/plugins/panels/brush_plugin/presets/` — presets de pincel

**Responsabilidade:** os dados dos presets por categoria (lápis, nanquim, marcador, aquarela, óleo, borracha, desfoque, smudge) e as chaves de tradução dos nomes.

## Porta de entrada

`from .presets import ...` (reexporta categorias e presets); lido por `presets_data.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Presets subpackage for BrushPlugin. |
| `basic_presets.py` | Basic brush and eraser categories and presets. |
| `effect_presets.py` | Marker, Blur, and Smudge categories and presets. |
| `i18n_keys.py` | I18N translation keys for brush presets and categories. |
| `paint_presets.py` | Watercolor and Oil Impasto categories and presets. |
| `sketch_ink_presets.py` | Pencil and Inker categories and presets. |

## Regras

Só dados: sem Qt e sem motor. Parâmetro de preset novo precisa existir em `ui/infrastructure/bridge_client/brush_param_table.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
