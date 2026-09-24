# `ui/core/screens/settings/` — aparência

**Responsabilidade:** o gerenciador e editor de temas.

## Porta de entrada

`from ui.core.screens.settings import ThemeDialog`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ThemeDialog`. |
| `theme_dialog.py` | ThemeDialog — Gerenciador & Customizador Completo de Aparência e Temas (Lumenia V2). |

## Dívida conhecida (medida em 2026-09-24)

`theme_dialog.py` está na parede dos 450 linhas: não recebe código novo sem antes ser dividido (regra do AGENTS.md).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/i18n`
- `ui/core/screens/settings/components`
- `ui/core/theme`
<!-- /arccc:deps -->
