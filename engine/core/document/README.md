# `engine/core/document/` — documento e camadas

**Responsabilidade:** a estrutura de camadas do documento (camada, grupo, camada de ajuste), a pilha com o papel na camada 0, mesclar e achatar, e o compositor que junta tudo num buffer.

## Porta de entrada

`LayerStack.hpp` (pilha) e `Compositor.hpp` (composição).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Compositor.hpp` | Compositor: modos de mesclagem, filtros, opções do pipeline e o retângulo que ele escreveu desde a última leitura (`takeDamage`: toda escrita no buffer de saída passa por aqui, então só ele sabe o que mudou) (declaração). |
| `Compositor.cpp` | Composição total e por região: as duas sobrecargas de região chamam `compositeLayers` (limites, fundo, dano) e a passada sobre as camadas é de `LayerCompositePass`. Com filtro de área na pilha, a região é composta com o dobro do alcance como contexto e só a área que a mudança pode alterar (a região mais um alcance) vai para o buffer de saída; a faixa de fora volta como estava (`tests/test_composite_region_filters.py`). |
| `CompositeRegionSupport.hpp` | Parte privada do compositor (namespace `document::internal`): alcance dos filtros, base de recorte, fundo, grupos isolados e `RegionMargin` (a margem que o filtro pede para ter vizinhos e que volta ao buffer como estava) (declaração). |
| `CompositeRegionSupport.cpp` | Implementação; veio da antiga subpasta `internal/`, que incluía esta pasta (ciclo). |
| `LayerCompositePass.hpp` | Uma passada de composição (`LayerCompositePass`): recebe as camadas de baixo para cima e carrega de uma para a seguinte o grupo isolado aberto; `CompositePolicy` e `ScratchOverlay` são o que distingue as duas sobrecargas de região (declaração). |
| `LayerCompositePass.cpp` | Grupo, filtro e tile de cada camada, mais o overlay do traço ativo logo acima da camada que ele sobrepõe. Era o laço duplicado em `Compositor.cpp` (CCN 17 e 12 numa só função). |
| `FilterLayer.hpp` | Camada de ajuste: tipo de filtro, parâmetros e `settings()` para `filters/` (declaração). |
| `FilterLayer.cpp` | Valores padrão de cada filtro. |
| `Layer.hpp` | Camada raster: nó + `TileGrid` + compressão de tiles inativos. |
| `LayerMerger.hpp` | Achatar grupo e mesclar para baixo (declaração). |
| `LayerMerger.cpp` | Implementação, reassociando pais e validando índices; mesclar para baixo e achatar grupo usam a mesma passada `blendGridInto` (com ou sem recorte à base). |
| `LayerNode.hpp` | Nó comum da árvore de camadas: tipo, modo de mesclagem, opacidade, visibilidade, travas, recorte. |
| `LayerStack.hpp` | Pilha de camadas (camada 0 = papel): adicionar, remover, redimensionar, restaurar (declaração). |
| `LayerStack.cpp` | Implementação; aloca tudo antes de mexer na pilha viva. |

| Pasta | Responsabilidade |
|---|---|
| `blending/` | Equações de mesclagem de pixel e o enum `LayerBlendMode`. |
| `filters/` | Filtros das camadas de ajuste (`FilterApplier`, `FilterType`, núcleos). |

## Regras

- A árvore de camadas do motor espelha o `LocalLayerManager` da UI; quem sincroniza é `ui/core/document/layer_backend_sync.py` (escritor único).
- As subpastas não incluem esta pasta: os enums que as duas lados usam moram nelas (`blending/LayerBlendMode.hpp`, `filters/FilterSettings.hpp`) e o documento os reexporta como `document::LayerBlendMode` e `document::FilterType`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document/blending`
- `engine/core/document/filters`
- `engine/utils`
<!-- /arccc:deps -->
