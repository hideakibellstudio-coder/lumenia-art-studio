# `tests/native/` — harness nativo de falhas do histórico

**Responsabilidade:** compilar e rodar um executável C++ que injeta falhas reais de E/S e de codec no histórico de tiles.

## Porta de entrada

`build_history_faults.py` (compila `history_faults.cpp` com o mesmo compilador da extensão).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `build_history_faults.py` | Compila o harness na pasta de build fora da árvore. |
| `history_faults.cpp` | Cenários de falha do `TileUndoManager` (disco de rascunho, codec, vários tiles). |

## Regras

- O executável vai para o diretório de build (`../build`, ou `build/` ignorado pelo git quando não há pasta irmã); nunca para esta pasta.
