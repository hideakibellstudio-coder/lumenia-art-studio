# 🎨 LUMENIA — Digital Art & Paint Studio

<div align="center">
  <img src="assets/images/icon_lumenia.png" alt="Lumenia Logo" width="128" height="128">
  <br>
  <strong>Estúdio Desktop de Arte e Pintura Digital de Alta Performance</strong>
  <br>
  <em>Desenvolvido com ALADYN C++20 Native Engine & PySide6</em>
  <br><br>
  <img src="https://img.shields.io/badge/Versão-v0.2.0%20Alpha-9333ea?style=for-the-badge" alt="Versão Alpha">
  <img src="https://img.shields.io/badge/C%2B%2B-C%2B%2B20%20SIMD-blue?style=for-the-badge" alt="C++20 SIMD">
  <img src="https://img.shields.io/badge/GUI-PySide6%206.11-success?style=for-the-badge" alt="PySide6">
  <img src="https://img.shields.io/badge/Portátil-Pipeline%20de%20verificação-orange?style=for-the-badge" alt="Portátil">
</div>

---

## 📖 Visão Geral

O **Lumenia** é um software desktop para ilustração, arte conceitual, lineart e pintura digital, construído para priorizar resposta de caneta e um motor nativo eficiente. Metas de latência, inicialização e compatibilidade de hardware exigem homologação em cada ambiente de release.

O Lumenia combina um **motor C++20 com caminho SIMD opcional** (`aladyn_engine_native`) e interface modular baseada em **PySide6 (Qt6)** sob a arquitetura ARCcC. Consulte [docs/03-guias/02-build-e-release.md](docs/03-guias/02-build-e-release.md) para compilar o artefato x64 compatível e executar a validação.

---

## ⚡ Recursos e Capacidades Implementadas

### 🖋️ 1. Motor de Pincéis ALADYN (Catmull-Rom Spline & WMA)
*   **Inker Spline Contínuo:** Interpolação matemática Catmull-Rom nativa em C++ para estabilização de traços.
*   **Dinâmica de Pressão & Stylus:** Curvas de pressão, suporte completo a inclinação (`xTilt`, `yTilt`) e rotação da caneta (`twist`) propagados do tablet ao motor nativo.
*   **Estabilização Cinemática WMA:** `DynamicStabilizer` nativo C++ com escala configurável de 0% a 98%, compensação ponderada de latência e resposta instantânea para tap isolado (single-click).
*   **Mídias Naturais:** Modos de Pincel de Tinta (Inker), Lápis de Esboço, Marcador com transparência, Aquarela com difusão e Óleo Impasto com relevo 3D processado em tempo real.
*   **Borracha & Borrador Inteligente:** Apagamento suave, preservação perfeita de canais alfa e ferramenta borrador (`smudge`) com anel geométrico reativo.
*   **Cursores Reativos & Feedback Tátil:** Redimensionamento de anel sob o ponteiro em tempo real (`brush_size`), hotspot milimétrico para conta-gotas e feedback de Pan (`ClosedHand`) e Zoom Drag (`SizeVer`).

### 📐 2. Suíte de Seleção Inteligente & Balde de Tinta
*   **Varinha Mágica (Magic Wand - `W`):** Preenchimento de seleção contígua com tolerância configurável e expansão de borda de 1px (evita frestas brancas sob a lineart).
*   **Seleções Geométricas & Laço (`L`):** Retângulo, Elipse, Laço Livre e Laço Poligonal com suporte a operações booleanas (`Shift` para somar, `Alt` para subtrair).
*   **Marching Ants Dinâmico:** Contorno pontilhado animado a 60 FPS com visibilidade em qualquer tom de fundo.
*   **Balde de Tinta (`G`):** Preenchimento inteligente respeitando estritamente os limites da seleção ativa.

### 🔄 3. Ferramenta de Transformação Livre (`Ctrl+T`)
*   **Bounding Box com 8 Alças:** Redimensionamento livre, proporcional (`Shift`) e simétrico a partir do centro (`Alt`).
*   **Pivô Central Móvel:** Âncora reposicionável permitindo rotações anatômicas realistas em torno de pontos de articulação (ombros, cotovelos, olhos).
*   **Interpolação Bicúbica Nativa (C++):** Rotação e escala preservando a nitidez da arte sem pixelização ou borrados.
*   **Seleção Flutuante:** Recorte automático e transformação isolada da área selecionada.

### 📑 4. Sistema de Camadas & Grupos
*   **Pilha Hierárquica:** Camadas normais, grupos de camadas expansíveis (com suporte a *Pass Through*) e reordenação intuitiva.
*   **13 Modos de Mesclagem Matemáticos:** Normal, Multiply, Screen, Overlay, Darken, Lighten, Color Dodge, Color Burn, Hard Light, Soft Light, Difference, Exclusion e Pass Through, com suporte a Linear Gamma.
*   **Controles de Precisão:** Alpha Lock, Clipping Mask (máscaras de recorte) e opacidade em ponto flutuante.
*   **Duplicação & Merge Down:** Mesclagem descendente com preservação de blend modes e grupos.
*   **Camada 0 (Cor de Papel):** Fundo base infinito customizável (branco, off-white, tom médio ou transparente).
*   **Dirty Tracking Total:** 18 operações de camada integradas à notificação de documento modificado (`*`) e histórico nativo.

### 🎨 5. Gerenciamento de Cores & Precisão Cromática
*   **Perfis de Cor & LittleCMS:** Catálogo unificado de perfis (sRGB, Display P3, Adobe RGB, CMYK) com engine LittleCMS para Soft-Proofing e perfis ICC customizados.
*   **Coerção Cromática Resiliente:** Função canônica `to_native_color_rgba` garantindo conversão segura entre QColor, tuplas e estruturas nativas C++.
*   **Simulador de Daltonismo:** Prova em tempo real para Protanopia, Deuteranopia e Tritanopia.
*   **Conta-Gotas com HUD Loupe 4x:** Lupa circular dinâmica com leitura matricial de pixels e captura precisa.
*   **Temas Visuais:** *Lumenia Purple* oficial, *Obsidian Dark*, *OLED High Contrast* e temas customizáveis.

### 📐 6. Suíte de Simetrias Dinâmicas, Réguas & Perspectiva
*   **Simetrias em Tempo Real (C++ SIMD):** Espelho Livre, Espelho Vertical, Espelho Horizontal, Espelho Duplo (4 quadrantes), Simetria Radial (2 a 32 pontas) e Caleidoscópio.
*   **Controle de Centro & Stop-at-Center:** Pivô e ângulo de rotação ajustáveis diretamente no canvas, com bloqueio opcional para impedir que o traço ultrapasse o eixo.
*   **Atração Magnética (Snapping):** Réguas retas infinitas, curvas francesas Bézier com aproximação de Newton-Raphson e perspectivas de 1, 2 e 3 Pontos de Fuga e Isométrica.
*   **Seletor Premium em Grid:** Menu popup intuitivo com 14 ícones vetorizados na gaveta de ferramentas.

### 🛡️ 7. Arquitetura em 6 Camadas, Retorno dos 5 Rios & Confiabilidade Zero-Leak
*   **Metodologia Concentric Satellite Peeling:** Arquitetura concêntrica de 6 camadas (UI $\to$ Plugins $\to$ Canvas Bridge $\to$ Python Backend $\to$ Fronteira PyBind11 $\to$ Núcleo Físico C++).
*   **Retorno Ascendente dos 5 Rios:** Validação bidirecional de fluxo de dados de ponta a ponta (Traço, Câmera/Viewport, Camadas/Histórico, Seleção/Transformação e Cor/Perfis).
*   **Qualidade e Zero Regressão:** **725 testes automatizados (100% verde)** e portão de estresse de longa duração aprovado ($\Delta\text{GDI} = 0$, $\Delta\text{Handles} = 0$, Drift de Memória Privada = $0.00\text{ MB} / 100\text{ ciclos}$).
*   **Governança ARCcC:** Limite estrito de < 450 linhas de código por arquivo (Zona Verde) em todo o código Python e C++.

---

## 📂 Estrutura do Repositório

```text
Lumenia/
├── bridge/                  # Ponte PyBind11 C++ ↔ Python
│   ├── boundary/contracts/  # Contratos tipados (aladyn_engine_native.pyi)
│   └── core/bindings/       # BufferContract.hpp (segurança de memória) e bind_*.cpp
│
├── engine/                  # ALADYN Native Engine (C++20 SIMD)
│   ├── boundary/public-api/ # PaintEngineFacade e 11 Orquestradores de Borda
│   └── core/                # TileGrid, TileUndoManager, Compositor, DabRenderer
│
├── ui/                      # Interface Gráfica PySide6 (Padrão BCE & Mixins)
│   ├── main.py              # Ponto de entrada (QApplication, Splash Screen)
│   ├── boundary/            # MainWindow, menus e coordenação de eventos
│   ├── core/                # DocumentManager, temas, internacionalização (i18n)
│   └── engine_backends/     # AladynBackend e 10 Mixins de domínio especializados
│
├── plugins/                 # Extensões e Módulos Desacoplados (Caixas-Pretas)
│   ├── system/              # Plugins do sistema (workspace_core, render_widget)
│   └── ui/                  # Plugins de interface (brush, color, layers, navigator)
│
├── tests/                   # 82 Suítes Automatizadas (725 testes com 100% aprovação)
│
├── docs/                    # Documentação Técnica Canônica (ver docs/README.md)
│   ├── 01-correcao-da-base/ # Pendências vivas, auditoria orbital e simplificação da ponte
│   ├── 02-arquitetura/      # Framework ARCcC, ALADYN engine, modelo de documento
│   ├── 03-guias/            # Guias de desenvolvimento, build portátil e testes
│   ├── 04-especificacoes/   # Formato .lmn e gestão cromática LittleCMS
│   ├── 05-visao-e-futuro/   # Roadmap estratégico e pipeline HDR/Deep Color
│   └── historico/           # Auditorias históricas encerradas (F-001 a F-031)
│
└── aladyn_engine_native.pyd # Binário C++20 compilado (Windows x64)
```

---

## 🚀 Como Executar

### Opção A: Executar em Modo de Desenvolvimento (Python)

**Pré-requisitos:** Windows x64, Python 3.11+ (recomendado 3.14) e o Visual
Studio Build Tools com a carga "Desenvolvimento para desktop com C++" (o
script de build encontra o compilador sozinho).

1. Instale as dependências:
   ```bash
   pip install -r requirements-dev.lock
   ```
2. Compile o motor C++ (gera `aladyn_engine_native.*.pyd` na raiz; os objetos
   intermediários vão para `../build`):
   ```bash
   python scripts/build_native.py --simd scalar
   ```
   Em CPU com AVX2 dá para usar `--simd avx2`. O binário não vai para o
   repositório: sem este passo o aplicativo abre, mas sem motor (canvas vazio).
3. Inicie o aplicativo:
   ```bash
   python main.py
   ```
   (ou `Iniciar_Lumenia.bat`). Para conferir a instalação:
   `python tests/run_all_tests.py`.

São os mesmos passos que o CI (`.github/workflows/ci.yml`) executa a partir de
um clone limpo em cada commit.

### Opção B: Versão Portátil Autônoma (Sem Instalação)

Gere o bundle com Nuitka a partir do motor nativo compilado:
```bash
python scripts/build_portable.py
```
O processo produz `build/portable/Lumenia.dist/Lumenia.exe` e um manifesto
SHA-256 dos arquivos distribuídos. Antes de publicar, execute a validação do
aplicativo e do instalador no ambiente de destino. Consulte [docs/03-guias/02-build-e-release.md](docs/03-guias/02-build-e-release.md)
para gerar o instalador Inno Setup e para os requisitos de assinatura de release.

---

## 🗺️ Roadmap de Próximas Implementações

- [ ] **Item 9:** Formas Vetoriais / Primitivas Rápidas (Linhas, Retângulos, Círculos e Estrelas).
- [ ] **Item 9.5:** Motor de Texto *In-Place* com tipografia editável direto no canvas.
- [ ] **Item 10:** Harmonias e Modos de Cor do Infinite Painter.
- [x] **Item 11:** Réguas, Simetrias Dinâmicas e Guias de Perspectiva (1, 2 e 3 Pontos de Fuga e Isométrica).
- [x] **Item 12:** Formato de Arquivo Nativo com Camadas (`.lmn` v2 com integridade e fuzzing).
- [x] **Item 13:** Consolidação da Base Primordial C++ e Retorno dos 5 Rios com Zero Regressão.

---

## 📄 Licença & Contato

*   **Desenvolvedor:** Equipe Lumenia / Maestros da IA
*   **E-mail de Contato & Feedback:** `lumeniateam@protonmail.com`
*   **Projeto:** Independente / Open Development
