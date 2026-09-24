# `docs/02-arquitetura/` — arquitetura

**Responsabilidade:** como o sistema é dividido e como as partes conversam (ARCcC, motor e ponte, documento, plugins, contratos).

## Porta de entrada

`06-contratos-entre-componentes.md` para quem vai mexer em código; `01-framework-arccc.md` para a metodologia.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `01-framework-arccc.md` | Governança Arquitetural ARCcC (Atomic Recursive Componentization by Contract) |
| `02-visao-geral-do-sistema.md` | Visão Geral do Sistema (System Overview) |
| `03-motor-aladyn-e-bridge.md` | ALADYN ENGINE & PyBind11 Bridge |
| `04-modelo-de-documento.md` | Modelo de Documento e Histórico Transacional |
| `05-subsistema-de-plugins.md` | Subsistema de Plugins e Extensibilidade |
| `06-contratos-entre-componentes.md` | Contratos entre componentes — como as peças do Lumenia conversam |
| `07-auditoria-da-estrutura-fisica.md` | Auditoria da estrutura física contra o ARCcC (2026-09-24): medidas, o que já foi corrigido e o plano |

## Regras

- Documento novo entra na tabela acima (o teste `tests/test_arccc_package_docs.py` falha se não entrar).
- Número escrito aqui vem de comando rodado na sessão que escreveu (AGENTS.md, seção 5).
