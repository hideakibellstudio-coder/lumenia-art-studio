# `engine/core/document/` — documento e camadas

**Responsabilidade:** a estrutura de camadas do documento (camada, grupo, camada de ajuste), a pilha com o papel na camada 0, mesclar e achatar, e o compositor que junta tudo num buffer (de 8 bits, ou de 16 com o resultado estreitado para a tela).

## Porta de entrada

`LayerStack.hpp` (pilha) e `Compositor.hpp` (composição).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `Compositor.hpp` | Compositor de um formato de pixel (`Compositor(w, h, formato)`): modos de mesclagem, filtros, opções do pipeline e o retângulo que ele escreveu desde a última leitura (`takeDamage`: toda escrita no buffer de saída passa por aqui, então só ele sabe o que mudou) e a projeção do buffer de saída: `invalidate`/`invalidateAll` marcam tiles velhos sem compor, `ensureFresh`/`ensureAllFresh` recompõem só os tiles velhos da área que alguém vai ler. Num documento de 16 bits a pilha é composta num buffer interno de 16 bits (`composite16()`, alocado na primeira leitura) e só a região composta é estreitada para o buffer de saída de 8 bits (declaração). |
| `Compositor.cpp` | Composição total e por região: as duas sobrecargas de região chamam `compositeLayers` (limites, fundo, dano) e a passada sobre as camadas é de `LayerCompositePass`. Com filtro de área na pilha, a região é composta com o dobro do alcance como contexto e só a área que a mudança pode alterar (a região mais um alcance) vai para o buffer de saída; a faixa de fora volta como estava (`tests/test_composite_region_filters.py`). Dona de uma `CompositeProjection`: o buffer de saída só é refeito onde alguém lê (S3); as composições por região (traço, colagem, balde, transformação) refazem inteiros os tiles velhos que tocam e deixam frescos os que cobrem por inteiro (`tests/native/compositor_stale_checks.cpp`). Em 16 bits o Deep Color é ignorado (a conta é sempre em precisão alta) e a gama linear vale; não há dithering. Um compositor recusa camada de outro formato (`std::logic_error`). |
| `CompositeRegionSupport.hpp` | Parte privada do compositor (namespace `document::internal`): só geometria, a mesma para os dois formatos de pixel: alcance dos filtros, base de recorte, fundo, grupos isolados, opacidade relativa e os limites da região (`computeRegionBounds`) (declaração). |
| `CompositeRegionSupport.cpp` | Implementação; veio da antiga subpasta `internal/`, que incluía esta pasta (ciclo). |
| `CompositePixel.hpp` | O que a composição precisa saber do pixel que compõe (`CompositePixel<Pixel>`): o plano de mesclagem de linha, a definição de um pixel e o alfa em [0, 1] de cada formato; é o que deixa `GroupBlender` e `LayerCompositePass` serem escritos uma vez (S5). |
| `GroupBlender.hpp` | `GroupBlender<Pixel>`: compõe tiles de camada para o buffer de saída ou para o acumulador de um grupo isolado e o funde contra o destino quando o grupo fecha; uma camada de outro formato é recusada antes de qualquer escrita (declaração). |
| `GroupBlender.cpp` | Implementação e as duas instâncias (8 e 16 bits). A passada por tiles lê cada tile por `Tile::view` num buffer por thread (tile comprimido segue comprimido) e busca o tile da base do recorte uma vez por tile, não uma por pixel. Monta o plano de mesclagem da camada uma vez e mescla cada linha do tile de uma vez; só o laço com base de recorte segue pixel a pixel. |
| `RegionBuffer.hpp` | O buffer em que uma composição por região escreve, para os dois formatos: `fillBackground` (alarga a cor de fundo ×257 num buffer de 16 bits), `RegionMargin` (a margem que o filtro pede para ter vizinhos e que volta ao buffer como estava, em bytes) e `narrowRegion` (a passagem do buffer composto de 16 bits para o de saída de 8) (declaração). |
| `RegionBuffer.cpp` | Implementação; o laço de `narrowRegion` é paralelo e só toca a região composta. |
| `LayerCompositePass.hpp` | Uma passada de composição (`LayerCompositePass<Pixel>`, `Pixel` = `ColorRGBA` ou `ColorRGBA16`): recebe as camadas de baixo para cima e carrega de uma para a seguinte o grupo isolado aberto; `CompositePolicy` e `ScratchOverlay` são o que distingue as duas sobrecargas de região (declaração). |
| `LayerCompositePass.cpp` | Grupo, filtro e tile de cada camada, mais o overlay do traço ativo logo acima da camada que ele sobrepõe, escritos uma vez para `Pixel` e instanciados para os dois formatos. Era o laço duplicado em `Compositor.cpp` (CCN 17 e 12 numa só função). |
| `FilterLayer.hpp` | Camada de ajuste: tipo de filtro, parâmetros e `settings()` para `filters/` (declaração). |
| `FilterLayer.cpp` | Valores padrão de cada filtro. |
| `Layer.hpp` | Camada raster: nó + `TileGrid` (no formato de pixel do documento) + compressão de tiles inativos. |
| `LayerMerger.hpp` | Achatar grupo e mesclar para baixo (declaração). |
| `LayerMerger.cpp` | Implementação, reassociando pais e validando índices; mesclar para baixo e achatar grupo usam a mesma passada `blendGridAs<Pixel>` (com ou sem recorte à base), nos dois formatos; uma pilha mista é recusada. |
| `LayerNode.hpp` | Nó comum da árvore de camadas: tipo, modo de mesclagem, opacidade, visibilidade, travas, recorte. |
| `LayerStack.hpp` | Pilha de camadas (camada 0 = papel) de um formato de pixel (`getPixelFormat()`: toda camada que ela cria, copia ou redimensiona tem esse formato): adicionar, remover, redimensionar, restaurar (declaração). |
| `LayerStack.cpp` | Implementação; aloca tudo antes de mexer na pilha viva. |

| Pasta | Responsabilidade |
|---|---|
| `blending/` | Equações de mesclagem de pixel e o enum `LayerBlendMode`. |
| `filters/` | Filtros das camadas de ajuste (`FilterApplier`, `FilterType`, núcleos). |
| `projection/` | Quais tiles de 128x128 do buffer composto estão velhos (`CompositeProjection`): quem muda o documento marca, quem lê recompõe só o que lê. |

## Regras

- A composição é escrita uma vez para `Pixel` (`ColorRGBA` ou `ColorRGBA16`) e instanciada para os dois formatos; o 8 bits não muda um byte por causa do 16 (`tests/test_composite_projection_native.py`, as fixações do compositor e os goldens seguem iguais). A medição dos 16 bits está em `tests/native/compositor16_checks.cpp`.
- A árvore de camadas do motor espelha o `LocalLayerManager` da UI; quem sincroniza é `ui/core/document/layer_backend_sync.py` (escritor único).
- As subpastas não incluem esta pasta: os enums que as duas lados usam moram nelas (`blending/LayerBlendMode.hpp`, `filters/FilterSettings.hpp`) e o documento os reexporta como `document::LayerBlendMode` e `document::FilterType`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/canvas`
- `engine/core/document/blending`
- `engine/core/document/filters`
- `engine/core/document/projection`
- `engine/utils`
<!-- /arccc:deps -->
