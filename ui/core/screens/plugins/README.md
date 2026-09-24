# `ui/core/screens/plugins/` — gerenciador de plugins

**Responsabilidade:** a janela que lista, filtra, liga/desliga e inspeciona plugins.

## Porta de entrada

`from ui.core.screens.plugins import PluginsWindow`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `PluginsWindow`. |
| `dialog.py` | PluginsWindow — Gerenciador Completo de Plugins & Inspector de Metadados (Lumenia V2). |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/screens/plugins/components`
- `ui/core/theme`
- `ui/core/widgets/toggle`
<!-- /arccc:deps -->
