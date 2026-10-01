# `docs/01-correcao-da-base/` — fase de correção da base

**Responsabilidade:** o que falta corrigir, como verificar e como usar o ARCcC-Navigator nesta fase.

## Porta de entrada

`01-pendencias-atuais.md` — a lista viva de pendências.

## Arquivos

| Arquivo | Responsabilidade |
|---|---|
| `01-pendencias-atuais.md` | Pendências atuais da fase de correção da base |
| `02-simplificacao-da-ponte.md` | Simplificar a ponte UI → motor |
| `03-protocolo-do-navigator.md` | PROTOCOLO DE AGENTE — ARCcC-Navigator |
| `04-testes-e-qualidade.md` | Suíte de Testes Automatizados e Qualidade |
| `05-fluxo-lumenia-navigator.md` | Relatório: o fluxo Lumenia ↔ ARCcC-Navigator |
| `06-auditoria-orbital-decomposta.md` | Metodologia de Auditoria Orbital Descomposta (Concentric Satellite Peeling) |
| `07-analise-arccc-decomposta.md` | Análise ARCcC decomposta de 2026-09-26: cada nó do sistema medido, fluxos ponta a ponta, defeitos D1–D16, riscos R1–R11, prontidão para features, o plano de solidificação S0–S4 e a avaliação do estudo externo do motor (Apêndice F) |
| `08-analise-arccc-v1-1-e-forma-de-trabalho.md` | Análise de 2026-10-01 sob o ARCcC v1.1.0: o que a nova versão pede, medições novas (portas de entrada, superfície pública, mecanismos sem entrega, complexidade, multi-pilar, 7 portas), defeito D17, as 5 famílias de defeito, o laço de trabalho, regras de parada e os pontos de extensão registrados |

## Regras

- Documento novo entra na tabela acima (o teste `tests/test_arccc_package_docs.py` falha se não entrar).
- Número escrito aqui vem de comando rodado na sessão que escreveu (AGENTS.md, seção 5).
