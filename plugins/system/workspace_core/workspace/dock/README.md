# `plugins/system/workspace_core/workspace/dock/` — peças das docas laterais

**Responsabilidade:** barra lateral de ícones, cabeçalho e conteúdo das gavetas, animações de recolher/expandir, cálculo de geometria e persistência da disposição dos painéis — usadas pelo `AdvancedDockSystem` (`dock_system.py`, na pasta mãe).

## Porta de entrada

Importar por módulo; quem usa é `dock_system.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `dock_animator.py` | DockAnimator — Animation Orchestration and Auto-Collapse Timers for Docks. |
| `dock_geometry_calculator.py` | DockGeometryCalculator — Geometry, Positioning, and Bounds Calculations for Docks. |
| `dock_state_store.py` | DockStateStore — State Serialization, Layout Persistence, and i18n for Docks. |
| `drawer_content_container.py` | DrawerContentContainer component for Workspace Dock System. |
| `drawer_header.py` | DrawerHeader component for Workspace Dock System. |
| `sidebar_button.py` | SidebarButton component for Workspace Dock System. |
| `sidebar_widget.py` | SidebarWidget component for Workspace Dock System. |

## Dívida conhecida (medida em 2026-09-24)

- `dock_animator.py` e `dock_state_store.py` importam `AdvancedDockSystem` da
  pasta mãe só para tipo. Desde 2026-09-24 nenhum lê privado da doca: a doca
  expõe `is_painting`, `has_panel`, `set_panel_order`; o animador,
  `schedule_collapse`/`cancel_collapse`/`auto_collapse`; a sidebar e a gaveta,
  `buttons()`/`panel_widget()`; e o animador avisa mudança de largura por
  callback (antes chamava `_workspace._update_pill_positions()`).
- `DockStateStore.serialize_state/restore_state` têm teste, mas o app ainda
  não salva nem restaura o estado das gavetas entre sessões (decisão pendente).
- Pasta sem `__init__.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/system/workspace_core/workspace`
- `ui/core`
- `ui/core/i18n`
- `ui/core/theme`
<!-- /arccc:deps -->
