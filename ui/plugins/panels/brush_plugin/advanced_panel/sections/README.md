# `ui/plugins/panels/brush_plugin/advanced_panel/sections/` — seções do painel avançado

**Responsabilidade:** as seções do painel avançado (tamanho/opacidade, geometria da ponta, jitter, textura e espaçamento), cada uma dona dos próprios widgets.

## Porta de entrada

Classes `SizeOpacitySection`, `TipGeometrySection`, `JittersSection`, `BrushTextureSection` e `SpacingSection`, todas `AdvancedSection(brush_state, writer)`, criadas pelo `AdvancedPanel`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `base.py` | `AdvancedSection`: controles rápidos (→ `BrushState`) e do motor (→ `BrushEngineWriter`), `show_param` e `show_profile`. |
| `brush_texture_section.py` | Seções 4 e 5: textura (matéria) do pincel e espaçamento. |
| `jitters_section.py` | Seção 3: jitter de tamanho, rotação e posição. |
| `size_opacity_section.py` | Seção 1: tamanho, opacidade, mesclagem e estabilizador. |
| `tip_geometry_section.py` | Seção 2: forma, dureza, ângulo e proporção da ponta. |
| `brush_engine_writer.py` | `BrushEngineWriter`: escreve os parâmetros avançados no motor, lê o perfil e as miniaturas, carrega textura do disco. |
| `non_scroll_combo_box.py` | `NonScrollComboBox`: combo que não troca de valor com a roda do mouse. |
| `panel_thumbnails.py` | Miniaturas padrão de ponta e de grão para as seções sem textura carregada. |
| `texture_file.py` | Leitura de uma imagem do disco como textura de pincel (RGBA8888). |

## Regras

- Controle novo usa os construtores da base (`quick_slider`, `engine_slider`,
  `engine_check`...): a seção já sabe mostrá-lo a partir do estado ou do
  perfil do motor.
- Parâmetro que passar a ter uma segunda tela vira `BrushParam` (controle
  rápido), nunca cópia sincronizada à mão.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
- `ui/core/state`
- `ui/core/widgets`
- `ui/core/widgets/slider`
- `ui/infrastructure/i18n`
<!-- /arccc:deps -->
