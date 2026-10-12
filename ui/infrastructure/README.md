# `ui/infrastructure/` — infraestrutura da interface

**Responsabilidade:** os serviços técnicos que a interface inteira usa e que não têm regra de negócio: o cliente da ponte com o motor nativo, configuração, idioma, tema, ícones, logging e caminhos de recursos.

## Porta de entrada

Cada subpasta tem a sua (ver o README dela). Os mais usados:
`ui.infrastructure.i18n.tr`, `ui.infrastructure.theme.manager.ThemeManager`,
`ui.infrastructure.icons.get_icon`, `ui.infrastructure.config.ConfigManager`,
`ui.infrastructure.runtime_paths.resource_path`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `accessibility.py` | Nomes acessíveis (leitor de tela): controle sem texto visível recebe a dica traduzida, ou o rótulo ligado por `setBuddy`, como nome. |
| `app_info.py` | Nome e versão do produto, fonte única para a interface; `tests/test_app_version.py` confere as cópias do empacotamento. Também o repositório público das atualizações, o DSN dos relatórios de erro (vazio = por e-mail) e o e-mail de suporte. |
| `legacy_data.py` | Importação única dos dados que o instalador da Alpha deixava ao lado do executável (`<instalação>\data`) para a pasta de dados do usuário; não sobrescreve nem apaga. |
| `runtime_paths.py` | Caminhos de recursos que funcionam no repositório e no executável empacotado (`resource_path`); dados do usuário em `%APPDATA%\Lumenia` quando instalado (a pasta do programa é trocada a cada atualização) ou ao lado do executável numa cópia portátil (`portable.flag`). |

| Pasta | Responsabilidade |
|---|---|
| `bridge_client/` | Cliente da ponte: `AladynBackend`, a implementação do contrato `EngineBackend` sobre `aladyn_engine_native`. |
| `config/` | Preferências da aplicação em JSON (`ConfigManager`), com esquema e migração. |
| `i18n/` | Traduções (`tr`, `I18nManager`) a partir de `assets/locales`. |
| `theme/` | `ThemeManager`: paletas, QSS, escala e ajustes de interface. |
| `icons/` | Catálogo SVG em código e `get_icon`. |
| `logging/` | Logging da aplicação (console e arquivo). |
| `diagnostics/` | Pacotes de relatório de erro em disco e envio ao Sentry sem SDK. |
| `updater/` | Atualização pelo Velopack (buscar, baixar o delta numa thread, aplicar ao fechar). |

## Regras

- Infraestrutura não importa `ui/core` a não ser contratos que ela implementa:
  `bridge_client` implementa `ui.core.engine.EngineBackend` e usa os tipos de
  cor e o `LayerBlendMode` do núcleo. Nenhuma pasta daqui importa telas,
  widgets ou plugins.
- Entre as subpastas, dependência em uma direção só (o tema usa ícones e
  configuração; os ícones não usam o tema — o tema registra as cores com
  `icons.set_color_resolver`).
- Lei nº 2: só `bridge_client/` importa `aladyn_engine_native`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
