# `ui/core/components/status_bar/` — barra de status

**Responsabilidade:** a barra de status da janela principal (mensagens e zoom).

## Porta de entrada

`from ui.core.components.status_bar import StatusBar`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `StatusBar`. |
| `bar.py` | `StatusBar`: `QStatusBar` com o indicador de zoom. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
