# `ui/plugins/panels/telemetry_plugin/` — plugin de telemetria

**Responsabilidade:** o painel de desempenho do motor em tempo real (latência por etapa do pipeline, FPS, memória), desligável sem custo.

## Porta de entrada

`TelemetryPlugin` (descoberto pelo `PluginManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `TelemetryPlugin`: registra o `TelemetryPanel` na doca direita. |
| `panel.py` | `TelemetryPanel`: resumo compacto na doca; view do `TelemetryTracker` (liga/desliga a coleta, abre cockpit e diagnóstico). |
| `panel_theme.py` | TelemetryPanelTheme — Estilização e Temas do Painel de Telemetria. |

## Regras

O painel não guarda estado de telemetria: lê o motor, entrega ao
`TelemetryTracker` e mostra. Banner, relatório e "Limpar Undo" vêm de
`ui/core/dialogs/telemetry_common.py`, iguais nas três telas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/dialogs`
- `ui/core/engine`
- `ui/core/plugins`
- `ui/core/widgets`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
