# 🏛️ MANIFESTO TÉCNICO DAS BARRAS & PAINÉIS — LUMENIA BRUSH ENGINE 2.0

> Documento de arquitetura visual e catálogo completo de componentes de interface (`Bars`, `Sidebars`, `Toolbars`, `Docks` e `Containers`) do software **Lumenia**.

---

## 📋 Visão Geral da Arquitetura Visual

O ecossistema **Lumenia** adota uma arquitetura modular inspirada nos softwares profissionais de pintura digital (Procreate, Photoshop, Clip Studio Paint e Krita). A interface é dividida em quatro camadas principais de suporte visual:

1. **Janela Shell Global (`QMainWindow`)**: Responsável pelas barras globais de topo e rodapé.
2. **Sistema Dinâmico de Docks e Gavetas (`AdvancedDockSystem`)**: Responsável pelas barras de ícones laterais e gavetas expansíveis.
3. **Gerenciador de Viewport e Ferramentas Flutuantes (`TabbedViewportContainer` e `FloatingToolbar`)**: Responsável pelas abas de projeto e ferramentas sob o canvas.
4. **Barras Internas de Painéis Plugin (`LayersHeader`, `LayersSecondaryBar`, `LayersPrimaryBox`)**: Sub-barras especializadas de controle operacional.

---

## 🗂️ Catálogo Completo dos Componentes

### 1. Janela Shell Global (MainWindow Shell)

#### 🟢 `MenuBar`
- **Caminho do Código**: [`ui/core/components/menu_bar/menu_bar.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/components/menu_bar/menu_bar.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QMenuBar`
- **Nome Técnico**: `MenuBar` (Barra de Menus Principal)
- **Funcionalidades**:
  - Menu `Arquivo`: Criar Novo Documento, Salvar, Exportar Imagem, Fechar.
  - Menu `Editar`: Desfazer/Refazer, Limpar Canvas.
  - Menu `Exibir`: Ajuste de Zoom, Reset de Rotação/Visão, Curvas LUT.
  - Menu `Janela`: Controle de visibilidade de gavetas, recolhimento global e atracamento.
  - Menu `Configurações`: Gestor de Temas (Dark/Light), Diálogo de Plugins e Ajustes de Docks.

#### 🟢 `ToolSidebar`
- **Caminho do Código**: [`ui/core/components/tool_sidebar/sidebar.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/components/tool_sidebar/sidebar.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QToolBar`
- **Nome Técnico**: `ToolSidebar` (Barra de Ferramentas Principal Superior)
- **Funcionalidades**:
  - Seleção direta entre ferramenta **Pincel** (`action_brush`) e **Borracha** (`action_eraser`).
  - Botões de ação rápida de Câmera: Zoom In, Zoom Out, Resetar Câmera e Limpar Canvas.

#### 🟢 `StatusBar`
- **Caminho do Código**: [`ui/core/components/status_bar/bar.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/ui/core/components/status_bar/bar.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QStatusBar`
- **Nome Técnico**: `StatusBar` (Barra de Status do Rodapé)
- **Funcionalidades**:
  - Exibição de mensagens de estado do sistema em tempo real.
  - Nome do documento ativo.
  - Nível de Zoom interativo do viewport.
  - Métrica de performance (FPS do motor C++ e taxa de dabs do traço).

---

### 2. Sistema Dinâmico de Docks e Gavetas (Advanced Dock System)

#### 🔵 `AdvancedDockSystem`
- **Caminho do Código**: [`plugins/system/workspace_core/workspace/dock_system.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/system/workspace_core/workspace/dock_system.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `AdvancedDockSystem` (Gerenciador Central de Docks)
- **Funcionalidades**:
  - Gerencia o layout dinâmico das barras de ícones laterais e gavetas flutuantes/acopladas.
  - Suporta atracamento à esquerda ou direita (`LeftDock`, `RightDock`).
  - Suporta modo "Gaveta" (*Drawer*) com recolhimento automático ao clicar fora.

#### 🔵 `SidebarWidget`
- **Caminho do Código**: [`plugins/system/workspace_core/workspace/dock_system.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/system/workspace_core/workspace/dock_system.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `SidebarWidget` (Barra de Ícones Lateral Verticais)
- **Funcionalidades**:
  - Barra vertical fina contendo os ícones dos painéis cadastrados (Camadas, Cor, Pincéis, Navegador, Telemetria, Propriedades).
  - Permite abrir/fechar a gaveta do painel com um clique no ícone correspondente.

#### 🔵 `DrawerHeader`
- **Caminho do Código**: [`plugins/system/workspace_core/workspace/dock_system.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/system/workspace_core/workspace/dock_system.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `DrawerHeader` (Barra do Cabeçalho da Gaveta de Painéis)
- **Funcionalidades**:
  - Exibe o título do painel ativo.
  - Botão de Fixar/Pinagem (converte a gaveta temporária em painel fixo/docked na tela).
  - Botão de Fechar Gaveta (`X`).

---

### 3. Ferramentas Flutuantes e Abas do Viewport

#### 🟡 `FloatingToolbar`
- **Caminho do Código**: [`plugins/system/workspace_core/workspace/floating_toolbar.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/system/workspace_core/workspace/floating_toolbar.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QDialog` / `QWidget` Flutuante
- **Nome Técnico**: `FloatingToolbar` (Barra de Ferramentas Flutuante)
- **Funcionalidades**:
  - Barra flutuante sobreposta ao canvas que pode ser arrastada e posicionada livremente.
  - Permite configuração personalizada de atalhos de ferramentas essenciais pelo usuário.

#### 🟡 `TabbedViewportContainer`
- **Caminho do Código**: [`plugins/system/workspace_core/workspace/viewport_container.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/system/workspace_core/workspace/viewport_container.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `TabbedViewportContainer` (Barra de Abas de Documentos)
- **Funcionalidades**:
  - Barra de navegação multi-documento estilo navegador web.
  - Botão de fechar aba (`TabCloseButton`) com confirmação de alterações não salvas.
  - Troca instantânea de projeto ativo sem perder o estado de câmera ou histórico.

---

### 4. Sub-Barras Internas do Painel de Camadas (`LayersPanel`)

#### 🟣 `LayersHeader`
- **Caminho do Código**: [`plugins/ui/layers_plugin/header.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN%20+%20UI%20LUMENIA/Lumenia/plugins/ui/layers_plugin/header.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `LayersHeader` (Barra do Cabeçalho do Painel de Camadas)
- **Funcionalidades**:
  - Seletor de Modo de Mesclagem (`QComboBox` com Normal, Multiply, Screen, Overlay, Erase, etc.).
  - Slider Customizado de Opacidade (`LayersOpacitySliderWidget`) com arrasto interativo de 0 a 100%.

#### 🟣 `LayersSecondaryBar`
- **Caminho do Código**: [`plugins/ui/layers_plugin/grid.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN + UI LUMENIA/Lumenia/plugins/ui/layers_plugin/grid.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `LayersSecondaryBar` (Barra Horizontal Superior de Ações de Camada)
- **Funcionalidades**:
  - ➕ `Nova Camada`: Adiciona uma nova camada de desenho.
  - 🗑️ `Deletar Camada`: Remove a camada ativa.
  - 🔼 `Mover Cima`: Eleva a posição da camada.
  - 🔽 `Mover Baixo`: Abaixa a posição da camada.
  - ⤓ `Mesclar para Baixo`: Funde os pixels da camada atual com a inferior.
  - 🎛️ `Adicionar Filtro`: Cria uma camada de ajuste/filtro.

#### 🟣 `LayersPrimaryBox`
- **Caminho do Código**: [`plugins/ui/layers_plugin/grid.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN + UI LUMENIA/Lumenia/plugins/ui/layers_plugin/grid.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QWidget`
- **Nome Técnico**: `LayersPrimaryBox` (Barra Vertical Lateral de Ações e Bloqueios)
- **Funcionalidades**:
  - 📂 `Novo Grupo (G)`: Agrupa camadas selecionadas.
  - *-- Divisória de Seção --*
  - 📎 `Clipping Mask`: Ativa/desativa máscara de recorte na camada base.
  - 🟧 `Alpha Lock`: Tranca o canal alpha para pintar apenas onde já existe pigmento.
  - 🔒 `Bloquear Camada`: Trava totalmente a camada contra edições acidentais.

---

### 5. Docks & Painéis de Motores de Pintura

#### 🟠 `BrushDock` & `PropertiesDock`
- **Caminho do Código**: [`plugins/ui/properties_plugin/dock.py`](file:///z:/DESENVOLVIMENTO/+ESTUDO%20ATUAL/ALADYN + UI LUMENIA/Lumenia/plugins/ui/properties_plugin/dock.py)
- **Tipo / Herança**: `PySide6.QtWidgets.QDockWidget`
- **Nome Técnico**: `BrushDock` / `PropertiesDock` (Painéis Atracáveis Nativos)
- **Funcionalidades**:
  - Atracamento padrão do Qt em qualquer borda da janela.
  - Exibição de presets dos 8 mini-motores nativos C++ (Pencil, Inker, Marker, Oil, Watercolor, Eraser, Blur, Smudge).
  - Ajuste de parâmetros físicos (Solvent Wetness, Impasto Depth, Granulation, Bristle Grooves, Blur Radius).

---

## 📊 Tabela Resumo do Manifesto

| Nome Técnico no Código | Tipo de Componente | Localização no Arquivo | Função Principal |
| :--- | :--- | :--- | :--- |
| **`MenuBar`** | `QMenuBar` | `ui/core/components/menu_bar/` | Menu superior global de comandos do aplicativo |
| **`ToolSidebar`** | `QToolBar` | `ui/core/components/tool_sidebar/` | Barra superior rápida de ferramentas e visão |
| **`StatusBar`** | `QStatusBar` | `ui/core/components/status_bar/` | Rodapé com coordenadas, zoom, FPS e status |
| **`AdvancedDockSystem`**| `QWidget` | `plugins/system/workspace_core/` | Gerenciador de sidebars e gavetas retráteis |
| **`SidebarWidget`** | `QWidget` | `plugins/system/workspace_core/` | Barra vertical fina de ícones dos painéis |
| **`DrawerHeader`** | `QWidget` | `plugins/system/workspace_core/` | Cabeçalho da gaveta com botão de fixar e fechar |
| **`FloatingToolbar`** | `QDialog` | `plugins/system/workspace_core/` | Toolbar flutuante sob o canvas totalmente móvel |
| **`TabbedViewportContainer`**|`QWidget` | `plugins/system/workspace_core/` | Barra de abas de múltiplos documentos abertos |
| **`LayersHeader`** | `QWidget` | `plugins/ui/layers_plugin/` | Controle de blend mode e slider de opacidade |
| **`LayersSecondaryBar`**| `QWidget` | `plugins/ui/layers_plugin/` | Barra superior de ações (+, lixeira, reordenar) |
| **`LayersPrimaryBox`** | `QWidget` | `plugins/ui/layers_plugin/` | Barra lateral vertical de atalhos (Group, Clip, Alpha, Lock) |
| **`BrushDock`** / **`PropertiesDock`**| `QDockWidget` | `plugins/ui/properties_plugin/` | Docks nativos de presets e física dos mini-motores |

---

> **Conclusão**: A estrutura de barras do Lumenia 2.0 é totalmente modular, desacoplada via sistema de plugins e orquestrada entre componentes nativos do Qt e controles customizados em PySide6/C++.
