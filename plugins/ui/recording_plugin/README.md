# `plugins/ui/recording_plugin/` — plugin de gravação (timelapse)

**Responsabilidade:** grava quadros do canvas durante a pintura e exporta o timelapse em MP4 (FFmpeg) ou ZIP; painel na doca direita e barra flutuante de controle.

## Porta de entrada

`RecordingPlugin` (descoberto pelo `PluginManager`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `RecordingPlugin`: cria o motor de gravação, liga o `strokeFinished` do canvas a ele e registra o painel. |
| `panel.py` | `RecordingPanel`: estado, opções e diagnósticos da gravação (view do motor); dono da barra flutuante. |
| `recording_actions.py` | `RecordingActions`: iniciar/pausar, parar, salvar e descartar com os diálogos, para o painel e a barra. |

## Regras

Painel e barra flutuante são views do `TimelapseRecordingEngine`; as ações
com o usuário ficam no `RecordingActions`. A barra não conhece o painel
(emite sinais); o motor não conhece o canvas (o plugin liga o fim do traço).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/recording_plugin/components`
- `plugins/ui/recording_plugin/engine`
- `ui/core/plugins`
- `ui/core/widgets`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
