# `plugins/ui/recording_plugin/` — plugin de gravação (timelapse)

**Responsabilidade:** grava quadros do canvas durante a pintura e exporta o timelapse em MP4 (FFmpeg) ou ZIP; painel na doca direita e barra flutuante de controle.

## Porta de entrada

`RecordingPlugin` (descoberto pelo `PluginManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `RecordingPlugin`: cria o motor de gravação, o painel e a barra flutuante. |
| `panel.py` | Timelapse Recording Panel — Painel Visual de Gravação & Timelapse (ARCcC). |

## Dívida conhecida (medida em 2026-09-24)

`panel.py` está na parede dos 450 linhas: não recebe código novo sem antes ser dividido.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/recording_plugin/components`
- `plugins/ui/recording_plugin/engine`
- `ui/core/plugins`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
