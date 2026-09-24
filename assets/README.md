# `assets/` — recursos da aplicação

**Responsabilidade:** arquivos que a aplicação carrega em tempo de execução: traduções, guia do usuário, ícone da janela.

## Porta de entrada

`ui.core.runtime_paths.resource_path("assets", ...)` — funciona no repositório e na distribuição empacotada.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `locales/` | Traduções da interface (4 idiomas). |
| `docs/` | Guia do usuário por idioma (diálogo de ajuda). |
| `images/` | Ícone da aplicação. |
| `icons/` | Ícones SVG (ver dívida). |

## Regras

- Recurso novo é carregado por `resource_path`, nunca por caminho relativo ao diretório atual.

## Dívida conhecida (medida em 2026-09-24)

Os ícones da interface vêm do catálogo em código (`ui/core/icon_svg_catalog.py`); de `icons/` só `close.svg` e `maximize.svg` são usados (fallback do QSS). Medido em 2026-09-24: 158 dos 160 SVG de `icons/` não têm consumidor.
