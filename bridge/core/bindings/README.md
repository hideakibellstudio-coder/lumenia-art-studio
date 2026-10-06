# `bridge/core/bindings/` — bindings PyBind11

**Responsabilidade:** registrar no módulo `aladyn_engine_native` a `PaintEngineFacade` e os tipos auxiliares, validando buffers na entrada.

## Porta de entrada

`engine_bindings.cpp` (define o módulo e chama cada `bind_*`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `engine_bindings.cpp` | `PYBIND11_MODULE(aladyn_engine_native)`: cria a classe `PaintEngineFacade` e chama os `bind_*`. |
| `BindingsCommon.hpp` | Inclui a porta única do motor (`AladynEngine.hpp`); declara os `bind_*` e o alias `FacadeClass`. |
| `bind_math_brush.cpp` | Tipos de matemática e pincel (`Point2D`, curvas, perfil, parâmetros por motor) e a prévia do traço. |
| `bind_canvas.cpp` | Canvas: redimensionar, limpar, papel, perfis de cor, buffers de exibição e exportação; o formato de pixel do documento (`get_pixel_format`, `max_canvas_dimension(pixel_format)`) e as leituras de 16 bits (`get_composite_pixel_buffer16`, `get_composite_region16`, `get_layer_pixel_buffer16`: 8 bytes por pixel, S5). `refresh_display` não faz nada de propósito: a tela o chama a cada evento de câmera e o motor compõe só o que `get_display_region` e os LODs leem. |
| `bind_layers.cpp` | Camadas: adicionar, grupos, camadas de ajuste, reordenar, propriedades. |
| `bind_persistence.cpp` | Persistência (S1.2): `LayerSnapshot` (o instantâneo das camadas; `encode_layer` roda sem o GIL), `snapshot_layers`, `restore_layer_tiles`, `DecodedLayer` com `decode_layer_tiles`/`adopt_decoded_layer` (decodificar fora do documento, adotar em tempo constante) e o par `begin_batch`/`end_batch` (contrato sem efeito desde a S3: o motor só compõe o que alguém lê). |
| `bind_stroke.cpp` | Traço, texturas e prévias da ponta, telemetria (métricas em tempo real, diagnóstico). |
| `bind_tools.cpp` | Ferramentas: balde, seleção, transformação, guias e snap. |

## Regras

- Do motor, só `BindingsCommon.hpp` inclui algo, e só `engine/boundary/public-api/AladynEngine.hpp`.
- Buffer vindo do Python passa por `bridge/infrastructure/BufferContract.hpp` antes de chegar ao motor (`tests/test_buffer_contract.py`); erro do motor vira `ValueError` sem `try/catch` no binding (política em `bridge/infrastructure/README.md`).
- Binding novo aparece em `bridge/boundary/contracts/aladyn_engine_native.pyi`.
- Sem cálculo: a máscara da ponta redonda, que era calculada aqui, passou para o motor em 2026-09-25 (`boundary::renderRoundTipMask`, `tests/test_stroke_preview_native.py`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
- `bridge/infrastructure`
- `engine/boundary/public-api`
<!-- /arccc:deps -->
