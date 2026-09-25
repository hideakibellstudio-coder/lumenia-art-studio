# `engine/core/history/` — histórico (desfazer/refazer)

**Responsabilidade:** o histórico do documento: passos de pixels por tile (o estado anterior de cada tile tocado), passos de estrutura (pilha de camadas e seleção), limites de memória e paginação em disco.

## Porta de entrada

`TileUndoManager.hpp` (namespace `history`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `TileUndoManager.hpp` | Histórico por tile e por estrutura: `beginStep`/`recordTileBefore`/`commitStep`, `undo`/`redo`, limites de memória (declaração). |
| `TileUndoManager.cpp` | Implementação: passos, compressão LZ4 e paginação para o disco de rascunho. |
| `TileHistoryRestore.cpp` | Restauração de tiles a partir do histórico, alocando tudo antes de publicar o estado. |

## Regras

- Alteração de pixel passa por `TileUndoManager::recordTileBefore` antes de escrever.
- Veio de `canvas/` em 2026-09-25: o histórico conhece a pilha de camadas e a seleção, que ficam acima dos tiles.
- Falhas de disco e de codec: `tests/native/history_faults.cpp`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document`
- `engine/core/selection`
- `engine/infrastructure/compression`
- `engine/infrastructure/storage`
<!-- /arccc:deps -->
