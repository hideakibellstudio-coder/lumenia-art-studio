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
| `app_info.py` | Nome e versão do produto, fonte única para a interface; `tests/test_app_version.py` confere as cópias do empacotamento. |
| `runtime_paths.py` | Caminhos de recursos que funcionam no repositório e no executável empacotado (`resource_path`). |

| Pasta | Responsabilidade |
|---|---|
| `bridge_client/` | Cliente da ponte: `AladynBackend`, a implementação do contrato `EngineBackend` sobre `aladyn_engine_native`. |
| `config/` | Preferências da aplicação em JSON (`ConfigManager`), com esquema e migração. |
| `i18n/` | Traduções (`tr`, `I18nManager`) a partir de `assets/locales`. |
| `theme/` | `ThemeManager`: paletas, QSS, escala e ajustes de interface. |
| `icons/` | Catálogo SVG em código e `get_icon`. |
| `logging/` | Logging da aplicação (console e arquivo). |

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
