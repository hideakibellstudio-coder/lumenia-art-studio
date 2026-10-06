# `engine/core/document/blending/` — mesclagem de pixel

**Responsabilidade:** a matemática de mesclar um pixel sobre outro (alpha over e os 13 modos de mesclagem de camada) e o kernel que a aplica a uma linha inteira, com SIMD escolhido pela CPU na hora de rodar (8 bits). Um documento de 16 bits tem a sua definição (`BlendEquations16.hpp`) e o seu kernel (`BlendKernel16`).

## Porta de entrada

`BlendEquations.hpp` (`blendPixel`, a definição de um pixel) e `BlendKernel.hpp` (`BlendKernel::plan` uma vez por camada, `blendRow` por linha: o mesmo resultado de `blendPixel`, bit a bit).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `LayerBlendMode.hpp` | Enum dos modos de mesclagem; espelhado 1:1 por `ui/core/document/layer_blend_mode.py` e reexportado como `document::LayerBlendMode`. |
| `BlendEquations.hpp` | `blendPixel` escolhe o caminho (atalhos exatos do Normal, Erase, Normal em linear ou sRGB, modos separáveis) e cada caminho é uma função com nome em `detail` (CCN máximo 13; era 32 numa função só). O Deep Color usa as tabelas exatas de `core/color/DeepColorLut.hpp`. |
| `ChannelBlend.hpp` | A única tabela das equações de canal dos modos separáveis (`s` e `d` em [0, 1], codificados em sRGB): a mesclagem de 8 bits e a de 16 bits chamam o mesmo caso, então um modo novo entra aqui uma vez e vale nas duas. |
| `BlendKernel.hpp` | O plano de mesclagem de uma camada (modo, gama, profundidade, opacidade, tabelas) e `blendRow`, que mescla uma linha de origem sobre uma de destino; o nível de SIMD (`Scalar`, `Avx2`) é o melhor que a CPU tem (`activeLevel`; `forceLevel` só para teste). |
| `BlendKernel.cpp` | Detecção do nível, o plano, a linha genérica (`blendPixel` com o desvio por modo fora do laço) e o laço escalar do Normal em gama linear de 8 bits, com tabelas fixas. |
| `BlendKernelAvx2.cpp` | O laço AVX2 do mesmo caso (oito pixels por vez, `gather` nas tabelas) e o teste de CPU. Só as funções daqui levam o alvo `avx2` e só rodam depois do teste: o binário escalar distribuído usa AVX2 onde ele existir. |
| `BlendKernelInternal.hpp` | Parte privada dos dois `.cpp` do kernel (tabelas alinhadas, teste de CPU, a linha AVX2). |
| `BlendEquations16.hpp` | `blendPixel16`: a definição de um pixel de 16 bits (S5), em double, lenta e clara. Sem Deep Color (a conta é sempre em precisão alta e arredondada ao inteiro mais próximo; os 8 bits truncam); o atalho exato é o do alfa cheio. |
| `BlendKernel16.hpp` | O plano de mesclagem de 16 bits (modo, gama, opacidade) e `blendRow` (declaração). Sem SIMD ainda: entra se a medição pedir. |
| `BlendKernel16.cpp` | O Normal em gama linear e em sRGB codificado tem laço em float com as tabelas de `core/color/LinearColorSpace16.hpp` (alfa em double, como a definição, porque é ele que decide o atalho do alfa cheio); em gama linear, com AVX2 na CPU e opacidade acima de 1e-12, a linha é a de `BlendKernel16Avx2.cpp`. Os demais casos (modos separáveis, Erase) rodam a própria definição pixel a pixel, com o desvio por modo fora do laço da camada. O nível de SIMD é um só para os dois kernels (`BlendKernel::activeLevel`/`forceLevel`). |
| `BlendKernel16Internal.hpp` | Parte privada dos dois `.cpp` do kernel de 16 bits: a linha escalar e a de AVX2 do Normal em gama linear. |
| `BlendKernel16Avx2.cpp` | O laço AVX2 do Normal em gama linear de 16 bits (oito pixels por vez, `gather` nas duas tabelas, o alfa em double como o escalar): MESMOS bytes que a linha escalar, só no caso comum de destino opaco nos oito pixels (o resto vai para a escalar). Mediu 927 → 476 ms numa composição de 4096² com 10 camadas translúcidas (2 núcleos, `tests/native` e a sonda da S5). |

## Regras

- Não inclui a pasta-mãe (`document/`): trabalha com pixel e modo, não com camada.
- Todo laço do kernel de 8 bits é EXATO: dá os mesmos bytes que `blendPixel`. Laço novo (outro modo, outro nível de SIMD) entra com a sua linha em `tests/native/blend_kernel_checks.cpp`, que compara com a definição em milhões de pixels; aproximação não entra aí.
- O kernel de 16 bits tem UM laço aproximado, o Normal em float (escalar e AVX2, iguais byte a byte entre si): erra no máximo 1 nível de 16 bits contra `blendPixel16` (0,09% dos canais em gama linear e 0,18% em sRGB, de 1,1 milhão de pixels), com o alfa e os atalhos exatos; os outros casos são a própria definição (3840 linhas, 12 modos × 2 gamas × 4 opacidades, idênticas). `tests/native/blend16_checks.cpp` mede os dois e falha se passar de 1 nível.
- Modo novo: valor no enum, caso em `detail::separableBlend` (uma equação de canal; o modo é escolhido uma vez por pixel, não por canal: escolher por canal custou 30% no Darken), espelho em Python e `tests/test_layer_blend_mode_contract.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/color`
- `engine/utils`
<!-- /arccc:deps -->
