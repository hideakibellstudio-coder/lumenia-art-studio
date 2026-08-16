# Plano de Implementação — Unificação Completa do Projeto em `Lumenia/` conforme ARCcC

Unificar todas as pastas separadas (`ALADYN ENGINE/` e `Lumenia/`) dentro do repositório principal **`Lumenia/`**, reestruturando o projeto em uma arquitetura monorepo ARCcC de **3 Pilares soberanos (Seção 15.3 do ARCcC)**:

```
Lumenia/
├── ui/              # PILAR 1 — Interface PySide6 (Python)
├── bridge/          # PILAR 2 — Interoperabilidade & Bindings PyBind11 (C++)
├── engine/          # PILAR 3 — Motor Nativo C++ (Canvas Tiled, Camadas, Compositor, Motores de Pincel)
├── plugins/         # Plugins modulares do sistema
├── docs/            # Documentação e especificações ARCcC
└── setup.py         # Script de compilação C++ unificado do projeto
```

---

## User Review Required

> [!IMPORTANT]
> **Aprovação do Plano**: Toda a estrutura de código-fonte C++ do motor `ALADYN ENGINE` será movida para `Lumenia/engine/`, os bindings PyBind11 para `Lumenia/bridge/` e o script de compilação `setup.py` será unificado na raiz de `Lumenia/`. Nenhum arquivo de motor continuará isolado fora de `Lumenia/`.

---

## Proposed Changes

### 1. Migração do Motor Nativo C++ (`engine/`)

#### [NEW] [`Lumenia/engine/`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/engine)
- Copiar todo o código-fonte C++17 de `ALADYN ENGINE/engine/` para `Lumenia/engine/`:
  - `engine/boundary/public-api/PaintEngineFacade.hpp` & `.cpp`
  - `engine/core/brush/` (`BrushProfile`, `BrushTip`, `DynamicMapper`)
  - `engine/core/canvas/` (`Tile`, `TileGrid`, `SpatialCuller`, `TileUndoManager`)
  - `engine/core/document/` (`LayerNode`, `Layer`, `LayerGroup`, `FilterLayer`, `LayerStack`, `Compositor`)
  - `engine/core/engines/` (`InkerEngine`, `PencilEngine`, `MarkerEngine`, `WatercolorEngine`, `OilImpastoEngine`, `SmudgeEngine`, `EraserEngine`, `BlurEngine`)
  - `engine/core/math/` (`Point2D`, `BezierCurve`)
  - `engine/core/raster/` (`DabInterpolator`, `DabRenderer`)
  - `engine/core/stroke/` (`DynamicStabilizer`, `VelocityTracker`)
  - `engine/core/texture/` (`ProceduralTextures`, `Texture2D`)

---

### 2. Migração da Camada de Ponte (`bridge/`) & Script de Build

#### [NEW] [`Lumenia/bridge/core/bindings/engine_bindings.cpp`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/bridge/core/bindings/engine_bindings.cpp)
- Mover os bindings PyBind11 C++ para a estrutura do Pilar `bridge/` em `Lumenia/`.

#### [NEW] [`Lumenia/setup.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/setup.py)
- Criar o `setup.py` unificado na raiz de `Lumenia/` configurado para compilar os fontes C++ em `engine/` e `bridge/` diretamente para a extensão nativa `aladyn_engine_native`.

---

### 3. Ajuste de Importações e Sincronização em `Lumenia/ui/`

#### [MODIFY] [`aladyn.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/engine_backends/aladyn.py)
- Garantir que o backend carregue a extensão compilada localmente no projeto unificado.

---

## Verification Plan

### Automated Tests
1. **Compilação Nativa C++ no Projeto Unificado**:
   - Executar `python setup.py build_ext --inplace` a partir da raiz de `z:\DESENVOLVIMENTO\+ESTUDO ATUAL\ALADYN + UI LUMENIA\Lumenia`.
   - Verificar a geração do binário `.pyd` compilado sem warnings nem erros.

2. **Bateria de Testes Automatizados**:
   - Executar `python -m unittest discover tests` para garantir que o motor C++ unificado responde perfeitamente a traços, camadas, clipping masks e undo/redo.
   - Executar `python scripts/boot_smoke.py` para validar o boot limpo da aplicação unificada.

3. **Verificação de Inicialização da GUI**:
   - Executar script de smoke test para validar a renderização do `MainWindow` e a comunicação via `EngineRegistry`.
