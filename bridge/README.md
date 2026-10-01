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
| `infrastructure/` | Validação e cópia de buffers e a política de tradução de erros (desde 2026-09-25). |

## Regras

- Do motor, a ponte inclui só `engine/boundary/public-api/AladynEngine.hpp` (`tests/test_arccc_cxx_layers.py`).
- Função nova exposta ao Python: binding em `core/bindings/`, assinatura no `.pyi`, teste `tests/test_pyi_contract_matches_binary.py` verde.
- Mudou o `.pyi`? Suba `kContractVersion` (`infrastructure/ContractVersion.hpp`) e `EXPECTED_CONTRACT_VERSION` (`ui/infrastructure/bridge_client/contract_version.py`), recompile, e atualize os dois campos de `tests/golden/bridge_contract.json`. A interface recusa, na partida, um binário de outra versão.
- A UI só alcança o módulo por `ui/infrastructure/bridge_client/` (Lei nº 2 do AGENTS.md).

## Dívida conhecida (medida em 2026-09-25)

- Nenhuma registrada. `infrastructure/` existe desde 2026-09-25 (antes o
  `BufferContract.hpp` morava entre os bindings e a política de erros não
  estava escrita).
