# `ui/core/widgets/slider/` — sliders

**Responsabilidade:** o slider com rótulo e os botões de passo (-/+).

## Porta de entrada

`from ui.core.widgets.slider import LabeledSlider, SliderStepButton`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Reexporta `LabeledSlider` e `SliderStepButton`. |
| `labeled_slider.py` | `LabeledSlider`: slider horizontal com rótulo, valor e botões de passo; ignora a roda do mouse. |
| `step_button.py` | `SliderStepButton`: botão -/+ desenhado em SVG que avança o slider um passo. |

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/theme`
<!-- /arccc:deps -->
