# `plugins/ui/geometry_plugin/components/` — peças do painel de geometria

**Responsabilidade:** o diálogo de ajustes avançados (abas de simetria, perspectiva curvilínea, encaixe e guias), o seletor de guia e as constantes de nomes.

## Porta de entrada

`from .components import ...` reexporta as três abas do diálogo avançado; o diálogo (`advanced_settings_dialog`) e o seletor (`geometry_selector`) são importados por módulo.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta as abas do diálogo avançado (simetria, perspectiva curvilínea, encaixe e guias). |
| `advanced_settings_dialog.py` | Advanced Geometry Dialog padronizado no Design System do Lumenia V2. |
| `constants.py` | Constants and Identifier mappings for Rulers and Symmetry. |
| `curvilinear_perspective_page.py` | CurvilinearPerspectivePage — 6P Curvilinear Perspective tab for AdvancedGeometryDialog. |
| `geometry_selector.py` | Geometry Selector Button with 2-Tab Category Grid and Smart Screen Clamping. |
| `snapping_guides_page.py` | SnappingGuidesPage — Snapping & Guides tab for AdvancedGeometryDialog. |
| `symmetry_settings_page.py` | SymmetrySettingsPage — Symmetry tab for AdvancedGeometryDialog. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core`
- `ui/core/dialogs`
- `ui/core/geometry`
- `ui/core/i18n`
- `ui/core/theme`
- `ui/core/widgets`
<!-- /arccc:deps -->
