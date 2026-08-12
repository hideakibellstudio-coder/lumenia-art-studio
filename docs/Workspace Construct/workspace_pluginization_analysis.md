# Análise de Viabilidade: Pluginização do Workspace no Lumenia V2

Esta análise avalia a viabilidade, riscos e a estratégia técnica para desacoplar a interface gráfica (Workspace) da classe principal `MainWindow` no Lumenia V2 (Surface WGPU) e transformá-la em um **Plugin de Sistema (Workspace Core System Plugin)**.

---

## 1. O Diagnóstico de Acoplamento Atual (Lumenia V2)

Na versão atual V2, a classe `MainWindow` ([`main_window.py`](file:///z:/Develop%20Omega/Repositorio%20MAIN/Lumenia%20%28Suface%20WGPU%29/Lumenia/ui/boundary/orchestrator/main_window.py)) acumula múltiplas responsabilidades de infraestrutura, layout e controle de pintura:

1.  **Criação de Layout Físico**: Instancia diretamente a `MenuBar`, `ToolSidebar`, `StatusBar` e as docas `BrushDock` e `PropertiesDock`.
2.  **Ciclo de Vida do Canvas WGPU**: Instancia o `CanvasWidget`, controla seu redimensionamento e centralização e inicia a engine do Rust.
3.  **Encaminhamento de Sinais (Wiring)**: Conecta manualmente os sinais da Roda de Cores e dos Sliders de Pincel (`BrushDock`) às funções de pintura do Canvas.
4.  **Sincronização de Câmera e Documentos**: Sincroniza a barra de status e o navegador com as atualizações de projeção da viewport.

### O Problema do Acoplamento Rígido:
Se quisermos introduzir elementos flexíveis de interface (como as gavetas auto-hide com reparentamento dinâmico ou a barra de ferramentas flutuante), precisaremos modificar diretamente a `MainWindow`. Isso fere os princípios SOLID (Open/Closed Principle) e torna a interface monolítica, impedindo que outros plugins de usuário adicionem abas, ferramentas ou painéis dinamicamente.

---

## 2. A Arquitetura Proposta: Desacoplamento via Plugin de Sistema

Para modularizar o Lumenia V2, seguiremos a arquitetura proposta na V1, mas adaptada para o padrão de serviços simplificado (`ServiceRegistry` e `PluginContext`) da V2.

### Visão Geral da Arquitetura:
```
MainWindow (Casca Vazia)
   └── PluginManager (Bootstrap)
         └── WorkspaceCore (Plugin de Sistema - Carregado Primeiro)
               ├── WorkspaceContainer (QWidget Central)
               │     ├── CanvasWidget (Surface WGPU)
               │     ├── Docks (AdvancedDockSystem Esquerda/Direita)
               │     └── Floating UI (Shells Frameless)
               └── WorkspaceManager (Exposto via ServiceRegistry)
```

---

## 3. O Design de Serviços no Lumenia V2

Na versão V2, não usaremos o EventBus legado da V1. Em vez disso, usaremos a classe global `ServiceRegistry` ([`registry.py`](file:///z:/Develop%20Omega/Repositorio%20MAIN/Lumenia%20%28Suface%20WGPU%29/Lumenia/ui/core/plugins/registry.py)) para expor as interfaces do Workspace de forma limpa.

### 1. Definindo o Contrato (`WorkspaceService`):
```python
from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget

class WorkspaceService(ABC):
    @abstractmethod
    def add_panel(self, panel_id: str, title: str, widget: QWidget, area: str = "right", icon_path: str = None):
        """Permite que outros plugins adicionem painéis às docas dinâmicas."""
        pass

    @abstractmethod
    def remove_panel(self, panel_id: str):
        """Remove um painel específico."""
        pass
```

### 2. Implementação do Plugin de Sistema (`WorkspaceCore`):
```python
from ui.core.plugins.base import BasePlugin
from ui.core.plugins.metadata import PluginMetadata, PluginType
from ui.core.plugins.registry import ServiceRegistry

class WorkspaceCore(BasePlugin, WorkspaceService):
    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            id="workspace_core",
            name="Workspace Core System",
            version="2.0.0",
            author="Lumenia Team",
            description="Cockpit central com docas, canvas WGPU e gerenciador de painéis.",
            plugin_type=PluginType.SYSTEM,
            dependencies=[]
        )

    def is_system_plugin(self) -> bool:
        return True # Interrompe o boot se falhar

    def get_priority(self) -> int:
        return 100 # Carrega antes de qualquer outro plugin

    def activate(self):
        # 1. Registra o serviço para outros plugins usarem
        ServiceRegistry.instance().register_service(WorkspaceService, self)
        
        # 2. Cria o container central e injeta na MainWindow
        # (MainWindow pode ser exposta no PluginContext ou recuperada via QApplication)
        
    def deactivate(self):
        ServiceRegistry.instance().unregister_service(WorkspaceService, self)
```

---

## 4. Plano de Transição (Passo a Passo)

A pluginização do workspace deve anteceder a implementação das gavetas auto-hide e elementos flutuantes para garantir que a base seja sólida. O roadmap recomendado é:

### Passo 1: Injeção da MainWindow no PluginContext
*   Atualmente, o `PluginContext` só expõe o `bridge_client` e o `dispatcher`. 
*   Devemos modificar o `PluginManager` para injetar a referência da `MainWindow` no `PluginContext`. Isso permitirá que plugins interajam de forma segura com o ciclo de vida da janela do sistema.

### Passo 2: Extração do Canvas e Docks da MainWindow
*   Criar o widget `WorkspaceContainer` em um sub-pacote (ex: `ui/core/components/workspace/`).
*   Mover a criação do `CanvasWidget`, `TabbedViewportContainer` e das Docks de dentro da `MainWindow` para o `WorkspaceContainer`.
*   O `WorkspaceContainer` será responsável por expor as funções de sincronização interna e reparentamento.

### Passo 3: Criação do Plugin de Sistema `WorkspaceCore`
*   Criar o plugin `WorkspaceCore` na pasta `plugins/` ou integrá-lo como um módulo de sistema nativo no importador.
*   No `activate()` do plugin, ele instancia o `WorkspaceContainer`, chama `main_window.setCentralWidget(container)` e registra a si mesmo no `ServiceRegistry`.

### Passo 4: Migração das Docas Atuais para a API do Workspace
*   Em vez de acoplar as docks, a própria inicialização padrão do sistema chamará `WorkspaceService.add_panel(...)` para injetar a árvore de camadas, o navegador e a roda de cores nas posições corretas.

---

## 5. Análise de Riscos e Viabilidade

| Risco | Impacto | Mitigação |
| :--- | :--- | :--- |
| **Ordem de Inicialização (Boot Race)** | Alto | Garantir que o `WorkspaceCore` tenha prioridade máxima de carregamento (`get_priority() -> 100`). Ele deve criar o canvas antes que outros plugins de ferramentas tentem usá-lo. |
| **Perda de Referência de Documentos** | Médio | Centralizar o `DocumentManager` como um singleton unificado fora da MainWindow. A comunicação de troca de documentos ativa deve ser ouvida diretamente pelo `WorkspaceContainer`. |
| **Redirecionamento de Input da Engine** | Baixo | Como o `BridgeClient` e o `EngineDispatcher` já são Singletons independentes, a comunicação do canvas com a Rust engine não é afetada por quem hospeda o canvas na tela. |

---

## 6. Conclusão de Viabilidade

**A pluginização do workspace é altamente viável e altamente recomendável.**

Ela reduzirá a `MainWindow` a um shell limpo de inicialização e criará um ecossistema modular no Lumenia V2. Com essa arquitetura orientada a serviços e dependências declaradas:
1.  Qualquer desenvolvedor poderá substituir ou modificar o visual do workspace sem tocar na janela principal.
2.  Facilitará drasticamente a injeção do reparentamento dinâmico e das barras flutuantes, mantendo a responsabilidade isolada de cada módulo.
3.  Evita regressões na lógica de pintura do Rust/WGPU.
