# `bridge/boundary/contracts/` — contrato tipado do módulo nativo

**Responsabilidade:** descrever em Python (stubs `.pyi`) cada classe, enum e método que `aladyn_engine_native` expõe.

## Porta de entrada

`aladyn_engine_native.pyi`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `aladyn_engine_native.pyi` | Stub do módulo: `PaintEngineFacade` e funções livres; reexporta os tipos de `_types.pyi`. |
| `_types.pyi` | Tipos de fronteira (pontos, curvas, parâmetros de pincel, enums). |

## Regras

- `tests/test_pyi_contract_matches_binary.py` confere o stub contra o binário carregado: método no binário sem stub (ou o contrário) falha.
