# `bridge/core/bindings/` — bindings PyBind11

**Responsabilidade:** registrar no módulo `aladyn_engine_native` a `PaintEngineFacade` e os tipos auxiliares, validando buffers na entrada.

## Porta de entrada

`engine_bindings.cpp` (define o módulo e chama cada `bind_*`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `engine_bindings.cpp` | `PYBIND11_MODULE(aladyn_engine_native)`: cria a classe `PaintEngineFacade` e chama os `bind_*`. |
| `BindingsCommon.hpp` | Declarações dos `bind_*` e o alias `FacadeClass`. |
| `BufferContract.hpp` | Validação de dimensões e tamanho de buffers RGBA/cinza antes de chegar ao motor. |
| `bind_math_brush.cpp` | Tipos de matemática e pincel (`Point2D`, curvas, perfil, parâmetros por motor) e a pré-visualização de pincel. |
| `bind_canvas.cpp` | Canvas: redimensionar, limpar, papel, perfis de cor, buffers de exibição e exportação. |
| `bind_layers.cpp` | Camadas: adicionar, grupos, camadas de ajuste, reordenar, propriedades. |
| `bind_stroke.cpp` | Traço e telemetria (métricas em tempo real, diagnóstico). |
| `bind_tools.cpp` | Ferramentas: balde, seleção, transformação, guias e snap. |

## Regras

- Buffer vindo do Python passa por `BufferContract.hpp` antes de chegar ao motor (`tests/test_buffer_contract.py`).
- Binding novo aparece em `bridge/boundary/contracts/aladyn_engine_native.pyi`.

## Dívida conhecida (medida em 2026-09-24)

Inclui arquivos internos do motor (`engine/core/canvas`, `color`, `math`, `raster` e `engine/boundary/public-api/internal`) em vez de só a API pública: pelo ARCcC a ponte deveria depender apenas de `engine/boundary/public-api`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `engine/boundary/public-api`
- `engine/boundary/public-api/internal`
- `engine/core/canvas`
- `engine/core/color`
- `engine/core/math`
- `engine/core/raster`
<!-- /arccc:deps -->
