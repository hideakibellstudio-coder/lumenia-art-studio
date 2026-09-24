# `ui/core/widgets/tool_options/` — telas de opções de ferramenta

**Responsabilidade:** a base `ToolOptionsView` (vínculo de uma tela com as opções de UMA ferramenta no `ToolState`) e as páginas de opções do painel de pincel.

## Porta de entrada

`from ui.core.widgets.tool_options import ToolOptionsView, BucketOptionsWidget, ...` (ver `__init__.py`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Telas de opções de ferramenta ligadas ao ToolState. |
| `base.py` | Base controls for tool options widgets. |
| `bound_view.py` | ToolOptionsView — widget que mostra e edita as opções de UMA ferramenta no ToolState. |
| `bucket_wand_options.py` | BucketOptionsWidget e WandOptionsWidget — páginas do painel de pincel (views do ToolState). |
| `eyedrop_options.py` | EyedropOptionsWidget — página do conta-gotas no painel de pincel. |
| `shapes_options.py` | ShapesOptionsWidget — página das formas vetoriais no painel de pincel (view do ToolState). |
| `transform_selection_options.py` | TransformOptionsWidget e SelectionOptionsWidget — páginas do painel de pincel (views do ToolState). |

## Regras

- Toda tela de opções herda `ToolOptionsView`: `show_options` (estado → tela),
  `publish(campo=valor)` só do campo editado, e mostrar nunca republica.
- Várias telas mostram a mesma ferramenta (esta pasta e as views da barra
  secundária) e não se conhecem: ficam iguais porque mostram o mesmo estado.
- Regra entre estados (ex.: formas usam a cor do pincel) não mora em tela:
  mora em `ui/core/state/state_links.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/i18n`
- `ui/core/state`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
