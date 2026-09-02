# 🎨 Lumenia Art Studio — Guia do Usuário

Bem-vindo ao **Lumenia Art Studio**, uma estação de trabalho profissional para pintura digital e arte conceitual 2D com alta fidelidade e latência ultra-baixa, potencializada pelo motor nativo **ALADYN C++20**.

---

## ⚡ 1. Visão Geral do Sistema

O Lumenia foi projetado segundo a arquitetura **ARCcC** (*Atomic Recursive Componentization by Contract*), separando estritamente a interface visual (PySide6) do motor físico de alta performance (C++20 com aceleração SIMD AVX2).

- **Resolução Infinita com Tiles Esparsos (64×64)**: O canvas gerencia blocos esparsos de memória, alocando pixels apenas onde há traços reais.
- **Interpolação Catmull-Rom & Clark**: Traços de caneta e stylus suaves, sem quebras pontilhadas em movimentos ultra-rápidos.
- **Suporte Multidocumento (MDI)**: Trabalhe em múltiplos documentos simultaneamente com instâncias isoladas do motor físico.

---

## 🖌️ 2. Ferramentas de Pintura

| Atalho | Ferramenta | Descrição |
| :---: | :--- | :--- |
| **B** | **Pincel** | Traço principal com física personalizável (Óleo, Aquarela, Grafite, Tinta). |
| **E** | **Borracha** | Apaga pigmentos preservando os canais alfa com suavização ajustável. |
| **U** | **Formas Vetoriais** | Retângulos, elipses, polígonos e estrelas com preenchimento ou traço. |
| **T** | **Texto** | Inserção tipográfica direta sobre o documento em camada rasterizada. |
| **I** | **Conta-Gotas** | Amostragem de cor de pixel único (1×1) ou média regional (3×3, 5×5). |
| **G** | **Balde de Tinta** | Preenchimento contíguo ou global com tolerância ajustável e anti-aliasing. |
| **W** | **Varinha Mágica** | Seleção por varredura cromática contígua ou difusa. |
| **Ctrl+T** | **Transformação** | Rotação, escala, espelhamento e translação livre com interpolação bicúbica. |

---

## 📐 3. Guias de Perspectiva e Simetria

Acesse o painel **Geometria & Simetria** na barra lateral para habilitar réguas interativas:
- **Réguas Planas**: Linhas retas, curvas Bézier e grades isométricas.
- **Perspectiva**: 1 Ponto (Central), 2 Pontos (Arquitetura) e 3 Pontos (Aérea/Zenital).
- **Perspectiva Curvilínea 6P**: Projeção olho de peixe esférica de 360° em tempo real.
- **Estúdio de Simetria**: Espelho Livre, Espelho Vertical, Espelho Horizontal, Espelho Duplo, Radial (3 a 36 eixos) e Caleidoscópio.

---

## 🎭 4. Camadas & Modos de Mesclagem

- **Organização Hierárquica**: Crie grupos aninhados com colapso/expansão instantâneos.
- **Modos de Mesclagem Suportados**:
  - *Normal*, *Multiplicar*, *Tela (Screen)*, *Sobrepor (Overlay)*, *Luz Suave*, *Luz Direta*.
  - *Escurecer*, *Clarear*, *Adicionar (Linear Dodge)*, *Borracha (Erase)*.
- **Recursos Avançados**: Máscara de Recorte (*Clipping Mask*), Bloqueio de Alfa (*Alpha Lock*) e Camadas de Ajuste Não-Destrutivas.

---

## 🎨 5. Modos de Cor & Prova de Cores (Soft Proofing)

Através do menu **Exibir > Prova de Cores & Renderização**:
- **Simulação de Gamut**: Visualize em tempo real como sua arte aparecerá em espaços de cor CMYK (FOGRA39, US Web Coated) ou dispositivos limitados.
- **Acessibilidade Visual**: Simulação integrada de daltonismo (Protanopia, Deuteranopia, Tritanopia e Acromatopsia).
- **Pipeline Deep Color (RGBA16F)**: Renderização com profundidade de 64 bits por pixel e correção gama linear eliminando bordas escuras.

---

## ⌨️ 6. Atalhos Essenciais

- `Ctrl + N`: Novo Documento
- `Ctrl + O`: Abrir Arquivo
- `Ctrl + S`: Salvar Documento
- `Ctrl + Shift + S`: Salvar Como
- `Ctrl + Z` / `Ctrl + Y`: Desfazer / Refazer
- `Ctrl + =` / `Ctrl + -`: Aproximar / Afastar Zoom
- `Espaço + Arrastar`: Mover Canvas (Pan)
- `Ctrl + A` / `Ctrl + D`: Selecionar Tudo / Desmarcar
