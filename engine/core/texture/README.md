# `engine/core/texture/` — texturas

**Responsabilidade:** texturas 2D amostráveis e as texturas geradas por código (formas de ponta e grão de papel).

## Porta de entrada

`Texture2D.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Texture2D.hpp` | Textura 2D com modo de repetição e amostragem rápida (declaração). |
| `Texture2D.cpp` | Implementação. |
| `ProceduralTextures.hpp` | Presets de forma e de relevo, máscara radial, grão de papel (declaração). |
| `ProceduralTextures.cpp` | Geração procedural. |

## Regras

- O id de `HeightPreset` é o `paper_texture_id` do documento: as listas de papel da UI (novo documento e `plugins/ui/layers_plugin/paper_texture_dialog.py`) usam os mesmos ids.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/utils`
<!-- /arccc:deps -->
