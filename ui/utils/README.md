# `ui/utils/` — funções puras

**Responsabilidade:** funções matemáticas puras da interface (`clamp`, `lerp`).

## Porta de entrada

`from ui.utils import clamp, lerp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | ui.utils — Funções Utilitárias Puras da Camada de Apresentação (ARCcC). |

## Dívida conhecida (medida em 2026-09-24)

Nenhum módulo importa esta pasta hoje (medido): candidata a sair ou a ser usada pelos que reimplementam `max(min(...))`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
