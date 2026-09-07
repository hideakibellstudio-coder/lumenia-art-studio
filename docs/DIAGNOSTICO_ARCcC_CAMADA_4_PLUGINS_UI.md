# 🩺 DIAGNÓSTICO ARCcC v2 — CAMADA 4 (PLUGINS DE UI DOCKÁVEIS)
## *Raio-X Estrutural, Censo de Linhas (LOC) e Análise de Coesão de Domínio dos Plugins de Interface*

---

## 🧭 1. INTRODUÇÃO & ESCOPO

Este diagnóstico formaliza a avaliação arquitetural da **Camada 4 (Plugins de UI Dockáveis)** do ecossistema **Lumenia Art Studio**, aplicando rigorosamente a metodologia **ARCcC v2** (*Atomic Recursive Componentization by Contract*).

A Camada 4 compreende todos os plugins de interface hospedados em `plugins/ui/`, responsáveis pelos painéis acopláveis (*dock panels*), diálogos avançados de configuração, seletores visuais e controles que o usuário interage diretamente:
- **`brush_plugin/`**: Painel de configurações rápidas de pincel, seletor pop-up de presets, catálogo e diálogo avançado de dinâmica.
- **`layers_plugin/`**: Gerenciador hierárquico da pilha de camadas, modelo/visão em árvore, renderização de miniaturas e camada de papel.
- **`geometry_plugin/`**: Painel de guias de perspectiva, réguas magnéticas, simetria e diálogo flutuante avançado.
- **`color_plugin/`**: Roda cromática HSV/RGB, histórico de paletas e harmonias cromáticas.
- **`navigator_plugin/`**: Miniatura global de navegação do documento com câmera interativa.
- **`telemetry_plugin/`**: Painel de diagnóstico em tempo real do pipeline C++ nativo e Qt.

---

## 📊 2. CENSO QUANTITATIVO GLOBAL DA CAMADA 4

A varredura completa da árvore de diretórios `plugins/ui/` revelou:
- **Total de Arquivos Python**: **48 arquivos**
- **Volume Total de Linhas de Código (LOC)**: **8.803 linhas**
- **Arquivos Violando a Regra 4 ($\ge 500\text{ LOC}$)**: **3 arquivos**
- **Arquivos na Zona de Alerta Vermelha ($450 - 499\text{ LOC}$)**: **5 arquivos**
- **Arquivos na Zona de Alerta Amarela ($300 - 449\text{ LOC}$)**: **4 arquivos**
- **Arquivos na Faixa Segura ($< 300\text{ LOC}$)**: **36 arquivos (75%)**

### Ranking dos Arquivos Mais Densos da Camada 4:

| Posição | Arquivo | Linhas (LOC) | Classificação ARCcC v2 | Diagnóstico Primário |
|:---:|---|:---:|:---:|---|
| **1º** | `plugins/ui/brush_plugin/presets_data.py` | **583 LOC** | 🚨 **Violação Crítica** | Dicionário estático massivo misturado com resolução de i18n |
| **2º** | `plugins/ui/geometry_plugin/components/advanced_settings_dialog.py` | **572 LOC** | 🚨 **Violação Crítica** | God Dialog com 3 abas complexas inteiras embutidas inline |
| **3º** | `plugins/ui/brush_plugin/panel.py` | **569 LOC** | 🚨 **Violação Crítica** | God Panel (coluna de ferramentas + sliders + opções + estilos) |
| **4º** | `plugins/ui/layers_plugin/panel.py` | **487 LOC** | ⚠️ *Zona Vermelha* | Painel central com árvore de camadas, menus e atalhos |
| **5º** | `plugins/ui/brush_plugin/advanced_panel/panel.py` | **477 LOC** | ⚠️ *Zona Vermelha* | Diálogo avançado com duplicação de lógica de janela flutuante |
| **6º** | `plugins/ui/layers_plugin/paper.py` | **470 LOC** | ⚠️ *Zona Vermelha* | Linha de papel misturada com diálogo modal completo `TexturePopup` |
| **7º** | `plugins/ui/brush_plugin/brush_dropdown.py` | **458 LOC** | ⚠️ *Zona Vermelha* | Dropdown com grade de presets e filtros de categorias |
| **8º** | `plugins/ui/telemetry_plugin/panel.py` | **456 LOC** | ⚠️ *Zona Vermelha* | Dashboard de telemetria com cards analíticos e polling a 30 FPS |
| **9º** | `plugins/ui/brush_plugin/dialog.py` | **417 LOC** | 🟡 *Zona Amarela* | Diálogo legatário de configurações |
| **10º** | `plugins/ui/layers_plugin/model.py` | **377 LOC** | 🟡 *Zona Amarela* | Modelo hierárquico `QAbstractItemModel` com nós e flags |
| **11º** | `plugins/ui/navigator_plugin/panel.py` | **305 LOC** | 🟡 *Zona Amarela* | Painel com enquadramento de câmera e viewport |
| **12º** | `plugins/ui/layers_plugin/view.py` | **302 LOC** | 🟡 *Zona Amarela* | `QTreeView` customizada com tratamento de drag-and-drop |

---

## 🔬 3. RADIOGRAFIA QUALITATIVA DOS PRINCIPAIS FOCOS DE CONTAMINAÇÃO

### Foco 1: `presets_data.py` (583 LOC) — Monólito de Dados Estáticos & Dicionários
- **Problema de Domínio**: O arquivo mistura duas responsabilidades:
  1. A definição massiva de centenas de parâmetros de presets para 10 motores/famílias de pincéis (lápis, tinta, marcadores, esfuminho, aquarela, óleo, etc.).
  2. Mapeamento e tradução de nomes (`PRESET_I18N_KEYS`, `CATEGORY_I18N_KEYS`, `get_preset_display_name`, `get_category_display_name`).
- **Impacto**: Qualquer novo preset ou ajuste em pincel infla ainda mais o arquivo. Arquivo monolítico com 30KB de texto estático em código Python.
- **Remédio ARCcC**: Decompor o catálogo em módulos atômicos por categoria de mídia sob `presets/` (ex: `natural_media.py`, `digital_inking.py`, `paint_media.py`) e manter `presets_data.py` como Facade transparente e enxuta ($< 100\text{ LOC}$) preservando 100% dos imports públicos.

### Foco 2: `advanced_settings_dialog.py` (572 LOC) — God Dialog Multi-Aba
- **Problema de Domínio**: A classe `AdvancedGeometryDialog` implementa no mesmo arquivo:
  1. Criação e manipulação de janela flutuante sem borda, arraste por mouse e docking inteligente (`show_near`).
  2. Construção da página inteira de Perspectiva 6P (`_build_curv_page`, câmera 3D, densidade, FOV, sliders).
  3. Construção da página de Snapping e Guias Magnéticas (`_build_snap_page`, tolerâncias, cores, estilos de guia).
  4. Construção da página de Simetria (`_build_sym_page`, eixos radiais, rotação).
  5. Retranslação de dezenas de textos em 3 idiomas e restauração de padrões.
- **Impacto**: Testes unitários de simetria ou perspectiva precisam instanciar o monólito inteiro; editar a UI de perspectiva pode quebrar a UI de simetria.
- **Remédio ARCcC**: Extrair as 3 páginas para componentes especializados (`components/perspective_page.py`, `components/snapping_page.py`, `components/symmetry_page.py`) e isolar o helper de enquadramento flutuante. O diálogo se torna um coordenador de abas de apenas $\approx 160\text{ LOC}$.

### Foco 3: `brush_plugin/panel.py` (569 LOC) — God Panel com Colunas Cruzadas
- **Problema de Domínio**: O `BrushSettingsPanel` tenta orquestrar no mesmo arquivo:
  1. A coluna lateral esquerda de ferramentas de pintura (`_make_tool_column()`).
  2. A coluna direita de propriedades com `BrushDropdown` e `StrokePreview`.
  3. A criação de 8 `CompactSlider` (tamanho, opacidade, dureza, pressão, curvatura, estabilizador, espaçamento, densidade) com lógica de fixação/pinning.
  4. 6 widgets embutidos de ferramentas de terceiros (`EyedropOptionsWidget`, `BucketOptionsWidget`, `WandOptionsWidget`, `TransformOptionsWidget`, `SelectionOptionsWidget`, `ShapesOptionsWidget`).
  5. Lógica complexa de injeção de stylesheets dinâmicos de tema.
- **Impacto**: Alta fragilidade. Modificar uma ferramenta afeta a exibição do painel principal de pincéis.
- **Remédio ARCcC**: Extrair a coluna de seleção de ferramentas para `tool_selection_column.py` e a gestão dos sliders rápidos e pináveis para `quick_sliders_section.py`. Reduzir o painel para $< 250\text{ LOC}$.

### Foco 4: `layers_plugin/paper.py` (470 LOC) — Camada de Papel vs. Diálogo Modal
- **Problema de Domínio**: O arquivo deveria conter apenas a representação visual da linha de papel de fundo (`PaperLayerWidget`), mas abriga dentro de si o `TexturePopup` completo (um diálogo modal de 250 linhas para carregar, aplicar e pré-visualizar texturas e presets de papel).
- **Remédio ARCcC**: Extrair `TexturePopup` para `paper_texture_dialog.py`, reduzindo `paper.py` para $< 250\text{ LOC}$.

### Foco 5: `layers_plugin/panel.py` (487 LOC) — Orquestração da Pilha de Camadas
- **Problema de Domínio**: Limítrofe ao teto de 500 LOC. Contém ações de menu contextual, atalhos de camada e lógica de sincronização que podem ser limpos e delegados ao `panel_actions.py` existente.

---

## 🎯 4. DIRETRIZES DE ELEVAÇÃO PARA A CAMADA 4

1. **Meta Zero Violações**: 100% dos 48 arquivos de `plugins/ui/` devem ficar estritamente $< 500\text{ LOC}$ (com meta prioritária $< 300\text{ LOC}$).
2. **Preservação Contratual Rigorosa**:
   - `BrushSettingsPanel`, `AdvancedGeometryDialog`, `LayersPanel`, `presets_data.py` são consumidos por testes, adaptadores do workspace core e menus.
   - Suas assinaturas públicas, sinais (`settingsChanged`, `colorChanged`, `sizeChanged`, etc.) e propriedades públicas devem ser **100% preservadas**.
3. **Zero Regressão na Suíte de Testes**:
   - Atualmente, 171 testes passam com sucesso. A elevação deve manter **100% de aprovação** e adicionar testes dedicados para cada novo componente atômico.
4. **Paridade Multi-Workspace & Commits Granulares**:
   - Toda alteração deve ser sincronizada simultaneamente entre `+ LUMENIA` e `ALADYN + UI LUMENIA`.
