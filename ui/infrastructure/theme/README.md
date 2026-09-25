# `ui/infrastructure/theme/` — tema e cores

**Responsabilidade:** o `ThemeManager`: paletas de cor, escala da interface, ajustes de raio e fonte do usuário, folha de estilo global e os sinais `themeChanged`/`scaleChanged`.

## Porta de entrada

`from ui.infrastructure.theme.manager import ThemeManager` (34 consumidores); `ThemeManager.instance().get_color(TOKEN, fallback)`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ThemeManager`. |
| `interface_tweaks.py` | Ajustes do usuário por cima de qualquer tema: raio dos cantos e família da fonte (tokens `RADIUS_*`/`FONT_FAMILY` do QSS). |
| `manager.py` | `ThemeManager` (singleton): tema atual, `get_color`, escala, aplicação da folha de estilo e sinais de mudança. |
| `overlay_palette.py` | `OverlayPalette`: cores com nome das sobreposições desenhadas sobre a arte (perspectiva, formigas da seleção, alças, lupa), iguais em todo tema. |
| `palettes.py` | Paletas de cor de cada tema embutido (tokens → cores). |
| `qss_icons.py` | `render_icon_png`: ícone do catálogo em PNG (cache) para `image: url(...)` no QSS. |

## Regras

Lei nº 5: nenhuma cor literal fora daqui; use `get_color(token, fallback)`. A catraca `tests/test_hardcoded_colors_ratchet.py` conta cores literais por arquivo e só deixa cair.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/infrastructure/config`
- `ui/infrastructure/icons`
<!-- /arccc:deps -->
