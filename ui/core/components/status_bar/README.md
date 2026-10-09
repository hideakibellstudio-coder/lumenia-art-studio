# `ui/core/components/status_bar/` — barra de status

**Responsabilidade:** a barra de status da janela principal (mensagens, zoom e o botão
"Versão gratuita · Ativar" enquanto não há licença). Não conhece licença: a janela diz
se a sessão está no modo gratuito (`show_free_mode`) e liga `activateRequested`.

## Porta de entrada

`from ui.core.components.status_bar import StatusBar`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `StatusBar`. |
| `bar.py` | `StatusBar`: `QStatusBar` com o indicador de zoom e o botão do modo gratuito. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/infrastructure/i18n`
<!-- /arccc:deps -->
