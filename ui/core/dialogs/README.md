# `ui/core/dialogs/` — diálogos compartilhados

**Responsabilidade:** diálogos usados pela casca e pelos plugins, e as duas bases de janela: `BaseFramelessDialog` (diálogo sem moldura do sistema) e `FloatingToolWindow` (janela-ferramenta flutuante sobre o canvas).

## Porta de entrada

Importados por módulo: `base_dialog.BaseFramelessDialog`,
`floating_tool_window.FloatingToolWindow` (5 consumidores cada),
`telemetry_grid_window.TelemetryGridWindow`. `__init__.py` reexporta os diálogos.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta os diálogos do pacote. |
| `base_dialog.py` | BaseFramelessDialog — Janela e Diálogo Base Padronizado com Design System Lumenia V2. |
| `canvas_size_dialog.py` | Canvas & Image Size Dialog — Redimensionamento de Canvas e Imagem. |
| `diagnostics_dialog.py` | Diagnostics & Telemetry Dialog — Diagnósticos e Desempenho do Motor ALADYN. |
| `floating_panel_window.py` | `FloatingPanelWindow`: janela de ajustes avançados que arrasta pela própria janela e abre ao lado do canvas (área vinda de `WorkspaceService.canvas_area_rect`). |
| `floating_tool_window.py` | FloatingToolWindow — Base compartilhada para janelas-ferramenta flutuantes sobre o canvas. |
| `layer_properties_dialog.py` | Layer Properties Dialog — Diálogo de Propriedades e Ajuste da Camada. |
| `modify_selection_dialog.py` | Modify Selection Dialog — Diálogo para Expandir, Contrair e Suavizar Seleção (ARCcC i18n). |
| `render_color_management_components.py` | ColorManagementGroup — Componente UI de Gestão Profissional de Cor e Soft-Proofing. |
| `render_settings_components.py` | Components for RenderSettingsDialog (ProofingPreviewBar, ProfileCard, EnginePipelineGroup). |
| `render_settings_dialog.py` | RenderSettingsDialog — Central de Renderização, Perfis de Cor & Prova de Impressão (Lumenia V2). |
| `telemetry_diagnostics_cards.py` | ui.core.dialogs.telemetry_diagnostics_cards — Componentes de Cartões Métricos de Telemetria. |
| `telemetry_diagnostics_dialog.py` | TelemetryDiagnosticsDialog — Diálogo Avançado de Diagnóstico & Telemetria do ALADYN ENGINE. |
| `telemetry_grid_report.py` | TelemetryGridReport — Gerador de Relatório e Diálogo de Histórico do Cockpit de Telemetria. |
| `telemetry_grid_window.py` | TelemetryGridWindow — Cockpit de Telemetria e Diagnóstico em Grid do ALADYN ENGINE. |
| `test_report_dialog.py` | Test Report Dialog — Diálogo Executivo de Relatório de Testes e Verificação de Sistema. |
| `user_guide_dialog.py` | User Guide Dialog — Diálogo de Visualização do Guia do Usuário e Documentação. |

## Regras

Diálogo mostra e devolve dados; não fala com o motor por fora do `EngineRegistry`/`EngineBackend`. Cores pelo `ThemeManager`.

## Dívida conhecida (medida em 2026-09-24)

`render_settings_components.py`, `telemetry_diagnostics_dialog.py` e `test_report_dialog.py` estão acima de 420 linhas (perto da parede dos 450).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/color`
- `ui/core/config`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/theme`
- `ui/core/widgets`
- `ui/core/widgets/toggle`
<!-- /arccc:deps -->
