# Arquitetura Ultra-Atômica (ARCcC) - Lumenia Painting Engine 2.0

Este documento define e descreve a arquitetura **100% Ultra-Atômica** implementada no Lumenia. A filosofia de design baseia-se no padrão **ARCcC (Atomic Recursive Componentization by Contract)** aplicado recursivamente tanto no Rust quanto no Python.

Cada componente funciona como uma "caixa preta" isolada e independente, comunicando-se apenas através de contratos formais de entrada/saída (sinais/slots no Python e FFI no Rust) e estruturas de dados primitivas.

---

## 📂 Árvore de Diretórios Física Completa

Abaixo está o mapeamento detalhado da estrutura do workspace:

### 🦀 1. Motor Gráfico e Ponte de Vinculação em Rust

O motor nativo está dividido em dois crates independentes sob um mesmo Cargo workspace:

*   **`engine/` (Core da Engine)**:
    *   `src/boundary/`: Interfaces públicas do motor gráfico, contendo o `Renderer` nativo principal.
    *   `src/core/`: Toda a lógica de gráficos WGPU, shaders WGSL, matemática de pincel (`spacing.rs`, `interpolator.rs`, `stabilizer.rs`, `pressure_curve.rs`), gerenciamento de ping-pong buffers (`texture_layer.rs`, `scratch_layer.rs`) e composição final do canvas.
    *   `src/infrastructure/`: Configurações de janela crua (`window.rs`) mapeando o HWND do Windows para a WGPU Surface.
*   **`bridge/` (FFI com PyO3)**:
    *   `src/boundary/`: Declaração de structs e comandos de FFI expostos ao Python (ex: `DrawCommand`, `StartStrokeCommand`).
    *   `src/core/`: Contém os bindings do `PyRenderer` e a **Worker Thread** nativa do `EngineDispatcher`.
    *   `src/lib.rs`: Registro do módulo pymodule do PyO3 (`engine_core`).

---

### 🐍 2. Interface de Usuário em Python (`ui/`)

Toda a interface em PySide6 também segue a taxonomia ARCcC:

*   **`ui/boundary/`**:
    *   `orchestrator/main_window.py`: MainWindow central que atua como orquestradora única do estado da aplicação, capturando sinais do frontend e disparando comandos na bridge.
*   **`ui/core/`**:
    *   `widgets/`: Componentes atômicos puros e isolados (ex: `CanvasWidget` para renderizar o WGPU, `ToggleSwitch` animado customizado).
    *   `screens/plugins/dialog.py`: A tela de diálogo `PluginsWindow` filtrável.
    *   `components/`: Painéis estruturais que formam a MainWindow (ex: `BrushDock` com roda de cores, `MenuBar` superior, `ToolSidebar`, `NavigatorPanel`).
    *   `theme/` e `icons.py`: Sistema de estilos dinâmicos (QSS) e gerador de ícones SVG.
*   **`ui/infrastructure/`**:
    *   `bridge_client/client.py`: Wrapper local `BridgeClient` que inicializa o `PyRenderer` em Rust.
    *   `bridge_client/dispatcher.py`: O `EngineDispatcher` em Python que intercepta e formata eventos de desenho, passando-os pelos plugins dinâmicos antes de enviá-los ao Worker Thread do Rust.
*   **`ui/utils/`**:
    *   Utilitários de conversão e cálculo puro.

---

## ⚡ 3. Mecanismo de Concorrência & Desempenho (FFI)

Para garantir pintura fluida a 60 FPS sem engasgos causados pelo GIL (Global Interpreter Lock) do Python, a comunicação é assíncrona:

1.  **Fila de Comandos (Channels)**: Quando o canvas detecta entrada física (mouse/stylus), ele envia o evento para o `EngineDispatcher`. O dispatcher repassa os comandos para a ponte nativa em Rust.
2.  **GIL-Free Worker Thread**: Em Rust, o dispatcher recebe a chamada FFI, libera o GIL (`py.allow_threads`) e joga a struct do comando em um canal assíncrono. Uma thread de processamento (Worker Thread) em Rust consome o canal em paralelo e executa a renderização física na GPU.
3.  **Thread-Safety (Mutex Compartilhado)**: A instância principal da GPU em Rust é protegida com exclusão mútua global:
    ```rust
    static GLOBAL_RENDERER: OnceLock<Mutex<Option<Renderer>>> = OnceLock::new();
    ```
    Isso assegura que o Qt (Main Thread do Python) possa renderizar o viewport síncronamente via `render(...)` enquanto a thread secundária de desenho grava pixels no canvas sem causar condições de corrida (Race Conditions).

---

## 🔌 4. Arquitetura de Plugins Avançada

O Lumenia estende seu core por meio de plugins dinâmicos baseados nas seguintes diretrizes de arquitetura limpa:

*   **Injeção de Dependências (`PluginContext`)**: Plugins não possuem referências ou imports de módulos de infraestrutura. Toda e qualquer interação com o sistema é mediada pelo objeto `PluginContext` injetado na ativação.
*   **Resolução de Dependências Topológica (DFS)**: O `PluginManager` analisa as dependências declaradas e as ordena topologicamente usando busca em profundidade com detecção de ciclos.
*   **Plugins Estruturais (de Sistema)**: Plugins marcados como `SYSTEM` têm ativação prioritária, seu controle de desativação na UI é bloqueado, e falhas de inicialização causam o encerramento seguro (fail-fast) da aplicação no boot.
