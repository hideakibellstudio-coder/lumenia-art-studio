# `plugins/ui/navigator_plugin/` — plugin do navegador

**Responsabilidade:** o painel com a miniatura do documento, o retângulo da área visível e controles de zoom, rotação e espelhamento.

## Porta de entrada

`NavigatorPlugin` (descoberto pelo `PluginManager`); o painel é `NavigatorPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | `NavigatorPlugin`: registra o `NavigatorPanel` na doca direita. |
| `panel.py` | `NavigatorPanel` e `NavigatorControls`: miniatura, zoom, rotação e espelhamento; emite as mudanças de câmera para o workspace. |

## Regras

Recebe a câmera do canvas pelo `cameraChanged` (via workspace) e devolve mudanças por sinal; não escreve no canvas.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `plugins/ui/navigator_plugin/components`
- `ui/core`
- `ui/core/i18n`
- `ui/core/plugins`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
