# `ui/core/geometry/` — geometria compartilhada

**Responsabilidade:** tipos e cálculos de geometria que cruzam a fronteira com o motor: enums canônicos de guia e simetria (espelhos 1:1 dos enums C++), conversões por DPI e o dicionário que sincroniza guias com o motor.

## Porta de entrada

Importar por módulo: `guide_type.GuideType`, `symmetry_mode.SymmetryMode`, `dpi_calculator`, `synced_dict.SyncedDict`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `__init__.py` | Marca o pacote. |
| `dpi_calculator.py` | ui.core.geometry.dpi_calculator — Utilitário de Conversão e Métricas Físicas Baseadas em DPI. |
| `guide_type.py` | GuideType -- enum canonico para o tipo de regua/guia ativa. |
| `symmetry_mode.py` | SymmetryMode -- enum canonico para o modo de simetria ativo. |
| `synced_dict.py` | SyncedDict -- dict que sincroniza automaticamente com o motor nativo a cada mutacao. |

## Regras

Lei nº 4 do rio: modo de guia/simetria cruza a fronteira como enum daqui, nunca como string solta mapeada por dicionário no meio do caminho.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
