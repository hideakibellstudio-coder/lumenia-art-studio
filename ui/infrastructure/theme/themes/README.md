# `ui/infrastructure/theme/themes/` — temas

**Responsabilidade:** as paletas de cor e métricas de cada tema, em JSON, e os módulos QSS que viram a folha de estilo.

## Porta de entrada

`ui/infrastructure/theme/manager.py` (`ThemeManager`) carrega todos os `.json` desta pasta.

## Conteúdo

| Item | Conteúdo |
|---|---|
| `*.json` | Um tema por arquivo (`colors`, `metrics`): cyberpunk, dark_default, light_default, lumenia_light, lumenia_purple, nordic_frost, oled_black, paper_white, warm_ochre. |
| `qss_modules/` | A folha de estilo em módulos, com tokens `@COR` resolvidos pelo tema. |

## Regras

- Tema novo tem todas as chaves de cor dos outros (`tests/test_theme_system.py`); código nunca usa cor literal (Lei nº 5).
