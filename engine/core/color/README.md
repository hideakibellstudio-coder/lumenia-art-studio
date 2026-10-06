# `engine/core/color/` — cor

**Responsabilidade:** os perfis de cor canônicos que UI, rasterizador e arquivo `.lmn` compartilham, a simulação de impressão (CMYK), as tabelas do espaço linear usado pelo Deep Color (e as tabelas exatas que o tiram do `pow` por pixel) e as de 16 bits da mesclagem de um documento de 16 bits e a conversão RGB ↔ HSV.

## Porta de entrada

`ColorProfile.hpp` (`ColorProfileType`, `ColorProfileManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `ColorProfile.hpp` | Ids canônicos de perfil (0–13), nomes e validação (declaração). |
| `ColorProfile.cpp` | Conversões por perfil, incluindo a simulação física de CMYK (ganho de ponto, limite de tinta). |
| `LinearColorSpace.hpp` | Tabelas de transferência sRGB ↔ linear (caminho rápido de 12 bits e caminho de precisão estendida). |
| `DeepColorLut.hpp` | O Deep Color sem `pow` por pixel: as tabelas (`toLinear` dos 256 valores e a escada de `linearToSRGBPrecise`, com os degraus achados por bisecção sobre os próprios doubles) e `blendLinearNormalDeep`, igual bit a bit a `blendLinearNormalHighPrecision` (24 milhões de doubles e 6 milhões de mesclagens conferidos). |
| `DeepColorLut.cpp` | Monta as tabelas uma vez, na primeira mesclagem em Deep Color (uma bisecção sobre os bits dos doubles para cada um dos 255 degraus). |
| `LinearColorSpace16.hpp` | sRGB ↔ linear para canais de 16 bits (S5): a definição em double (`srgbToLinearReference`, `linearToSrgb16Reference`) e as tabelas que a reproduzem sem `pow` por pixel: `toLinear` dos 65536 valores e `encode` interpolada de 16385 pontos (erro máximo 0,223 passo de 16 bits, no balde da junção em 0,0031308; 0,003 acima de 0,05; medido em `tests/native/blend16_checks.cpp`). |
| `LinearColorSpace16.cpp` | Monta as tabelas uma vez, na primeira mesclagem de 16 bits em gama linear (montadas antes de um laço paralelo, não dentro dele). |
| `HsvConversion.hpp` | RGB ↔ HSV em float (usado pelo filtro Matiz/Saturação); saiu de `document/blending` em 2026-09-25. |

## Regras

- Id de perfil novo precisa existir aqui, no catálogo Python (`ui/core/color`) e na validação do `.lmn` (`ui/core/document/schema.py`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/utils`
<!-- /arccc:deps -->
