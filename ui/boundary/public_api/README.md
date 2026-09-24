# `ui/boundary/public_api/` — API pública (reservada)

**Responsabilidade:** reservada para a API estável que plugins de terceiros poderão importar. Hoje está vazia.

## Porta de entrada

Nenhuma. Plugins usam hoje `ui.core.plugins` (BasePlugin, PluginMetadata, WorkspaceService) e `ui.core.state`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Vazio. |

## Dívida conhecida (medida em 2026-09-24)

Pasta sem conteúdo. Ou vira a porta única da API de plugins (reexportando o que plugins podem usar), ou sai.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
