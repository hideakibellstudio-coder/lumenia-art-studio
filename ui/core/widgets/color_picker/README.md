# `ui/core/widgets/color_picker/` — seletor de cor

**Responsabilidade:** a roda de cores, amostras, campo hexadecimal, cores recentes e as harmonias de cor.

## Porta de entrada

`from ui.core.widgets.color_picker import ColorButton, ColorPaletteGrid`; a roda por módulo (`color_wheel.ColorWheelWidget`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `ColorButton` e `ColorPaletteGrid`. |
| `color_swatch_widgets.py` | Color swatch and auxiliary widgets for ColorWheel. |
| `color_wheel.py` | Unified Color Wheel Component for Lumenia. |
| `harmony.py` | Harmonias de cor na roda (complementar, análogas, tríade...) -- 2026-09-23. |
| `harmony_widgets.py` | Faixa de harmonias do painel de cores: escolha da regra + amostras clicáveis. |
| `picker.py` | `ColorButton` e `ColorPaletteGrid`: botão de cor e grade de amostras. |

## Regras

A roda é uma view: o painel de cores a liga ao `BrushState` (`ui/plugins/panels/color_plugin`).

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/infrastructure/config`
- `ui/infrastructure/i18n`
- `ui/infrastructure/icons`
- `ui/infrastructure/theme`
<!-- /arccc:deps -->
