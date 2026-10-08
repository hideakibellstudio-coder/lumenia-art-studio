# `engine/infrastructure/crash/` — minidump de queda

**Responsabilidade:** quando o processo cai por uma exceção não tratada (acesso inválido no motor, falha do Qt), gravar um minidump do Windows numa pasta de relatórios. Não decide se o relatório sai da máquina: isso é do diagnóstico da interface (`ui/infrastructure/diagnostics/`), com o consentimento do usuário.

## Porta de entrada

`CrashHandler.hpp` (`installCrashHandler`, `writeDiagnosticDump`), exposto por `bridge/core/bindings/bind_runtime.cpp`.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `CrashHandler.hpp` / `CrashHandler.cpp` | `SetUnhandledExceptionFilter` + `MiniDumpWriteDump` (pilhas, threads e a memória que elas apontam; sem os tiles do canvas). Devolve "continue a busca": o `faulthandler` do Python e o Windows Error Reporting continuam valendo. Fora do Windows, não faz nada. |

## Regras

- O filtro não aloca memória: o caminho da pasta é guardado na instalação.
- O dump só serve com o PDB do mesmo build: `scripts/build_native.py --pdb` grava o PDB fora da árvore, junto do `native-build.json`.

## Dependências internas

Medidas pelo teste `tests/test_arccc_package_docs.py` (`#include` e `import`):
dependência nova entre pastas entra nesta lista no mesmo commit.

<!-- arccc:deps -->
(nenhuma dependência interna)
<!-- /arccc:deps -->
