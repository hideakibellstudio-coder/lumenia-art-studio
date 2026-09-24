# `plugins/ui/telemetry_plugin/` — plugin de telemetria

**Responsabilidade:** o painel de desempenho do motor em tempo real (latência por etapa do pipeline, FPS, memória), desligável sem custo.

## Porta de entrada

`TelemetryPlugin` (descoberto pelo `PluginManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `TelemetryPlugin`: registra o `TelemetryPanel` na doca direita. |
| `panel.py` | TelemetryPanel — Painel Visual de Telemetria e Diagnóstico do ALADYN ENGINE. |
| `panel_theme.py` | TelemetryPanelTheme — Estilização e Temas do Painel de Telemetria. |

## Dívida conhecida (medida em 2026-09-24)

`panel.py` passa de 420 linhas (perto da parede dos 450).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/engine`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
