# `plugins/ui/recording_plugin/engine/` — motor de gravação

**Responsabilidade:** captura de quadros em segundo plano (sem travar o traço), aplicação de guias/marca d'água e compilação do vídeo ou ZIP.

## Porta de entrada

`recording_engine.TimelapseRecordingEngine` (criado pelo `RecordingPlugin`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `export_worker.py` | Timelapse Export Worker — Compilador Assíncrono FFmpeg e Fallback ZIP (ARCcC). |
| `frame_save_task.py` | FrameSaveTask — Tarefa Assíncrona de Salvamento de Frames de Gravação (ARCcC). |
| `frame_source.py` | `DocumentFrameSource`: cada quadro = pixels do motor + tamanho, papel e guias do documento ativo. |
| `recording_engine.py` | `TimelapseRecordingEngine`: sessão (iniciar, pausar, parar, descartar), gatilhos e captura assíncrona. |

## Regras

O motor de gravação não conhece o canvas: o quadro vem da fonte
(`DocumentFrameSource`, documento ativo + `EngineBackend`) e o fim do traço
chega por `on_stroke_finished`, que o plugin liga ao `strokeFinished` do
canvas. Até 2026-09-24 ele guardava o canvas e lia tamanho, papel e guias
dele com `getattr`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/document`
- `ui/core/engine`
- `ui/infrastructure`
<!-- /arccc:deps -->
