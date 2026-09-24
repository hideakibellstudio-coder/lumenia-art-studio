# `plugins/ui/recording_plugin/engine/` — motor de gravação

**Responsabilidade:** captura de quadros em segundo plano (sem travar o traço), aplicação de guias/marca d'água e compilação do vídeo ou ZIP.

## Porta de entrada

`recording_engine.TimelapseRecordingEngine` (criado pelo `RecordingPlugin`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `export_worker.py` | Timelapse Export Worker — Compilador Assíncrono FFmpeg e Fallback ZIP (ARCcC). |
| `frame_save_task.py` | FrameSaveTask — Tarefa Assíncrona de Salvamento de Frames de Gravação (ARCcC). |
| `recording_engine.py` | Timelapse Recording Engine — Motor de Captura e Sessão de Gravação (ARCcC). |

## Regras

Tamanho do quadro vem do documento ativo (`DocumentManager`), não de atributo privado do backend.

## Dívida conhecida (medida em 2026-09-24)

`recording_engine.py` passa de 400 linhas. Pasta sem `__init__.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/document`
- `ui/core/engine`
- `ui/core/plugins`
<!-- /arccc:deps -->
