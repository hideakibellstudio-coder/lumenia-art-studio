# `ui/core/theme/` — tema e cores

**Responsabilidade:** o `ThemeManager`: paletas de cor, escala da interface, folha de estilo global e os sinais `themeChanged`/`scaleChanged`.

## Porta de entrada

`from ui.core.theme.manager import ThemeManager` (34 consumidores); `ThemeManager.instance().get_color(TOKEN, fallback)`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ThemeManager`. |
| `manager.py` | `ThemeManager` (singleton): tema atual, `get_color`, escala, aplicação da folha de estilo e sinais de mudança. |
| `palettes.py` | Paletas de cor de cada tema embutido (tokens → cores). |

## Regras

Lei nº 5: nenhuma cor literal fora daqui; use `get_color(token, fallback)`. A catraca `tests/test_hardcoded_colors_ratchet.py` conta cores literais por arquivo e só deixa cair.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/config`
<!-- /arccc:deps -->
