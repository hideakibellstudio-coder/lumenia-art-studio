# `ui/infrastructure/` — infraestrutura

**Responsabilidade:** serviços técnicos sem regra de negócio (hoje, o logging). A fachada antiga do motor (`bridge_client`) saiu em 2026-09-24: o motor se alcança só pelo `EngineRegistry`.

## Porta de entrada

Nenhuma; use as subpastas.

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
