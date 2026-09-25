# `ui/plugins/panels/geometry_plugin/assets/` — ícones do seletor de geometria

**Responsabilidade:** os ícones de cada régua e de cada simetria no popup do seletor.

## Porta de entrada

`components/geometry_selector.py` carrega `ruler_<tipo>.svg` e `symmetry_<modo>.svg` desta pasta.

## Regras

- O nome do arquivo segue a chave do tipo (`GuideType`) ou do modo de simetria; tipo novo precisa do ícone com o mesmo nome.
