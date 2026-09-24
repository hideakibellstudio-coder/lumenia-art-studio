# `plugins/ui/brush_plugin/advanced_panel/sections/` — seções do painel avançado

**Responsabilidade:** montam as seções do painel avançado (tamanho/opacidade, geometria da ponta, jitter, textura e espaçamento).

## Porta de entrada

Funções `create_*_section(panel, ...)`, chamadas por `AdvancedPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `brush_texture_section.py` | Section 4 & 5: Brush Texture and Spacing. |
| `jitters_section.py` | Section 3: Brush Jitters and Random Variations. |
| `size_opacity_section.py` | Section 1: Brush Size, Opacity and Blending. |
| `tip_geometry_section.py` | Section 2: Brush Tip Geometry. |

## Dívida conhecida (medida em 2026-09-24)

Decomposição por tamanho de arquivo, não por responsabilidade: cada função recebe o `AdvancedPanel` e cria atributos nele (`panel.slider_x = ...`). O caminho é virar widgets com estado próprio, como a barra secundária em 2026-09-24. Pasta sem `__init__.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/brush_plugin/advanced_panel`
- `ui/core/i18n`
- `ui/core/state`
- `ui/core/widgets`
- `ui/core/widgets/slider`
<!-- /arccc:deps -->
