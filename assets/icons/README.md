# `assets/icons/` — ícones SVG

**Responsabilidade:** ícones em arquivo; hoje só dois servem de fallback para o QSS dos botões fechar/maximizar.

## Porta de entrada

`ui/core/theme/manager.py` (`@ASSETS_DIR/icons/close.svg` e `maximize.svg`, quando a renderização em PNG falha).

## Conteúdo

| Pasta | Conteúdo |
|---|---|
| `geometry/` | Cópia dos ícones de régua e simetria (ver dívida). |
| `plugins_hash/` | Ícones com nome por hash e o índice deles (ver dívida). |

## Regras

- Ícone de interface novo entra no catálogo em código (`ui/core/icon_svg_catalog.py`), que troca `currentColor` pela cor do tema.

## Dívida conhecida (medida em 2026-09-24)

93 dos 95 SVG desta pasta e o `icon_index.json` não têm consumidor no código (medido em 2026-09-24).
