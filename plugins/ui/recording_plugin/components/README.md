# `plugins/ui/recording_plugin/components/` — peças da gravação

**Responsabilidade:** o diálogo de progresso da exportação e a barra flutuante de controle (REC, pausa, parar).

## Porta de entrada

Importar por módulo.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `export_dialog.py` | Timelapse Export Dialog — Diálogo de Progresso de Exportação (ARCcC). |
| `recording_floating_bar.py` | RecordingFloatingBar — Barra de Controle Flutuante de Gravação (ARCcC). |

## Dívida conhecida (medida em 2026-09-24)

Pasta sem `__init__.py`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/theme`
<!-- /arccc:deps -->
