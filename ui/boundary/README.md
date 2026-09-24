# `ui/boundary/` — casca da aplicação

**Responsabilidade:** agrupa a camada mais externa da interface: a janela principal, o boot e (no futuro) a API pública para plugins de terceiros.

## Porta de entrada

Nenhuma: use `ui.boundary.orchestrator`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote; vazio. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
