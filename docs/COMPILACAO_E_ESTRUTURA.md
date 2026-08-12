# Documentação de Estrutura e Compilação - Lumenia

Esta documentação descreve a nova estrutura arquitetural do Lumenia baseada no padrão **ARCcC Multi-Pilar** (aninhamento físico de nível 4+) e as instruções passo a passo para compilar e executar o motor gráfico nativo.

---

## 1. Nova Estrutura do Projeto

O projeto foi reestruturado para separar fisicamente os runtimes da interface gráfica (Python) e do motor nativo (Rust + wgpu). A raiz do projeto contém apenas os manifestos de build/orquestração e os três pilares principais:

```
Lumenia/
├── ui/                              # PILAR 1: Interface Gráfica (Python / PySide6)
│   ├── boundary/                    # Orquestradores da janela e interfaces públicas
│   ├── core/                        # Widgets, componentes e temas (aninhamento 4+)
│   │   ├── components/              # MenuBar, ToolSidebar, BrushDock, Navigator, etc.
│   │   ├── screens/                 # Diálogos flutuantes (ex: ThemeDialog)
│   │   ├── theme/                   # ThemeManager e paletas JSON
│   │   └── widgets/                 # Canvas (render_widget), sliders, picker, etc.
│   ├── infrastructure/
│   │   └── bridge_client/           # BridgeClient (Ponto único de contato com Rust)
│   └── main.py                      # Arquivo de entrada da UI (python ui/main.py)
│
├── bridge/                          # PILAR 2: Camada de Interoperabilidade (Rust / PyO3)
│   ├── boundary/contracts/          # Definições de estruturas compartilhadas (ex: PointerEvent)
│   ├── core/bindings/               # Wrappers PyO3 expostos (PyRenderer, InputAdapter)
│   ├── infrastructure/error_mapping/ # Tradução de erros Rust para exceções Python
│   └── lib.rs                       # Crate root dos bindings (gera a DLL engine_core)
│
├── engine/                          # PILAR 3: Motor Nativo (Rust Puro + WGPU)
│   ├── Cargo.toml                   # Manifesto da crate engine (independente de PyO3)
│   └── src/
│       ├── boundary/public_api/     # APIs nativas expostas (Renderer, InputAdapter)
│       ├── core/                    # Lógica de renderização e input nativo (aninhamento 4+)
│       │   ├── input/               # mouse, stylus, curves, stabilizer
│       │   └── rendering/           # canvas, pipelines de desenho/composição, texturas
│       └── infrastructure/          # wgpu_adapter e mapeamento de RawWindow
│
├── Cargo.toml                       # Manifesto raiz que compila a bridge (engine_core)
└── pyproject.toml                   # Manifesto raiz do Maturin
```

### O Fluxo de Comunicação
Toda a comunicação da interface com o Rust ocorre de forma indireta através do **`BridgeClient`** (`ui/infrastructure/bridge_client/client.py`). A UI nunca importa o módulo binário diretamente nas telas. O `BridgeClient` carrega a extensão compilada `engine_core` e expõe métodos limpos em Python, garantindo desacoplamento total.

---

## 2. Instruções de Compilação do Motor

O motor nativo é compilado como uma biblioteca dinâmica (`.dll` no Windows) que o Python carrega como um módulo C extension (`.pyd`).

### Pré-requisitos
1. **Rust Toolchain**: Certifique-se de possuir o compilador Rust instalado (`rustc` e `cargo`).
2. **Python**: Python 3.8 ou superior (com PySide6 instalado).
3. **Maturin**: Opcional, para empacotamento completo. O build também pode ser feito diretamente via Cargo.

### Como Compilar

#### Passo 1: Configurar Variáveis de Ambiente (Importante)
Caso a versão do Python instalada no sistema seja mais nova que a versão do PyO3 configurada no manifesto (por exemplo, Python 3.14 com PyO3 v0.22 que suporta até 3.13), a compilação falhará por incompatibilidade padrão de versão. 

Para resolver isso, **habilite a retrocompatibilidade estável da API (ABI3)** definindo a variável de ambiente abaixo no terminal antes de rodar o build:

* **No PowerShell (Recomendado):**
  ```powershell
  $env:PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
  ```
* **No Prompt de Comando (CMD):**
  ```cmd
  set PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
  ```
* **No Linux / macOS (Terminal):**
  ```bash
  export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1
  ```

#### Passo 2: Rodar o Build do Workspace Rust
Compile os pacotes do monorepo executando o comando Cargo na raiz do projeto:

```bash
cargo build --release
```
*(Nota: O build em modo `--release` otimiza drasticamente a performance do wgpu e a taxa de quadros por segundo do desenho).*

O compilador irá gerar o arquivo binário:
`target/release/engine_core.dll`

---

## 3. Como Executar o Projeto

Após compilar o motor nativo, você precisa disponibilizar o binário para o pilar de UI.

### Passo 1: Copiar o Binário para a UI
Copie a DLL gerada renomeando a extensão para `.pyd` e coloque-a dentro do diretório `ui/`:

```powershell
Copy-Item "target/release/engine_core.dll" "ui/engine_core.pyd" -Force
```

### Passo 2: Rodar a Interface
Inicie a aplicação executando o ponto de entrada da UI com o interpretador Python do seu ambiente:

```bash
python ui/main.py
```

O aplicativo deverá abrir imediatamente, carregando a MainWindow e inicializando o canvas gráfico com aceleração por hardware (WGPU).
