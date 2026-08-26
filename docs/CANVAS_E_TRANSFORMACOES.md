# 📐 CANVAS, SELEÇÃO & TRANSFORMAÇÃO LIVRE — LUMENIA

Este documento descreve os modelos matemáticos, algoritmos de rasterização e arquitetura de manipulação de pixels utilizados no **Canvas**, na **Suíte de Seleções** e na **Ferramenta de Transformação Livre (Ctrl+T)** do Lumenia.

---

## 1. O Pipeline do Canvas (`CanvasWidget` & `LayerManager`)

O `CanvasWidget` gerencia o viewport interativo do artista com transformações em tempo real:

*   **Matriz de Viewport:** Combina translação de pan $(dx, dy)$, nível de zoom $z \in [0.05, 32.0]$ e rotação contínua de tela $\theta_{\text{view}}$ em uma matriz de projeção $3 \times 3$.
*   **Mapeamento Inverso de Coordenadas:** Quando a caneta ou mouse clica em coordenadas físicas da tela $(x_{\text{screen}}, y_{\text{screen}})$, a matriz inversa mapeia o ponto exatamente no espaço local da imagem $(x_{\text{canvas}}, y_{\text{canvas}})$, independentemente da rotação ou zoom aplicados.

---

## 2. Algoritmo da Suíte de Seleções & Marching Ants

A seleção é armazenada como uma **Máscara de 8-bits por pixel (Canal Alpha $\mathbf{M} \in [0, 255]$)** com dimensões idênticas às do canvas.

```
┌─────────────────────────────────────────────────────────────┐
│                     CANVAS (RGB 24-bit)                     │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                  MÁSCARA DE SELEÇÃO (1-bit / 8-bit)         │
│  - 0: Pixel totalmente protegido                            │
│  - 255: Pixel selecionado e editável                         │
└──────────────────────────────┬──────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│                    MARCHING ANTS OVERLAY                     │
│  - Detecção de contorno (Kernel Laplaciano / Sobel)         │
│  - Renderização QPen pontilhado animado (Dash Offset)       │
└─────────────────────────────────────────────────────────────┘
```

### 🪄 A. Varinha Mágica (Magic Wand)
1.  **Seed Point:** Obtém a cor de referência $C_0 = (R_0, G_0, B_0)$ no ponto clicado.
2.  **Flood Fill 8-Way:** Expande a busca para os 8 vizinhos imediatos com verificação de distância euclidiana no espaço RGB:
    $$d = \sqrt{(R - R_0)^2 + (G - G_0)^2 + (B - B_0)^2} \le \text{Tolerância}$$
3.  **Dilatação de 1px (Expansão de Borda):** Aplica um kernel morfológico de dilatação para avançar a máscara em 1 pixel sob a lineart, eliminando halos brancos durante o preenchimento com balde de tinta.

### 🐜 B. Marching Ants a 60 FPS
O contorno visível é calculado extraindo as bordas onde a máscara transita de $0 \to 255$. O `QPainter` desenha uma linha pontilhada bicolor (preto e branco) modulando o `dashOffset` por um timer de alta precisão a 60 FPS, garantindo contraste perfeito em qualquer cor de arte.

---

## 3. Algoritmo da Ferramenta de Transformação Livre (Ctrl+T)

A ferramenta de Transformação Livre permite deformar a camada inteira ou uma **Seleção Flutuante** isolada.

### 🎛️ A. Bounding Box & As 8 Alças Geométricas

```
 (Top-Left) [0] ────────── [1] (Top-Center) ────────── [2] (Top-Right)
       │                                                     │
       │                                                     │
 [7] (Mid-Left)                   (+) [Pivô Móvel]     [3] (Mid-Right)
       │                                                     │
       │                                                     │
(Bottom-Left) [6] ─────── [5] (Bottom-Center) ──────── [4] (Bottom-Right)
```

*   **Pivô Central Móvel:** Por padrão posicionado no baricentro da bounding box, mas pode ser livremente arrastado para qualquer coordenada da imagem (ex: para rotacionar um braço em torno do ombro do personagem).
*   **Detecção de Alça Ativa:** Cálculo de distância euclidiana da posição do cursor para cada uma das 8 alças no espaço do viewport com raio de tolerância de 12px.
*   **Zona de Rotação Externa:** Se o cursor estiver fora da bounding box em um raio de até 35px, o cursor muda para rotação e calcula o ângulo $\theta$ entre o vetor do pivô e o cursor.

---

### 🔬 B. Interpolação Bicúbica Nativa (C++) vs Bilinear

Ao confirmar a transformação, o buffer de pixels é reamostrado pelo motor C++ utilizando **Interpolação Bicúbica Convolucional**:

| Característica | Interpolação Bilinear (Comum) | Interpolação Bicúbica ALADYN (C++) |
| :--- | :--- | :--- |
| **Vizinhança de Amostragem** | $2 \times 2$ (4 pixels) | $4 \times 4$ (16 pixels) |
| **Ordem de Derivada** | $C^0$ (Descontínua na derivada) | $C^1$ (Gradiente contínuo e suave) |
| **Preservação de Linhas** | Tende a desfocar e embasar a lineart | **Mantém o contraste e nitidez nítidos** |
| **Desempenho** | Rápido | **Ultra Rápido (SIMD AVX2 em C++)** |

---

### ✂️ C. Pipeline de Seleção Flutuante
Quando a transformação é acionada com uma seleção ativa:
1.  **Recorte (Extraction):** Os pixels contidos na máscara são extraídos da camada de origem e colocados em um buffer flutuante temporário.
2.  **Limpeza da Base:** A área recortada na camada de origem é limpa (preenchida com transparência alfa zero).
3.  **Manipulação Interativa:** O artista translada, escala e gira o elemento flutuante em tempo real no overlay.
4.  **Reamostragem & Fixação (Commit):** Ao pressionar `Enter` ou clicar em Confirmar, o buffer flutuante é rasterizado via interpolação bicúbica e fundido (*stamped*) de volta na camada de destino, registrando uma única ação atômica no histórico de Undo/Redo.
