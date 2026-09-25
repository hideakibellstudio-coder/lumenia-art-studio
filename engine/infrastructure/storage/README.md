# `engine/infrastructure/storage/` — disco de rascunho

**Responsabilidade:** o arquivo de rascunho em disco onde o histórico pagina blocos antigos quando passa do limite de memória.

## Porta de entrada

`ScratchDiskManager.hpp` (namespace `storage`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ScratchDiskManager.hpp` | Arquivo de rascunho: gravar/ler blocos com checksum, purgar (declaração). |
| `ScratchDiskManager.cpp` | Implementação; nome de arquivo único por processo e limpeza na saída. |

## Regras

- Só o histórico (`engine/core/history`) usa esta pasta; o teste de falhas `tests/native/history_faults.cpp` injeta um disco que falha.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
