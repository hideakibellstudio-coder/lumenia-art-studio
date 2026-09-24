# `ui/core/screens/settings/components/` — peças do diálogo de temas

**Responsabilidade:** cartão e amostras de cada tema, o grupo de ajustes finos (raio, fonte, escala) e as folhas de estilo do diálogo.

## Porta de entrada

Importar por módulo: `theme_card`, `interface_tweaks_group`, `theme_dialog_styles`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `interface_tweaks_group.py` | `InterfaceTweaksGroup`: raio dos cantos, fonte e escala; view do `ThemeManager` (`set_interface_tweaks`, `set_ui_scale`). |
| `theme_card.py` | Components for Theme Settings Dialog (ThemeCard, Swatches). |
| `theme_dialog_styles.py` | ThemeDialogStyles — Folhas de Estilo e Formatação Visual do Diálogo de Temas. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/i18n`
- `ui/core/theme`
<!-- /arccc:deps -->
