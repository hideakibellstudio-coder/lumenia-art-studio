# `engine/core/compression/` — compressão de tiles

**Responsabilidade:** comprimir e descomprimir blocos de memória (tiles inativos e histórico) com LZ4.

## Porta de entrada

`Lz4Codec.hpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Lz4Codec.hpp` | Interface do codec: capacidade de pior caso, `compress`, `decompress`. |
| `Lz4Codec.cpp` | Implementação LZ4 própria (sem dependência externa). |

## Regras

- Sem dependência de nenhuma outra pasta do motor; qualquer uso de compressão passa por aqui.

## Dívida conhecida (medida em 2026-09-24)

É um utilitário: pelo ARCcC ficaria em `engine/utils/` (ou `infrastructure/`), não entre os domínios.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
