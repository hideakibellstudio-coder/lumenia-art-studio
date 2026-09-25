# `ui/core/screens/plugins/components/` — peças do gerenciador de plugins

**Responsabilidade:** o cartão de cada plugin e o inspetor de metadados.

## Porta de entrada

Importar por módulo: `plugin_card.PluginCard`, `plugin_inspector.PluginDetailsInspector`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `plugin_card.py` | PluginCard component for PluginsWindow. |
| `plugin_inspector.py` | PluginDetailsInspector component for PluginsWindow. |

## Dívida conhecida (medida em 2026-09-24)

`plugin_inspector.py` usa muitos `hasattr` sobre metadados de plugin; a pasta não tem porta de entrada.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/plugins`
- `ui/core/widgets/toggle`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
