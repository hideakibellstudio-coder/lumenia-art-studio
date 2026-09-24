# `assets/icons/` — ícones SVG

**Responsabilidade:** os dois ícones em arquivo que o QSS usa quando a renderização em PNG dos botões fechar/maximizar falha.

## Porta de entrada

`ui/core/theme/manager.py` (`@ASSETS_DIR/icons/close.svg` e `maximize.svg`, quando a renderização em PNG falha).

## Arquivos

| Arquivo | Uso |
|---|---|
| `close.svg` | Fallback do ícone do botão fechar no QSS. |
| `maximize.svg` | Fallback do ícone do botão maximizar no QSS. |

## Regras

- Ícone de interface novo entra no catálogo em código (`ui/core/icon_svg_catalog.py`), que troca `currentColor` pela cor do tema.
