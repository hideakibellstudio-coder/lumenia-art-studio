# `tests/native/` — harnesses nativos do motor

**Responsabilidade:** compilar e rodar executáveis C++ que exercitam o motor sem passar pela ponte: falhas reais de E/S e de codec no histórico de tiles, a independência de ordem do Borrar, os pixels do `blendPixel` em todos os modos e o núcleo de dab com o codec de tiles e o pixel de 16 bits (armazenamento, conversão, codec e histórico).

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
| `build_dab_core_checks.py` | Fontes do harness do núcleo de dab (pegada, permissão, ponta, alfa over e o codec de tiles). |
| `dab_core_checks.cpp` | Confere sem Python: a pegada de um dab visita exatamente os pixels que uma varredura bruta acha dentro da elipse (redonda e achatada, girada, na borda do canvas e com o círculo encostando num tile); seleção e camada-base do recorte; alfa over e Alpha Lock; queda da ponta; e o codec de tiles (ida e volta, bloco malformado recusado sem tocar a grade). |
| `build_blend_pins.py` | Fontes do harness do `blendPixel` (só `DeepColorLut.cpp`, que o caminho Deep Color usa). |
| `blend_pixel_pins.cpp` | Resume em hash 4096 casos determinísticos por combinação de modo (13) × gama linear/sRGB × 8 bits/Deep Color (52) e compara com os hashes gravados antes da divisão do `blendPixel`; `--print` regrava a tabela. |
| `build_blend_kernel_checks.py` | Fontes do harness do kernel de mesclagem (`BlendKernel.cpp`, `BlendKernelAvx2.cpp`, `DeepColorLut.cpp`). |
| `blend_kernel_checks.cpp` | Confere o kernel de linha e as tabelas do Deep Color contra as definições, byte a byte: a escada sRGB (24 milhões de doubles, os vizinhos de cada degrau), 6 milhões de mesclagens Deep Color, 33 mil linhas (modo × gama × profundidade × opacidade × comprimento × padrão de alfa, com pixels-guarda contra escrita fora da linha) em cada nível de SIMD, e 4 milhões de pixels em linhas de comprimento ímpar com o nível escalar contra o AVX2. |
| `build_pixel_format_checks.py` | Fontes do harness do formato de pixel (tile, grade, codec, pilha de camadas, histórico, compositor e mesclagem). |
| `pixel_format_checks.cpp` | Confere o pixel de 16 bits sem Python: a conversão (256 valores de 8 bits, 65536 de 16, 100 mil cores), `PixelBuffer`, `Tile`, `TileGrid` (cinco redimensionamentos com deslocamento iguais ao mesmo nos dois planos de bytes, alto e baixo, de cada canal) e o codec do bloco nos dois formatos (cabeçalho, ida e volta, e recusa de bloco de outro formato, de formato desconhecido, truncado, com tile cru de tamanho de 8 bits e de 9000 px em 16 bits). Liga o executável ao `pixel_format_document_checks.cpp`. |
| `pixel_format_document_checks.cpp` | As camadas que uma pilha de 16 bits cria, copia e redimensiona; histórico de tile (tile novo e tile existente, desfazer e refazer byte a byte, e o "antes" de tamanho de 8 bits recusado) e de estrutura num documento de 16 bits; e as guardas do compositor e da mesclagem de 8 bits. |
| `build_blend16_checks.py` | Fontes do harness da mesclagem de 16 bits (`BlendKernel16.cpp`, `BlendKernel16Avx2.cpp`, o kernel de 8 bits que escolhe o nível de SIMD, `LinearColorSpace16.cpp`, `DeepColorLut.cpp`). |
| `blend16_checks.cpp` | Confere a mesclagem de 16 bits (S5): as tabelas sRGB (erro de `toLinear`, a codificação interpolada dentro de 0,25 passo, ida e volta exata nos 65536 valores), o kernel do Normal em gama linear e sRGB contra `blendPixel16` em 1,1 milhão de pixels cada (no máximo 1 nível, alfa e atalhos exatos), os demais modos idênticos à definição (3840 linhas) o laço AVX2 do Normal linear, byte a byte igual ao escalar (80 mil pixels em todo comprimento de 0 a 40, 9 opacidades, destino opaco, translúcido e vazio, com pixels-guarda) e os 13 modos contra a mesclagem de 8 bits em valores exatos de 8 bits. |
| `build_compositor16_checks.py` | Fontes do harness do compositor de 16 bits (compositor, passada de camadas, mesclagem, filtros de 16 bits, codec e histórico de tiles). |
| `compositor16_scene.hpp` | Cenas compartilhadas dos três arquivos do harness: o plano (pilha de camadas aleatória) construído em 8 bits e em 16 bits alargado, a composição e a medida da distância entre duas imagens. |
| `compositor16_checks.cpp` | Concordância: pilhas Normal em gama linear e sRGB (contra um modelo por pixel da definição e contra o documento de 8 bits), outros modos sobre base opaca (idênticos ao modelo), grupos isolados e Pass Through, recortes e camadas ocultas, e os sete filtros entre camadas. |
| `compositor16_lazy_checks.cpp` | Os 16 bits sobrevivem (rampa de 300 valores dentro de 2 níveis de 8 bits), a projeção preguiçosa (84 edições sob desfoque e pixelização, 252 janelas, iguais byte a byte a uma composição inteira, no buffer de 16 bits e na tela; e 80 edições sob grupos isolados, Pass Through e recorte, 240 janelas, porque uma janela composta sozinha põe o acumulador do grupo no deslocamento dela), as mesclagens e o `main` do harness. |
| `filter16_checks.cpp` | Cada um dos sete filtros de 16 bits contra o de 8 bits em entrada idêntica (17 ajustes × 2 opacidades × buffer inteiro e sub-retângulo): no máximo 2 níveis, nada fora do retângulo e nenhum pixel de alfa 0 alterado. |
| `build_composite_projection_checks.py` | Fontes do harness da projeção do buffer composto (a projeção, o compositor, os filtros e o kernel de mesclagem). |
| `composite_projection_checks.cpp` | Confere a `CompositeProjection` contra um modelo de um bool por tile que responde por interseção de intervalos: 600 operações aleatórias em cada um de 7 canvases (de 1x1 a 1024x1024; retângulos dentro, cruzando e fora, vazios e invertidos), comparando contagem, `expandToStale` e `staleRects` (caixas alinhadas a tile, sem sobreposição, cobrindo exatamente os tiles velhos), mais as formas de resposta conhecida (canvas velho é uma caixa, xadrez é uma caixa por tile) e o tile da borda. Liga o executável ao `compositor_stale_checks.cpp`. |
| `compositor_stale_checks.cpp` | Confere o que o `Compositor` recompõe e onde: nasce velho, `invalidate` não compõe, ler outro tile não compõe, ler o tile compõe só ele, sentinelas em tiles que não deviam ser escritos, composição por região em tiles inteiros (e só roçando o vizinho pela margem de 2 px), tinta de traço que um `ensureFresh` seguinte não apaga, o alcance de um desfoque (uma edição 8 px antes da borda do tile marca o tile vizinho), e 40 cenas de edições sob desfoque e pixelizar, invalidadas pela região e lidas em janelas aleatórias, em que toda janela lida sozinha e todo canvas lido por inteiro são iguais à composição inteira. |

## Regras

- O executável vai para o diretório de build (`../build`, ou `build/` ignorado pelo git quando não há pasta irmã); nunca para esta pasta.
