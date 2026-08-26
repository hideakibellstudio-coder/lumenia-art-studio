# 🔌 GUIA TÉCNICO DE MÓDULOS & PLUGINS — LUMENIA

Este documento detalha o sistema de plugins do **Lumenia**, a arquitetura de desacoplamento, os módulos integrados e o passo a passo para criar novas ferramentas e extensões.

---

## 1. Módulos & Plugins Nativos do Sistema

A pasta `plugins/` é dividida em categorias estruturadas:

```text
plugins/
├── system/                  # Plugins de infraestrutura vitais
│   └── workspace_core/      # Gerenciamento de janelas, docas e menus centrais
│
├── ui/                      # Plugins visuais de controle e ferramentas
│   ├── brush_plugin/        # Painel de Pincéis (Tamanho, Opacidade, Dureza, Estabilizador)
│   ├── color_plugin/        # Seletor de Cores, Wheel HUD, Sliders RGB/HSV e Perfis P3/CMYK
│   ├── layers_plugin/       # Painel de Camadas, Grupos, Opacidade, Duplicação e Merge Down
│   ├── navigator_plugin/    # Painel de Navegação em Miniatura, Zoom e Rotação rápida do Canvas
│   └── telemetry_plugin/    # Monitoramento de FPS, uso de memória e diagnóstico de desempenho
│
├── rainbow_dynamics.py      # Plugin de exemplo de dinâmica de pincelada procedural
└── plugins_config.json      # Estado persistido de ativação/desativação dos plugins
```

---

## 2. A API de Plugins (`PluginBase` & `PluginContext`)

Todos os plugins herdam da classe abstrata `PluginBase` (em `ui/core/plugins/base.py`) e operam através de injeção de dependência via `PluginContext`.

### 📑 Estrutura Básica de um Plugin

```python
from ui.core.plugins.base import PluginBase, PluginMetadata, PluginCategory, PluginContext

class MeuPluginCustomizado(PluginBase):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            id="com.lumenia.meu_plugin",
            name="Meu Plugin Incrível",
            version="1.0.0",
            description="Adiciona novos recursos visuais ao canvas.",
            author="Equipe Lumenia",
            category=PluginCategory.TOOL,
            dependencies=[]  # Ex: ["com.lumenia.workspace_core"]
        )

    def activate(self, context: PluginContext) -> bool:
        """Executado quando o plugin é ativado no boot ou pelo menu."""
        self.context = context
        self.context.logger.info(f"Plugin {self.metadata.name} ativado!")
        
        # Registra um botão no menu
        self.context.register_menu_action(
            menu="Ferramentas",
            action_name="Executar Ação",
            callback=self.executar_acao
        )
        return True

    def deactivate(self) -> bool:
        """Executado na desativação ou fechamento do software."""
        self.context.logger.info("Plugin desativado.")
        return True

    def executar_acao(self):
        canvas = self.context.get_service("canvas")
        if canvas:
            self.context.logger.info("Acessando o canvas com segurança.")
```

---

## 3. Hooks de Interceptação de Pinceladas e Canvas

Plugins podem interceptar eventos físicos de desenho e aplicar dinâmicas procedurais:

| Método / Hook | Parâmetros | Descrição |
| :--- | :--- | :--- |
| `on_stroke_start(x, y, pressure)` | Coordenadas e pressão inicial | Disparado no primeiro contato da caneta ou clique do mouse. |
| `on_stroke_point(x, y, pressure)` | Ponto intermediário interpolado | Permite modular a cor, o tamanho ou a dinâmica antes de desenhar o dab. |
| `on_stroke_end()` | Nenhum | Disparado ao levantar a caneta ou soltar o botão do mouse. |
| `render_overlay(painter)` | Instância `QPainter` | Permite desenhar elementos flutuantes sobre o canvas (ex: réguas, miras, grids). |

---

## 4. Como Criar um Novo Plugin Passo a Passo

### Exemplo: Criando um Plugin de Grade Isométrica (`IsometricGridPlugin`)

1. Crie uma pasta dentro de `plugins/ui/isometric_grid/`.
2. Crie o arquivo `plugin.py` com o código:

```python
from PySide6.QtGui import QPainter, QPen, QColor
from ui.core.plugins.base import PluginBase, PluginMetadata, PluginCategory, PluginContext

class IsometricGridPlugin(PluginBase):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            id="com.lumenia.grid.isometric",
            name="Grade Isométrica",
            version="1.0.0",
            description="Renderiza guias isométricas no canvas para desenho técnico.",
            category=PluginCategory.VISUAL,
            dependencies=["com.lumenia.workspace_core"]
        )
        self.enabled = True

    def activate(self, context: PluginContext) -> bool:
        self.context = context
        context.register_overlay_renderer(self.render_grid)
        return True

    def render_grid(self, painter: QPainter, viewport_rect):
        if not self.enabled:
            return
        pen = QPen(QColor(147, 51, 234, 40), 1)
        painter.setPen(pen)
        
        # Desenha linhas inclinadas a 30 graus
        step = 40
        w, h = viewport_rect.width(), viewport_rect.height()
        for y in range(0, h * 2, step):
            painter.drawLine(0, y, w, y - int(w * 0.577))
            painter.drawLine(0, y - int(w * 0.577), w, y)
```

3. Abra o Lumenia: o plugin será detectado e carregado automaticamente pelo `PluginManager`!
