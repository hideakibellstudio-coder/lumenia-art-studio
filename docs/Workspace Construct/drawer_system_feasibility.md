# Viabilidade Técnica: Gavetas Colapsáveis (Docks Auto-Hide) sobre Canvas WGPU

Esta análise responde à questão crítica: **é possível implementar gavetas laterais colapsáveis com comportamento auto-hide (que flutuam sobre o canvas) usando a arquitetura de alta performance Surface WGPU, ou deveríamos desistir desta ideia?**

A resposta técnica é direta: **Não desista! É 100% possível e a solução é extremamente elegante.** 

A chave para conciliar o desempenho nativo do WGPU com a sofisticação das gavetas auto-hide é o **Padrão de Reparentamento Dinâmico (Dynamic Reparenting Pattern)**.

---

## 1. O Desafio Técnico: Pinar (Layout) vs Despinar (Sobreposição)

Para entender a solução, precisamos dividir o comportamento da doca lateral em seus dois estados fundamentais:

```
ESTADO 1: PINADO (Fixado)
┌───────────────────────────────────────────────┐
│ [Doca] ┌────────────────────────────────────┐ │
│ [Fixa] │ Canvas WGPU (Redimensionado)       │ │
│ [300px]│                                    │ │
│        └────────────────────────────────────┘ │
└───────────────────────────────────────────────┘
  ↳ Comportamento: Empurra o layout. Sem sobreposição. 
    Seguro para o Qt e WGPU nativos.

ESTADO 2: DESPINADO (Auto-hide/Flutuante)
┌───────────────────────────────────────────────┐
│ ┌──┐ ┌──────────────────────────────────────┐ │
│ │Sb│ │ Canvas WGPU (Área de Pintura Total)  │ │
│ └──┘ │                                      │ │
│   ┌──┴──────────────────────┐               │ │
│   │ Gaveta Flutuante        │               │ │
│   │ (Sobreposta ao Canvas)  │               │ │
│   └─────────────────────────┘               │ │
└───────────────────────────────────────────────┘
  ↳ Comportamento: A Gaveta abre por cima do Canvas.
    Se for widget filho direto, causa FLICKERING.
```

---

## 2. A Solução: Padrão de Reparentamento Dinâmico

A solução definitiva consiste em **mudar a natureza do widget da gaveta conforme o seu estado de pinamento**:

### 1. Quando o painel está PINADO:
*   O widget da gaveta é inserido no layout principal (`QHBoxLayout`) do workspace, ao lado do canvas.
*   O canvas diminui de tamanho para abrir espaço físico.
*   **Por que funciona**: Não há sobreposição física entre o canvas `WA_PaintOnScreen` e a gaveta. A pintura é limpa e sem conflitos.

### 2. Quando o painel está DESPINADO (Auto-hide):
*   O widget de conteúdo da gaveta é removido do layout principal e **reparentado** para uma janela flutuante baseada em `QDialog` com a flag `Qt.Tool | Qt.FramelessWindowHint` (exatamente como o `AdvancedPanel`).
*   Esta janela flutuante é posicionada via coordenadas globais imediatamente ao lado da barra de ícones (Sidebar) da doca.
*   A animação de slide (abrir/fechar de 0px a 300px) é executada na largura dessa janela flutuante externa.
*   **Por que funciona**: Como a gaveta agora é uma janela independente gerenciada pelo DWM do sistema operacional, ela flutua por cima do canvas nativo WGPU de forma 100% estável e sem piscar.

---

## 3. Arquitetura de Implementação (Portabilidade)

A transição de estados é transparente para o desenvolvedor e muito leve em termos de CPU:

```python
class AdvancedDockSystem(QtWidgets.QWidget):
    def __init__(self, side, parent_workspace):
        super().__init__(parent_workspace)
        self.side = side
        self.workspace = parent_workspace
        self.is_pinned = False
        
        # 1. A Sidebar de ícones (sempre fixada no layout principal, sem sobreposição)
        self.sidebar = SidebarWidget() 
        
        # 2. O contêiner de conteúdo da gaveta
        self.content_container = DrawerContentContainer()
        
        # 3. A janela flutuante para o estado auto-hide
        self.floating_shell = FramelessToolShell(parent=parent_workspace)
        
        self.resolve_state()

    def set_pinned(self, pinned: bool):
        self.is_pinned = pinned
        self.resolve_state()

    def resolve_state(self):
        if self.is_pinned:
            # 1. Tira do shell flutuante se estiver lá
            self.floating_shell.hide()
            # 2. Insere no layout fixo do Workspace
            self.workspace.dock_layout.addWidget(self.content_container)
            self.content_container.show()
        else:
            # 1. Remove do layout fixo
            self.workspace.dock_layout.removeWidget(self.content_container)
            # 2. Injeta no shell flutuante
            self.floating_shell.set_content(self.content_container)
```

---

## 4. Conclusão

**Não desista do Surface WGPU.** 

Voltar para a versão baseada em Readback significaria comprometer severamente o desempenho de pintura (limitação de taxa de atualização de tela, uso pesado de CPU para cópia de buffers de imagem e latência do cursor).

O **Reparentamento Dinâmico** oferece o melhor dos dois mundos:
1.  **Desempenho Extremo**: O motor WGPU renderiza direto na tela à velocidade máxima de hardware da máquina.
2.  **Sofisticação Visual**: O comportamento auto-hide das gavetas permanece idêntico ao planejado, operando por cima do canvas através de janelas nativas de ferramentas sem nenhuma falha visual ou interferência de renderização.
