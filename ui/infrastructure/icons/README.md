# `ui/infrastructure/icons/` — ícones da interface

**Responsabilidade:** o catálogo de ícones SVG em código e a fábrica de `QIcon` que troca `currentColor` pela cor do tema.

## Porta de entrada

`from ui.infrastructure.icons import get_icon` → `get_icon("brush")`, `get_icon("brush", "#rrggbb")` ou `get_icon("brush", "accent")` (token do tema).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta de entrada: `get_icon`, `svg_to_icon`, `clear_icon_cache`, `set_color_resolver`, `SVG_ICONS`, `ALIASES`. |
| `icon_factory.py` | `get_icon`: resolve o nome (aliases), aplica a cor e guarda em cache. |
| `svg_catalog.py` | Catálogo central `SVG_ICONS` e `ALIASES` (nomes antigos → nome canônico). |
| `svg_tool_icons.py` | SVG das ferramentas artísticas e das camadas (entra no catálogo). |

## Regras

- Ícone novo: SVG com `currentColor` em `svg_catalog.py` (ou `svg_tool_icons.py`).
- Não importa o tema: a cor de um token vem do resolver que o `ThemeManager`
  registra ao ser criado. Até 2026-09-24 havia ciclo entre ícones e tema.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
