# Análise Comparativa: Workspace Core (V1 Readback vs V2 Surface WGPU)

Esta análise detalha a viabilidade técnica e a estratégia para portar a interface elegante e reativa do **Workspace Core** (gavetas auto-hide, barra de ferramentas flutuante, overlays de seleção e menus de contexto) da versão legada (V1 Readback) para a versão atual (V2 Surface WGPU) sem perder o alto desempenho da renderização direta na GPU.

---

## 1. Tabela Comparativa de Arquitetura

| Característica | Versão V1 (Legada - Readback) | Versão V2 (Atual - Surface WGPU) | Implicações na Portabilidade |
| :--- | :--- | :--- | :--- |
| **Apresentação do Canvas** | Copia o buffer da GPU para a CPU (`staging buffer -> QImage -> QPainter`). | Apresentação nativa direta no handle da janela (`HWND` via swapchain do WGPU). | O Canvas atual tem desempenho máximo, mas impede composição de widgets filhos transparentes. |
| **Widgets de Overlays** | `QStackedLayout` com `StackAll` (Widgets transparentes desenhados por cima do Canvas). | Incompatível com `WA_PaintOnScreen` (causa flickering severo ou invisibilidade). | Overlays de desenho (como seleção e scrims) devem migrar para passos de renderização no Rust/WGPU. |
| **Painéis Flutuantes** | Popups e barras flutuantes (`QFrame` ou `QDialog`). | Devem ser instanciados como janelas nativas com flag `Qt.Tool \| Qt.FramelessWindowHint`. | Perfeitamente viável, pois o DWM do Windows cuida da composição de janelas independentes de forma estável. |
| **Docas (Gavetas)** | `AdvancedDockSystem` com auto-hide baseado em animação de `maximumWidth`. | `AdvancedDockSystem` empurrando o layout lateralmente. | 100% viável, pois o redimensionamento do canvas dispara o swapchain resize nativo perfeitamente. |

---

## 2. A Barreira Técnica do `WA_PaintOnScreen`

Na versão V2, o `CanvasWidget` é marcado com:
```python
self.setAttribute(QtCore.Qt.WA_PaintOnScreen, True)
```
Isso desativa a pintura dupla do Qt. O motor Rust WGPU escreve os pixels diretamente no buffer de tela (Backbuffer da Swapchain) associado ao `HWND` da janela.

### O Problema dos Overlays Clássicos (`QStackedLayout`)
Se tentarmos empilhar um widget semi-transparente como o `CanvasOverlay` ou o `SelectionOverlay` (que herdam de `QWidget`) em cima do canvas nativo, o Qt tentará renderizar esses widgets transparentes usando seu pipeline raster padrão (CPU). No entanto:
1.  Como a swapchain do WGPU atualiza o buffer de forma assíncrona e contínua, os desenhos do Qt serão atropelados, causando um efeito de piscar (**flickering**) constante.
2.  A entrada do mouse e cliques podem se perder devido à sobreposição de handles nativos vs sintéticos.

---

## 3. Estratégia de Implementação para a Versão V2 (Surface WGPU)

Para recriar a experiência da interface do Workspace Core legada na versão atual de forma limpa e otimizada, devemos adotar as seguintes soluções:

### A. Gavetas Laterais (`AdvancedDockSystem` e Auto-hide)
*   **Viabilidade**: **100% Viável**.
*   **Como implementar**:
    *   Podemos reintroduzir a classe `AdvancedDockSystem` controlando os painéis. 
    *   As animações de abrir/recolher a gaveta (alterando a largura máxima) reduzem ou expandem a área útil do canvas central.
    *   Como o `CanvasWidget` atual responde corretamente ao `resizeEvent` (recriando o swapchain e ajustando a projeção), a tela de pintura se adapta dinamicamente à largura das docas de forma fluida.

### B. Barra de Ferramentas Flutuante e Ajustes Rápidos (`FloatingToolbar`, `BrushQuickSettings`)
*   **Viabilidade**: **100% Viável**.
*   **Como implementar**:
    *   A toolbar e os popups rápidos não devem ser widgets filhos sobrepostos inseridos em layouts de divisão comuns.
    *   Eles devem ser criados como widgets independentes com a flag de janela de ferramentas frameless:
        ```python
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        ```
    *   Desta forma, o Windows (DWM) lida com a sobreposição de janelas, desenhando a barra flutuante por cima do canvas nativo do WGPU de forma estável, sem flickering.
    *   O snap magnético e o reposicionamento por clique/arrasto podem ser portados linha a linha do código original da toolbar.

### C. Overlays de Seleção (`SelectionOverlay`) e Scrim de Bloqueio (`CanvasOverlay`)
*   **Viabilidade**: **Inviável como Widgets Qt**. Deve ser delegado ao Rust/WGPU.
*   **Como implementar**:
    *   **Seleção (Lasso / Retângulo)**: Quando o usuário arrasta para selecionar, o `CanvasWidget` envia as coordenadas do mouse para o motor Rust. O próprio shader de desenho do Rust desenha a linha pontilhada de seleção diretamente na viewport 3D antes da apresentação final do frame.
    *   **Bloqueio de Canvas (Scrim)**: Quando uma gaveta auto-hide se expande, o `CanvasWidget` desativa os inputs de mouse de pintura locais. A viewport pode ser escurecida aplicando-se um overlay translúcido via shader (ou diminuindo temporariamente o brilho da renderização do canvas dentro do Rust).

---

## 4. Roteiro Passo a Passo de Codificação (Tradução da Lógica)

Se decidirmos implementar o Workspace Core na versão atual:

1.  **Fase 1: Preparação das Janelas Flutuantes**:
    *   Criar `FloatingToolbar` herdando de `QtWidgets.QFrame` com flag `Qt.Tool`.
    *   Implementar a lógica de drag e os eixos de snap magnético nas bordas físicas da `MainWindow`.
2.  **Fase 2: Gavetas Dinâmicas**:
    *   Criar o componente `AdvancedDockSystem` com suporte a `is_pinned` e cronômetro de hover (`QTimer` de 300ms) para auto-hide.
    *   Substituir as docks estáticas da direita e esquerda por instâncias dessa gaveta reativa.
3.  **Fase 3: Sincronização de Renderização**:
    *   Conectar os sinais `strokeStarted` / `strokeFinished` do Canvas para suspender a expansão automática da gaveta se o usuário estiver ativamente pintando.
