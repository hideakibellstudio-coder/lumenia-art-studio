# `bridge/infrastructure/` — conversão, validação e erros da ponte

**Responsabilidade:** o que a ponte faz na fronteira Python ↔ C++ e que não é
binding de uma função do motor: validar e copiar buffers de pixels, e a
política de tradução de erros. Criada em 2026-09-25 (ARCcC multi-pilar: cada
pilar tem `infrastructure/`); até então o `BufferContract.hpp` morava entre os
bindings.

## Porta de entrada

`BufferContract.hpp` (incluído pelos bindings em `../core/bindings/`).

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `BufferContract.hpp` | Validação de dimensões e tamanho de buffers RGBA/cinza antes de chegar ao motor, e cópia imutável dos pixels que voltam ao Python. |
| `ContractVersion.hpp` | `kContractVersion`: a versão do contrato Python ↔ motor, exposta como `aladyn_engine_native.CONTRACT_VERSION`. Sobe quando o `.pyi` muda (`tests/test_bridge_contract_version.py` trava). |

## Regras

- Buffer vindo do Python passa por `BufferContract.hpp` antes de chegar ao
  motor (`tests/test_buffer_contract.py`).
- **Erros:** o motor só lança `std::invalid_argument` para entrada inválida, e
  o pybind11 a traduz para `ValueError`; buffer inválido também é
  `ValueError`. Binding não repete essa tradução com `try/catch` (o de
  `transform_rgba_for_profile` saiu em 2026-09-25).
  `tests/test_bridge_error_policy.py` confere. Exceção de outro tipo no motor
  é decisão nova: registre a tradução aqui.
- Não inclui o motor: só pybind11 e a biblioteca padrão.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py`: import novo entre
pastas entra nesta lista no mesmo commit (é decisão de arquitetura).

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
