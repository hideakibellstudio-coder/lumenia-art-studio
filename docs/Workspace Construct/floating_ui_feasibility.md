# Viabilidade Técnica: O Padrão AdvancedPanel para Elementos Flutuantes (Floating UI)

Esta análise valida e aprofunda a ideia de utilizar a arquitetura lógica por trás do `AdvancedPanel` como um **modelo base (Design Pattern)** para implementar todas as interfaces flutuantes do Lumenia (como a `FloatingToolbar` e o `BrushQuickSettings`) sem o risco de flickering ou conflitos de desenho sobre o Canvas WGPU.

---

## 1. O Segredo do `AdvancedPanel` (Por que ele funciona?)

O `AdvancedPanel` funciona perfeitamente sobre o canvas nativo `WA_PaintOnScreen` porque ele não é um widget filho sintético (desenhado dentro do mesmo canvas de pintura do Qt), mas sim uma **Janela Nativa do Sistema Operacional (HWND independente)** disfarçada:

```python
class AdvancedPanel(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
```

### Análise dos Componentes de Sucesso:
1.  **`QtWidgets.QDialog` + `QtCore.Qt.Tool`**:
    *   Cria um novo handle de janela no Windows (`HWND`).
    *   A flag `Tool` garante que a janela permaneça sempre empilhada acima da janela mãe (o Lumenia), minimize/restaure junto com ela, mas **não apareça na barra de tarefas do Windows** como um aplicativo separado.
2.  **`FramelessWindowHint` + `WA_TranslucentBackground`**:
    *   Remove as bordas padrão do Windows (barra de título, botões Fechar/Minimizar).
    *   Permite que o Qt renderize transparências reais e cantos arredondados via CSS/QSS.
3.  **Composição DWM (Desktop Window Manager)**:
    *   Como a janela flutuante e o canvas WGPU possuem HWNDs separados, o Windows DWM gerencia a sobreposição em nível de hardware. Isso elimina 100% dos travamentos, piscadas de tela (flickering) e bugs de pintura assíncrona.

---

## 2. Generalização: O Padrão `LumeniaFloatingWidget`

Podemos extrair essa lógica para uma classe base abstrata e reutilizável chamada `LumeniaFloatingWidget` (ou similar). Qualquer painel que precise flutuar sobre o canvas herdará dela.

### Estrutura do Padrão Base:
```python
class LumeniaFloatingWidget(QtWidgets.QDialog):
    def __init__(self, parent=None, title=""):
        super().__init__(parent, QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        self.setWindowTitle(title)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        
        self._drag_pos = None
        self._is_snapped = False
        
    # --- Lógica de Arrastar (Drag) ---
    def mousePressEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & QtCore.Qt.LeftButton:
            new_pos = e.globalPosition().toPoint() - self._drag_pos
            self.move(new_pos)
            self._check_magnetic_snaps(new_pos)
            e.accept()

    def mouseReleaseEvent(self, e):
        self._drag_pos = None
        e.accept()
        
    def _check_magnetic_snaps(self, pos):
        # Lógica de atração magnética nas bordas da MainWindow
        pass
```

---

## 3. Aplicação nos Componentes do Workspace

A adoção desta arquitetura baseada em HWNDs independentes viabiliza os seguintes componentes sobre a versão Surface WGPU:

### A. Barra de Ferramentas Flutuante (`FloatingToolbar`)
*   **Implementação**: Herda de `LumeniaFloatingWidget`.
*   **Benefício**: Pode ser arrastada e posicionada livremente acima do canvas de pintura WGPU. A animação de recolher/expandir (auto-collapse) funciona alterando a largura da própria sub-janela sem interferir na viewport da engine.

### B. Ajustes Rápidos de Pincel (`BrushQuickSettings`)
*   **Implementação**: Herda de `LumeniaFloatingWidget`.
*   **Comportamento**: Quando o usuário pressiona `Q`, a janela é exibida nas coordenadas globais do cursor do mouse (`QtGui.QCursor.pos()`). Ao mover o mouse para fora dela ou clicar fora, ela se esconde (`self.hide()`), simulando um popup limpo e reativo.

### C. Barra de Ações Rápidas de Seleção (`SelectionActionBar`)
*   **Implementação**: Herda de `LumeniaFloatingWidget`.
*   **Comportamento**: Aparece flutuando centralizada logo acima da seleção ativa, sumindo automaticamente quando a seleção é desfeita.

---

## 4. Conclusão de Viabilidade

**A proposta é 100% viável e é a melhor prática recomendada de arquitetura de UI.**

Usar a lógica do `AdvancedPanel` (janela nativa frameless baseada em `QDialog` + `Qt.Tool`) para todos os elementos flutuantes resolve completamente o problema de renderização assíncrona do WGPU, pois delega a composição de camadas ao próprio sistema operacional, blindando a interface contra bugs visuais e mantendo o desempenho de renderização ultra-rápido da swapchain nativa.
