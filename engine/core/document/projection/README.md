# `engine/core/document/projection/` — o que do buffer composto está velho

**Responsabilidade:** lembrar, por tile de 128x128, se o buffer composto naquele tile ainda é o que a composição das camadas daria, para que o motor só componha o que alguém vai ler.

## Porta de entrada

`CompositeProjection.hpp`. Quem a usa é o `Compositor` (`invalidate`, `invalidateAll`, `ensureFresh`), que é dono de uma; ninguém mais mexe nela.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CompositeProjection.hpp` | `PixelRect` e a projeção: `markStale`/`markAllStale` (barato: um byte por tile), `markFresh` (só tile INTEIRO dentro do retângulo composto), `expandToStale` (o retângulo e os tiles velhos que ele toca, para uma composição por região nunca deixar um tile pela metade) e `staleRects` (os tiles velhos de uma área em poucas caixas alinhadas a tile) (declaração). |
| `CompositeProjection.cpp` | Implementação; as caixas de `staleRects` juntam tiles vizinhos pelas corridas iguais de colunas em linhas seguidas, então um canvas inteiro velho é uma caixa. |

## Regras

- Invariante: tile fresco => o buffer composto nele é igual ao da composição inteira. Marcar velho a mais só custa trabalho; marcar fresco a mais mostraria um pixel velho. Por isso `markFresh` não aceita tile parcial.
- Não sabe nada de camadas nem de pixels: quem sabe o que uma mudança alcança (a região, o alcance dos filtros de área, o bloco do pixelizar) é o `Compositor`.
- Todo leitor do buffer composto passa por `Compositor::ensureFresh`/`ensureAllFresh` antes de ler; leitor novo sem esse portão mostra um pixel velho. O mapa dos leitores está em `docs/01-correcao-da-base/07-analise-arccc-decomposta.md` (S3) e a prova de que a tela é igual a uma recomposição total, em `tests/test_composite_projection.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
<!-- /arccc:deps -->
