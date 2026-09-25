# `bridge/` — pilar da ponte (PyBind11)

**Responsabilidade:** transformar a API pública do motor C++ no módulo Python `aladyn_engine_native`, com o contrato tipado que a UI consome.

Pilar 2 do ARCcC multi-pilar (`ui/` → `bridge/` → `engine/`): só serializa, converte tipos, valida buffers e expõe bindings — nenhuma regra de negócio.

## Porta de entrada

`core/bindings/engine_bindings.cpp` (`PYBIND11_MODULE(aladyn_engine_native, ...)`); contrato em `boundary/contracts/aladyn_engine_native.pyi`.

## Conteúdo

| Pasta | Responsabilidade |
|---|---|
| `boundary/` | Contrato tipado (`.pyi`) do módulo nativo. |
| `core/` | Os bindings PyBind11. |

## Regras

- Do motor, a ponte inclui só `engine/boundary/public-api/AladynEngine.hpp` (`tests/test_arccc_cxx_layers.py`).
- Função nova exposta ao Python: binding em `core/bindings/`, assinatura no `.pyi`, teste `tests/test_pyi_contract_matches_binary.py` verde.
- A UI só alcança o módulo por `ui/infrastructure/bridge_client/` (Lei nº 2 do AGENTS.md).

## Dívida conhecida (medida em 2026-09-25)

- Falta `infrastructure/` (ex.: mapeamento de erros nativo ↔ Python), que o ARCcC multi-pilar prevê; hoje a validação de buffers (`BufferContract.hpp`) lança `ValueError` direto nos bindings.
