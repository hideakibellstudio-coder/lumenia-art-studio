# `plugins/` — plugins embutidos

**Responsabilidade:** raiz dos plugins que vêm com o Lumenia: `system/` (o workspace, sem o qual não há canvas) e `ui/` (painéis: pincel, cores, camadas, navegador, geometria, gravação, telemetria).

## Porta de entrada

Os plugins são descobertos pelo `PluginManager` (`ui/core/plugins`) a partir das pastas; num pacote compilado (Nuitka) a lista vem de `builtin_registry.py`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `builtin_registry.py` | Lista estática dos plugins embutidos para o pacote compilado (sem fontes para varrer). |

## Regras

- Lei nº 1: um plugin nunca importa outro plugin. Comunicação pelo
  `ServiceRegistry`/`WorkspaceService` ou pelo estado em `ui/core/state`.
- Plugin recebe o que usa pelo construtor dos seus widgets (injeção), obtendo
  os serviços com `ui.core.state.require(context.service_registry, Tipo)`.
- `plugins/plugins_config.json` guarda quais plugins estão ativos; os testes
  gravam num arquivo temporário (`LUMENIA_PLUGINS_CONFIG_PATH`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
