# `engine/core/brush/` — perfil e dinâmica do pincel

**Responsabilidade:** o que descreve um pincel (motor, ponta, curvas, texturas, parâmetros de cada mini-motor) e como pressão e velocidade viram tamanho, opacidade e dispersão de cada dab.

## Porta de entrada

`BrushProfile.hpp` (struct do perfil e enum `EngineType`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `BrushProfile.hpp` | Perfil completo do pincel: `EngineType`, parâmetros de cada motor (`PencilParams`, `InkerParams`, `MarkerParams`, `BlurParams`, `SmudgeParams`...), curvas e texturas. |
| `BrushTip.hpp` | Geometria da ponta: ângulo, achatamento, seguir o traço e jitters. |
| `DynamicMapper.hpp` | `DynamicMapper`/`MappedBrushState`: estado do dab (tamanho, fluxo, ângulo da ponta, achatamento) a partir de pressão, velocidade, inclinação e perfil. A direção do traço não entra aqui: é do caminho e o interpolador a soma. |
| `DynamicMapper.cpp` | Implementação do mapeamento dinâmico e da dispersão (scatter), com os controles escalares de 0 a 1 `velocityToFlow` (traço rápido deposita menos), `tip.tiltToSize` (caneta deitada dobra o diâmetro com 1,0) e `tip.tiltToFlow` (caneta deitada apaga com 1,0), todos desligados no padrão. |
| `TiltShading.hpp` | A inclinação da caneta (`pen_tilt::lean`: 0 em pé ou com mouse, 1 deitada) e, sobre ela, o lado do grafite: com o interruptor do Lápis ligado e a caneta deitada, a marca se alonga no sentido em que a caneta pende e deposita menos por área. Só o cabeçalho. |

## Regras

- Parâmetro novo de pincel entra no perfil aqui, é lido pelo mini-motor em `engines/` e chega da UI pela tabela `ui/infrastructure/bridge_client/brush_param_table.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/core/math`
- `engine/core/texture`
- `engine/utils`
<!-- /arccc:deps -->
