# `ui/core/i18n/` — idiomas

**Responsabilidade:** tradução da interface: `tr(chave, texto_padrão)` e o `I18nManager`, que troca o idioma e avisa as telas (`languageChanged`).

## Porta de entrada

`from ui.core.i18n import tr, I18nManager`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `tr` e `I18nManager`. |
| `manager.py` | I18nManager — Sistema Central de Internacionalização e Idiomas (Lumenia V2 / ARCcC). |

## Regras

Todo texto visível passa por `tr()`; tela que mostra texto conecta `languageChanged` a um `retranslate_ui`. Chave nova vai para os quatro arquivos de idioma em `assets/`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/config`
<!-- /arccc:deps -->
