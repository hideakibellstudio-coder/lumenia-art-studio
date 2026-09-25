# `ui/plugins/` — plugins embutidos

**Responsabilidade:** as funcionalidades da interface empacotadas como plugins: `system/` (o workspace, sem o qual não há canvas) e `panels/` (painéis: pincel, cores, camadas, navegador, geometria, gravação, telemetria). No ARCcC são os módulos de negócio do pilar de interface; o carregador que os descobre e ativa mora em `ui/core/plugins`.

## Porta de entrada

O `PluginManager` (`ui/core/plugins`) descobre os plugins varrendo esta pasta no desenvolvimento e, num pacote compilado (Nuitka), pela lista de `builtin_registry.py`. Nome importável: `ui.plugins.<system|panels>.<plugin>`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote e explica as pastas de agrupamento sem `__init__.py`. |
| `builtin_registry.py` | Lista estática dos plugins embutidos para o pacote compilado (sem fontes para varrer). |
| `plugins_config.json` | Quais plugins estão ativos no desenvolvimento; os testes gravam num arquivo temporário (`LUMENIA_PLUGINS_CONFIG_PATH`) e o executável, na pasta de dados. |

| Pasta | Responsabilidade |
|---|---|
| `system/` | Plugins de sistema (`workspace_core`). |
| `panels/` | Plugins de painel (até 2026-09-25, `plugins/ui/` na raiz do repositório). |

## Regras

- Lei nº 1: um plugin nunca importa outro plugin
  (`tests/test_arccc_architecture_invariants.py`). Comunicação pelo
  `ServiceRegistry`/`WorkspaceService` ou pelo estado em `ui/core/state`.
- Plugin recebe o que usa pelo construtor dos seus widgets (injeção), obtendo
  os serviços com `ui.core.state.require(context.service_registry, Tipo)`.
- O resto de `ui/` não importa `ui.plugins` (catraca `reverse_import`); a
  exceção é o carregador em `ui/core/plugins`, que lê `builtin_registry.py`.
- `system/` e `panels/` não têm `__init__.py`: pasta com `__init__.py` é
  tratada como plugin pelo `PluginManager`.
- Plugin embutido novo: pasta em `system/` ou `panels/` e linha em
  `builtin_registry.py` (senão o executável não o encontra).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
