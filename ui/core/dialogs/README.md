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
| `crash_report_dialog.py` | `CrashReportDialog`: pergunta se um relatório de erro pode sair da máquina (enviar, agora não, descartar; "enviar sempre" vira a preferência). |
| `diagnostics_dialog.py` | `DiagnosticsDialog`: informações do sistema (motor, documento, perfil de cor, RAM medida pelo motor, versões). |
| `floating_panel_window.py` | `FloatingPanelWindow`: janela de ajustes avançados que arrasta pela própria janela e abre ao lado do canvas (área vinda de `WorkspaceService.canvas_area_rect`). |
| `floating_tool_window.py` | FloatingToolWindow — Base compartilhada para janelas-ferramenta flutuantes sobre o canvas. |
| `layer_properties_dialog.py` | Layer Properties Dialog — Diálogo de Propriedades e Ajuste da Camada. |
| `modify_selection_dialog.py` | Modify Selection Dialog — Diálogo para Expandir, Contrair e Suavizar Seleção (ARCcC i18n). |
| `pen_calibration_dialog.py` | `PenCalibrationDialog`: calibra a pressão da caneta (zona morta, pressão total, gama) à mão ou pela sugestão medida no quadro; grava no motor e na configuração (`pen`). |
| `pen_calibration_pad.py` | `PressurePad`: quadro onde o artista desenha para o assistente medir a pressão bruta da caneta (o mouse não conta). |
| `render_color_management_components.py` | ColorManagementGroup — Componente UI de Gestão Profissional de Cor e Soft-Proofing. |
| `render_settings_components.py` | Components for RenderSettingsDialog (ProofingPreviewBar, ProfileCard, EnginePipelineGroup). |
| `render_settings_dialog.py` | RenderSettingsDialog — Central de Renderização, Perfis de Cor & Prova de Impressão (Lumenia V2). |
| `telemetry_benchmark.py` | `run_stroke_benchmark`: benchmark sintético num contexto nativo descartável (não pinta no documento do usuário). |
| `telemetry_common.py` | O que as três telas de telemetria compartilham: `banner_style` por estado, `copy_report`, `clear_undo_history` (o "Limpar Undo" real, via `DocumentHistory.clear`). |
| `telemetry_diagnostics_cards.py` | ui.core.dialogs.telemetry_diagnostics_cards — Componentes de Cartões Métricos de Telemetria. |
| `telemetry_diagnostics_dialog.py` | `TelemetryDiagnosticsDialog`: diagnóstico em abas (desempenho, memória, pipeline, caneta, logs e benchmark). |
| `telemetry_grid_window.py` | `TelemetryGridWindow`: cockpit não modal com os 20 medidores (`telemetry_meters`); view do `TelemetryTracker`. |
| `telemetry_state_history_dialog.py` | `TelemetryStateHistoryDialog`: linha do tempo das transições de estado do pipeline. |
| `test_report_dialog.py` | `TestReportDialog`: roda a suíte com log ao vivo e mostra o resultado medido (cartões e seções). |
| `test_report_model.py` | `parse_junit`: JUnit XML do pytest → contagens totais e por seção (`SECTIONS`). |
| `test_report_runner.py` | `TestRunnerThread`: executa `tests/run_all_tests.py --junit` sem travar a interface (XML na pasta temporária do sistema). |
| `update_dialog.py` | `UpdateDialog`: versão nova e notas; atualizar e reiniciar, instalar ao fechar ou depois. |
| `user_guide_dialog.py` | User Guide Dialog — Diálogo de Visualização do Guia do Usuário e Documentação. |

## Regras

Diálogo mostra e devolve dados; não fala com o motor por fora do `EngineRegistry`/`EngineBackend`. Cores pelo `ThemeManager`.

Telemetria: as três telas (cockpit, painel do plugin e diagnóstico) são views
do `TelemetryTracker` (`ui/core/engine`). Estado, picos, histórico de
transições e o texto do relatório moram lá; tela nenhuma guarda cópia. Os 20
medidores são definidos em `ui/core/engine/telemetry_meters.py`.

## Dívida conhecida (medida em 2026-09-24)

`render_settings_components.py` está acima de 420 linhas (perto da parede dos 450).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/color`
- `ui/core/diagnostics`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/state`
- `ui/core/updates`
- `ui/core/widgets`
- `ui/core/widgets/toggle`
- `ui/infrastructure`
- `ui/infrastructure/config`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
