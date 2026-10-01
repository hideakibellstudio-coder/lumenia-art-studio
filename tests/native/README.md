# `tests/native/` — harnesses nativos do motor

**Responsabilidade:** compilar e rodar executáveis C++ que exercitam o motor sem passar pela ponte: falhas reais de E/S e de codec no histórico de tiles, e a independência de ordem do Borrar.

## Porta de entrada

`harness_build.py` (`build_harness(nome, fontes)`: compila um executável com o mesmo compilador da extensão). Cada harness tem o seu `build_*.py`, que só lista as fontes.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `harness_build.py` | Compilação comum a todo harness (ambiente do Visual Studio, pasta de build fora da árvore, recompila só se a fonte mudou). |
| `build_history_faults.py` | Fontes do harness de falhas do histórico. |
| `history_faults.cpp` | Cenários de falha do `TileUndoManager` (disco de rascunho, codec, vários tiles). |
| `build_smudge_checks.py` | Fontes do harness do Borrar. |
| `smudge_source_snapshot.cpp` | Pinta o mesmo traço do Borrar com a cena deslocada de modo a cruzar outras fronteiras de tile, nos dois sentidos; falha se o resultado mudar. |

## Regras

- O executável vai para o diretório de build (`../build`, ou `build/` ignorado pelo git quando não há pasta irmã); nunca para esta pasta.
