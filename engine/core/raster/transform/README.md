# `engine/core/raster/transform/` — núcleo da transformação

**Responsabilidade:** a matemática de amostrar a imagem de origem para cada pixel de destino, comum à transformação livre e à distorção.

## Porta de entrada

`InverseMappedComposite.hpp` (`compositeInverseMapped`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Homography.hpp` | Transformação projetiva de 4 cantos usada por Distorcer. |
| `InverseMappedComposite.hpp` | Composição por mapeamento inverso: para cada pixel de destino, de onde ele vem na origem. |
| `TransformSamplers.hpp` | Amostradores (vizinho mais próximo, bilinear, bicúbico). |

## Regras

- Só `../TransformEngine*.cpp` inclui esta pasta.

## Dívida conhecida (medida em 2026-09-24)

`Homography.hpp` declara a struct `Homografia` (nome em português, contra a seção 14 do ARCcC).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/raster`
<!-- /arccc:deps -->
