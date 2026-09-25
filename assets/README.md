# `assets/` — recursos da aplicação

**Responsabilidade:** arquivos que a aplicação carrega em tempo de execução: traduções, guia do usuário, ícone da janela.

## Porta de entrada

`ui.infrastructure.runtime_paths.resource_path("assets", ...)` — funciona no repositório e na distribuição empacotada.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `locales/` | Traduções da interface (4 idiomas). |
| `docs/` | Guia do usuário por idioma (diálogo de ajuda). |
| `images/` | Ícone da aplicação. |
| `icons/` | Os dois SVG de fallback do QSS (fechar e maximizar). |
| `legal/` | Avisos de licença de terceiros (LGPLv3 do Qt e demais) que a distribuição leva. |

## Regras

- Recurso novo é carregado por `resource_path`, nunca por caminho relativo ao diretório atual.

Os ícones da interface vêm do catálogo em código (`ui/infrastructure/icons/svg_catalog.py`).
Até 2026-09-24 `icons/` tinha 160 SVG, 158 sem nenhum consumidor (e 15 cópias
dos ícones do plugin de geometria); saíram.
