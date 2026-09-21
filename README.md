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

### 🖋️ 1. Motor de Pincéis ALADYN (Catmull-Rom Spline)
*   **Inker Spline Contínuo:** Interpolação matemática Catmull-Rom nativa em C++ para estabilização de traços.
*   **Dinâmica de Pressão:** Curvas de pressão configuráveis processadas pelo motor; a compatibilidade com mesas digitalizadoras requer homologação de hardware.
*   **Mídias Naturais:** Modos de Pincel de Tinta (Inker), Lápis de Esboço, Marcador com transparência, Aquarela com difusão e Óleo Impasto com relevo 3D processado em tempo real.
*   **Borracha Inteligente:** Apagamento suave e preservação perfeita de canais alfa.

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
*   **Pilha Hierárquica:** Camadas normais, grupos de camadas expansíveis e reordenação intuitiva.
*   **Modos de Mesclagem & Opacidade:** Controle fino de transparência e mesclagem de canais.
*   **Duplicação & Merge Down:** Mesclagem descendente com preservação de blend modes e grupos.
*   **Camada 0 (Cor de Papel):** Fundo base infinito customizável (branco, off-white, tom médio ou transparente).

### 🎨 5. Gerenciamento de Cores & Precisão Cromática
*   **Perfis de Cor:** Catálogo nativo de transformações para sRGB, Display P3 e simulações CMYK. Perfis ICC arbitrários e fluxo RGBA16/float permanecem no roadmap.
*   **Simulador de Daltonismo:** Prova em tempo real para Protanopia, Deuteranopia e Tritanopia.
*   **Conta-Gotas com HUD Loupe 4x:** Lupa circular dinâmica com leitura matricial de pixels e captura precisa.
*   **Temas Visuais:** *Lumenia Purple* oficial, *Obsidian Dark*, *OLED High Contrast* e temas customizáveis.

### 📐 6. Suíte de Simetrias Dinâmicas, Réguas & Perspectiva
*   **Simetrias em Tempo Real (C++ SIMD):** Espelho Livre, Espelho Vertical, Espelho Horizontal, Espelho Duplo (4 quadrantes), Simetria Radial (2 a 32 pontas) e Caleidoscópio.
*   **Controle de Centro & Stop-at-Center:** Pivô e ângulo de rotação ajustáveis diretamente no canvas, com bloqueio opcional para impedir que o traço ultrapasse o eixo.
*   **Atração Magnética (Snapping):** Réguas retas infinitas, curvas francesas Bézier com aproximação de Newton-Raphson e perspectivas de 1, 2 e 3 Pontos de Fuga e Isométrica.
*   **Seletor Premium em Grid:** Menu popup intuitivo com 14 ícones vetorizados na gaveta de ferramentas.

---

## 📂 Estrutura do Repositório

```text
Lumenia/
├── assets/                  # Ícones oficiais, imagens e tipografias
│   └── images/              # Logotipos (icon_lumenia.png)
│
├── ui/                      # Interface Gráfica PySide6 (Padrão BCE)
│   ├── main.py              # Ponto de entrada (QApplication, Splash Screen)
│   ├── boundary/            # Orquestradores e APIs públicas
│   │   └── orchestrator/    # MainWindow, menus e coordenação de eventos
│   ├── core/                # Componentes e subsistemas internos
│   │   ├── components/      # MenuBar, ToolSidebar, StatusBar, Splash
│   │   ├── document/        # Modelos de dados e gerenciamento de estado
│   │   ├── plugins/         # Gerenciador dinâmico de plugins (PluginManager)
│   │   ├── theme/           # Sistema de estilização QSS e temas dinâmicos
│   │   └── widgets/         # Widgets atômicos do canvas e controles
│   ├── engine_backends/     # Adaptadores de motor gráfico (aladyn.py)
│   └── utils/               # Helpers matemáticos, cores e formatadores
│
├── plugins/                 # Extensões e Módulos Desacoplados
│   ├── system/              # Plugins vitais do sistema (workspace_core)
│   ├── ui/                  # Plugins de interface (brush, color, layers, navigator)
│
├── data/                    # Dados graváveis ao executar o pacote portátil
│   └── plugins_config.json  # Preferências de plugins, com backup
│
├── docs/                    # Documentação Técnica Completa (ver docs/README.md)
│   ├── architecture/        # Arquitetura, engine nativo, modelo de documento, plugins
│   ├── guides/               # Guia do desenvolvedor, build/release, testes, Navigator
│   ├── specifications/       # Formato .lmn e gestão de cor
│   └── audit/                # Relatórios de auditoria e encerramento
│
└── aladyn_engine_native.pyd # Binário C++20 compilado (Windows x64)
```

---

## 🚀 Como Executar

### Opção A: Executar em Modo de Desenvolvimento (Python)

**Pré-requisitos:** Python 3.11+ (recomendado Python 3.14).

1. Instale as dependências:
   ```bash
   pip install -r requirements-dev.lock
   ```
2. Inicie o aplicativo:
   ```bash
   python main.py
   ```

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
- [ ] **Item 12:** Formato de Arquivo Nativo com Camadas (`.lmn`).

---

## 📄 Licença & Contato

*   **Desenvolvedor:** Equipe Lumenia / Maestros da IA
*   **E-mail de Contato & Feedback:** `lumeniateam@protonmail.com`
*   **Projeto:** Independente / Open Development
