# `ui/core/screens/settings/components/` — peças do diálogo de temas

**Responsabilidade:** cartão e amostras de cada tema, e as folhas de estilo do diálogo.

## Porta de entrada

Importar por módulo (sem `__init__.py`): `theme_card`, `theme_dialog_styles`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `theme_card.py` | Components for Theme Settings Dialog (ThemeCard, Swatches). |
| `theme_dialog_styles.py` | ThemeDialogStyles — Folhas de Estilo e Formatação Visual do Diálogo de Temas. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/theme`
<!-- /arccc:deps -->
