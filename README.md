# Lumenia - Digital Painting Application (WGPU + PySide6)

O **Lumenia** é um aplicativo desktop de pintura digital de altíssima performance. Ele combina o poder gráfico nativo acelerado por GPU em **Rust (WGPU)** para processamento físico de dabs e renderização, com uma interface rica e altamente responsiva escrita em **Python (PySide6)**.

Tanto o motor gráfico quanto a interface visual seguem o padrão de design **ARCcC (Atomic Recursive Componentization by Contract)**, dividindo-se de forma desacoplada e simétrica em subpastas com responsabilidades estritas.

---

## 📂 Estrutura Física do Projeto

O repositório é composto por uma árvore ultra-atômica e organizada de diretórios:

```text
Lumenia/
├── engine/             # CRATE RUST: O motor gráfico core de pintura
│   ├── Cargo.toml
│   └── src/
│       ├── boundary/       # Interfaces e contratos públicos (Renderer, etc.)
│       ├── core/           # Regras de desenho (brush math, spacing, interpolator, shaders)
│       └── infrastructure/ # Drivers e setups gráficos (WGPU Surface, window mapper)
│
├── bridge/             # CRATE RUST: A camada FFI (PyO3)
│   ├── Cargo.toml
│   └── src/
│       ├── boundary/       # Contratos de comandos FFI expostos ao Python
│       ├── core/           # bindings do PyRenderer e Worker Thread do dispatcher
│       └── lib.rs          # Declaração do pymodule PyO3 (engine_core)
│
├── ui/                 # FOLDER PYTHON: Interface gráfica PySide6
│   ├── main.py             # Ponto de entrada (dispara o loop QApplication)
│   ├── boundary/           # MainWindow e orquestração de layouts
│   ├── core/               # Widgets de desenho (CanvasWidget), telas e componentes visuais
│   ├── infrastructure/     # Clientes do sistema (BridgeClient, EngineDispatcher)
│   └── utils/              # Temas, estilos QSS, geradores de ícones dinâmicos
│
└── plugins/            # FOLDER PYTHON: Extensões dinâmicas do usuário
    ├── rainbow_dynamics.py # Plugin exemplo de dinâmica com modulação senoidal e pressão
    └── plugins_config.json # Estado persistido de ativação dos plugins
```

---

## ⚙️ Características do Motor de Pintura

*   **Ponte de Eventos Assíncrona (Dispatcher)**: Eventos de traçado (`StartStroke`, `Draw`, `EndStroke`) são convertidos para structs nativas Rust com segurança de tipo FFI e despachados para processamento em uma thread secundária (Worker Thread), liberando o GIL do Python (`py.allow_threads`).
*   **Estabilização & Curva de Pressão**: Suavização de tremor por Média Móvel Exponencial (EMA) e ajuste matemático de sensibilidade de pressão da caneta física.
*   **Rotação 2D do Viewport**: Renderização da tela rotacionada usando shaders WGSL nativos e mapeamento inverso das coordenadas físicas no `InputAdapter` do Rust.
*   **Premultiplied Alpha Over**: Composição física de dabs na GPU sem halos cinzas nas bordas (blending pré-multiplicado).

---

## 🔌 Sistema de Plugins

O sistema de plugins do Lumenia suporta o carregamento de extensões dinâmicas em tempo de execução:
*   **Injeção de Contexto (`PluginContext`)**: Plugins recebem serviços e logs de forma injetada, sem importar variáveis globais.
*   **Ordenação Topológica**: Resolvedor DFS com detecção de dependências cíclicas.
*   **Plugins de Sistema**: Suporte a plugins vitais travados na UI (não podem ser desligados) e que abortam a aplicação de forma segura caso falhem (fail-fast).

---

## 🚀 Como Compilar e Executar

### Pré-requisitos
- Rust (Cargo)
- Python 3.8+ com `PySide6` e `maturin` instalados

### 1. Compilar o Core Gráfico (Rust -> Python PYD)
Com o terminal no diretório raiz do projeto, execute:
```powershell
# Configura compatibilidade de ABI e compila a bridge
$env:PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
cargo build

# Copie o binário compilado (.dll) para o frontend Python como (.pyd)
Copy-Item -Path "target/debug/engine_core.dll" -Destination "ui/engine_core.pyd" -Force
```

### 2. Executar a Aplicação
```powershell
python ui/main.py
```
