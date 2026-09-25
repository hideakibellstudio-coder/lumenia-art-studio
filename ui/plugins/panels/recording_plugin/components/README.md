# `ui/plugins/panels/recording_plugin/components/` — peças da gravação

**Responsabilidade:** o diálogo de progresso da exportação e a barra flutuante de controle (REC, pausa, parar).

## Porta de entrada

Importar por módulo.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `export_dialog.py` | Timelapse Export Dialog — Diálogo de Progresso de Exportação (ARCcC). |
| `recording_floating_bar.py` | `RecordingFloatingBar`: barra flutuante ancorada no topo do canvas; os botões emitem sinais, o estado chega por `update_state`. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/dialogs`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
