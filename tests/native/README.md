# `tests/native/` — harnesses nativos do motor

**Responsabilidade:** compilar e rodar executáveis C++ que exercitam o motor sem passar pela ponte: falhas reais de E/S e de codec no histórico de tiles, a independência de ordem do Borrar e os pixels do `blendPixel` em todos os modos.

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
| `build_blend_pins.py` | Fontes do harness do `blendPixel` (só o cabeçalho: nenhum fonte do motor). |
| `blend_pixel_pins.cpp` | Resume em hash 4096 casos determinísticos por combinação de modo (13) × gama linear/sRGB × 8 bits/Deep Color (52) e compara com os hashes gravados antes da divisão do `blendPixel`; `--print` regrava a tabela. |

## Regras

- O executável vai para o diretório de build (`../build`, ou `build/` ignorado pelo git quando não há pasta irmã); nunca para esta pasta.
