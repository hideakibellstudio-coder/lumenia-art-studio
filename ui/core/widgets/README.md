# `ui/core/widgets/` — widgets compartilhados

**Responsabilidade:** widgets reutilizáveis por casca e plugins: moldura de painel (`PanelCardBox`), seção recolhível, slider compacto, cartão métrico, barra de pipeline, seletor de formas; subpastas de cor, slider, toggle e opções de ferramenta.

## Porta de entrada

Importados por módulo: `card_box.PanelCardBox` (6 consumidores),
`compact_slider.CompactSlider`, `shape_dropdown.ShapeDropdown`,
`collapsible_section.CollapsibleSection`, `pipeline_bar.PipelineBar`.
`ui.core.widgets` reexporta `ColorButton`, `ColorPaletteGrid`, `LabeledSlider`,
`ToggleSwitch`, `GridMetricCard`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta widgets das subpastas. |
| `card_box.py` | PanelCardBox — Caixa/Cartão Padronizado de Design System para Painéis V2. |
| `collapsible_section.py` | CollapsibleSection. |
| `compact_slider.py` | CompactSlider (com botões de acessibilidade (-) e (+) no visual quadrado - Captura 1). |
| `metric_card.py` | GridMetricCard — Card Métrico Compacto Reutilizável. |
| `pipeline_bar.py` | PipelineBar — Barra empilhada proporcional colorida para decomposição do pipeline nativo C++. |
| `shape_dropdown.py` | ui.core.widgets.shape_dropdown — Dropdown Personalizado em Grid para Formas Vetoriais. |

## Regras

Widget não guarda estado da aplicação (Lei do rio nº 1): mostra o que recebe e emite o que o usuário mexeu.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/widgets/color_picker`
- `ui/core/widgets/slider`
- `ui/core/widgets/toggle`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
