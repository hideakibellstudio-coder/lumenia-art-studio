# 🏛️ CONSTITUIÇÃO ARQUITETURAL: LUMENIA ART STUDIO & ALADYN ENGINE

Este documento é a **Regra Soberana Always-On** do projeto. Qualquer agente ou desenvolvedor que opere neste repositório **DEVE** seguir integralmente estas diretrizes e princípios arquiteturais (**ARCcC** — *Atomic Recursive Componentization by Contract*).

---

## 🗺️ 1. Mapa Mental & Hierarquia de Camadas

O ecossistema é estritamente dividido em 4 camadas com responsabilidades isoladas:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. CAMADA DE UI & PLUGINS (`plugins/`, `ui/boundary/`, `ui/core/screens/`)   │
│    • PySide6 (Qt) puramente declarativo e reativo.                          │
│    • NUNCA importa `aladyn_engine_native`.                                   │
│    • NUNCA acessa ponteiros ou atributos privados `_facade` / `_native`.    │
│    • Consome o motor UNICAMENTE via `EngineRegistry.instance().get_backend()`│
├─────────────────────────────────────────────────────────────────────────────┤
│ 2. CAMADA DE BASE CENTRAL (`ui/core/`)                                      │
│    • Átomos e Moléculas de UI: `ui/core/widgets/` (Sliders, Cards, Secoes). │
│    • Single Source of Truth do Documento: `ui/core/document/` (LayerManager)│
│    • Dinamismo de Temas: `ui/core/theme/manager.py` (ThemeManager).         │
│    • Contrato Universal: `ui/core/engine/backend.py` (`EngineBackend`).      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 3. CAMADA DE PONTE / BACKEND (`ui/engine_backends/`)                         │
│    • `ui/engine_backends/aladyn.py` (`AladynBackend`).                      │
│    • A ÚNICA camada autorizada a importar `aladyn_engine_native`.           │
│    • Converte chamadas canônicas em chamadas nativas de `PaintEngineFacade`. │
│    • Gerencia MDI multi-documento isolando instâncias nativas via Mixins.   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 4. CAMADA DE MOTOR NATIVO (`engine/`, `aladyn_engine_native`)               │
│    • C++20 puro, de altíssimo desempenho, livre de Qt e de Python.          │
│    • Tiles esparsos 64x64, SIMD AVX2/SSE2, interpolação Catmull-Rom/Clark.  │
│    • Mini-motores físicos (Pencil, Watercolor, Oil, Inker, Marker, Smudge). │
│    • Exposto ao Python via PyBind11 em `PaintEngineFacade`.                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔒 2. As 6 Leis Invioláveis do Projeto (ARCcC)

1. **Zero Cross-Plugin Imports**:
   - Um plugin em `plugins/<tipo>/<plugin_A>/` **NUNCA** importa nada de `plugins/<tipo>/<plugin_B>/`.
   - Se um componente é necessário em múltiplos plugins, ele **DEVE** residir em `ui/core/widgets/` ou `ui/core/`.
2. **Zero Binário C++ em Camadas Superiores**:
   - É expressamente proibido `import aladyn_engine_native` fora de `ui/engine_backends/`.
3. **Zero Acesso a Atributos Privados de Motor (`_facade`, `_native`)**:
   - Toda comunicação entre UI e Motor ocorre exclusivamente pelos métodos públicos canônicos definidos em `EngineBackend`.
4. **Fluxo de 3 Etapas para Qualquer Nova Funcionalidade de Motor**:
   - **Passo 1**: Declarar o método canônico em `ui/core/engine/backend.py` com retorno seguro padrão.
   - **Passo 2**: Implementar o método em `ui/engine_backends/aladyn.py` despachando para `self._facade` ou `self._native`.
   - **Passo 3**: Consumir na UI chamando `backend.metodo(...)` obtido via `EngineRegistry.instance().get_backend()`.
5. **Fonte Única de Verdade (Single Source of Truth)**:
   - Os dados do documento (camadas, visibilidade, opacidade, transformações, papel) residem em `Document` / `LocalLayerManager` (`ui/core/document/`).
   - Painéis de UI (`LayersPanel`, `NavigatorWidget`, etc.) são apenas **Views** sincronizadas via sinais Qt.
6. **Zero Hardcode de Cores em Folhas de Estilo**:
   - Nunca use `#hex` fixo em `setStyleSheet` dentro de plugins.
   - Sempre utilize `ThemeManager.instance().get_color(...)` ou seletores de classe QSS (`setObjectName`).

---

## 🎨 3. Convenções de Design System & UI

- **Sliders**: Utilize `CompactSlider` (`ui/core/widgets/compact_slider.py`) para controles de valor com passos e botões de acessibilidade.
- **Seções Expansíveis**: Utilize `CollapsibleSection` (`ui/core/widgets/collapsible_section.py`) para blocos de parâmetros agrupados.
- **Janelas Flutuantes**: Nunca faça loops `while curr.parentWidget():`. Utilize `anchor_widget.window()` para localizar o topo determinístico.
- **Ícones**: Carregue ícones sempre via `ui.core.icons.get_icon(name)`.

---

## 🧪 4. Protocolo de Validação Obrigatória

Ao concluir qualquer alteração de código, **SEMPRE** execute a suíte executiva:
```bash
python tests/run_all_tests.py
```
O teste `test_arccc_architecture_invariants.py` valida a Árvore Sintática (AST) e bloqueará a entrega caso haja qualquer vazamento de abstração ou import proibido.
