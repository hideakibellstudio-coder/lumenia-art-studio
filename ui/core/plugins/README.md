# `ui/core/plugins/` — sistema de plugins

**Responsabilidade:** descoberta, dependências, ativação e desativação de plugins; o contrato que um plugin implementa (`BasePlugin` + `PluginMetadata`); o `ServiceRegistry` por onde casca e plugins trocam serviços; e a instalação segura de pacotes externos.

## Porta de entrada

`from ui.core.plugins import BasePlugin, PluginMetadata, PluginType,
ServiceRegistry, PluginManager, PluginContext, WorkspaceService`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Porta de entrada: reexporta as classes do contrato de plugin. |
| `base.py` | `BasePlugin`: ciclo de vida (`activate`/`deactivate`) e acesso ao `PluginContext`. |
| `canvas_access.py` | canvas_access — Caminho canônico para alcançar o canvas ativo. |
| `context.py` | `PluginContext`: o que um plugin recebe da casca (registro de serviços, fachada do motor). |
| `discovery.py` | Shared helpers for registering plugin classes from imported modules. |
| `lifecycle.py` | Transações de ativação e encerramento de plugins. |
| `manager.py` | PluginManager — Gerenciador do Ciclo de Vida e Descoberta de Plugins (Lumenia V2). |
| `metadata.py` | `PluginMetadata` e `PluginType`: identidade, versão, dependências e tipo do plugin. |
| `panel_ids.py` | `PanelId` (ids canônicos dos painéis) e `PANEL_TITLES` (título traduzível de cada um). |
| `package_installer.py` | PackageInstaller — Instalação, Validação e Desinstalação Segura de Pacotes de Plugins. |
| `package_manifest.py` | Contrato verificável para pacotes de plugins instalados externamente. |
| `registry.py` | `ServiceRegistry`: registro de serviços por tipo (casca e plugins registram e pedem implementações). |
| `workspace_contract.py` | `WorkspaceService`: contrato do workspace para plugins (painéis nas docas, canvas). |

## Regras

- Plugin nunca importa outro plugin (Lei nº 1); fala pelo `ServiceRegistry`
  ou pelo `WorkspaceService`.
- Serviço obrigatório: `ui.core.state.require(registry, Tipo)` (erro claro
  se a casca não instalou).
- Painel registrado com `add_panel` usa um `PanelId` (nunca string solta):
  o menu Janela e as docas acham o painel pelo mesmo id.
- Painel de plugin fala com o usuário emitindo um sinal que o plugin liga a
  `WorkspaceService.show_status` (nunca `QApplication.activeWindow()`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/engine`
- `ui/infrastructure`
- `ui/infrastructure/config`
- `ui/infrastructure/logging`
<!-- /arccc:deps -->
