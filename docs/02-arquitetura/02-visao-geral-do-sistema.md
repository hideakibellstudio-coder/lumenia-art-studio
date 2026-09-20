# 🖥️ Visão Geral do Sistema (System Overview)

O **Lumenia Art Studio** é uma aplicação desktop profissional para ilustração digital, pintura e arte conceitual, combinando um frontend reativo em **Python 3.11+ / PySide6** com um motor de renderização de alto desempenho em **C++20 (ALADYN ENGINE)**.

---

## 🏗️ 1. Arquitetura em Camadas

```text
┌──────────────────────────────────────────────────────────┐
│                   LUMENIA UI (Qt/PySide6)                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Shell Principal (Menu, Barras, Dock Widgets)       │  │
│  └─────────────────────────┬──────────────────────────┘  │
│                            │                             │
│  ┌─────────────────────────▼──────────────────────────┐  │
│  │ Sistema MDI & Orquestração de Documentos           │  │
│  │ (Document, LocalLayerManager, DocumentHistory)     │  │
│  └─────────────────────────┬──────────────────────────┘  │
│                            │                             │
│  ┌─────────────────────────▼──────────────────────────┐  │
│  │ Backend Adapter (AladynBackend via Mixins)        │  │
│  │ + ColorManagementEngine (LittleCMS 2.18)           │  │
│  └─────────────────────────┬──────────────────────────┘  │
└────────────────────────────┼─────────────────────────────┘
                             │  PyBind11 Bridge (C++)
┌────────────────────────────▼─────────────────────────────┐
│                 ALADYN ENGINE CORE (C++20)               │
│  ┌────────────────────────────────────────────────────┐  │
│  │ PaintEngineFacade (API Canônica Unificada)         │  │
│  └─────────────┬────────────────────────┬─────────────┘  │
│                │                        │                │
│  ┌─────────────▼──────────┐ ┌───────────▼─────────────┐  │
│  │ StrokeOrchestrator     │ │ LayerStack & Composição │  │
│  │ + DynamicStabilizer    │ │ (Blending SIMD, Mipmap) │  │
│  └────────────────────────┘ └─────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

---

## 📂 2. Subsistemas Principais

### A. Shell e Orquestração (`ui/boundary/orchestrator/`)
- **`MainWindow`**: Janela mestre da aplicação, hospeda o viewport central, barras de ferramentas, seletores de cor e docks laterais.
- **`main_window_menu_actions.py`**: Trata comandos de arquivo, edição, seleção e visualização.
- **`main_window_image_actions.py`**: Trata redimensionamento de tela, corte (*crop*), rotações e transformações de canvas.

### B. Gestão Multi-Documento (MDI)
- Cada documento aberto é uma instância de `ui.core.document.document.Document`.
- O motor nativo gerencia uma instância de `PaintEngineFacade` por documento em seu mapa interno `_doc_facades`.
- A alternância de abas MDI ocorre em tempo constante $O(1)$ através de `backend.set_active_document_context(uid, width, height)`, garantindo isolamento total de pixels, histórico e camadas entre documentos.

### C. Recuperação de Falhas e Autosave em Background
- O `DocumentManager` monitora continuamente o estado sujo (*dirty*) dos documentos.
- Sessões inesperadamente interrompidas são recuperadas com base em transações atômicas seguras em arquivos de backup temporários `.lmn.bak`.\n