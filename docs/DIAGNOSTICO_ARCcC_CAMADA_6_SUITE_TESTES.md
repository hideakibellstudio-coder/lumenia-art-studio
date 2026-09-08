# 🏛️ DIAGNÓSTICO ARCcC v2: CAMADA 6 (SUÍTE DE TESTES AUTOMATIZADOS)
## *Raio-X de Coesão, Densidade de Código e Guardrails da Suíte de Testes do Lumenia*

---

## 🧭 1. RESUMO EXECUTIVO & CENSO ESTRUTURAL

Após a homologação completa das Camadas 1 a 5, a **Camada 6 (Suíte de Testes Automatizados)** constitui a muralha de defesa e garantia de qualidade do **Lumenia Art Studio & Aladyn Engine**. Ela é responsável por assegurar a estabilidade de todos os contratos de API, fiação de interface, precisão de renderização de pixels e integridade arquitetural do sistema.

Sob a metodologia **ARCcC v2**, o código de teste é código de produção de primeira classe e deve submeter-se aos mesmos limites rigorosos de anti-entropia, responsabilidade única e teto de tamanho ($< 500\text{ LOC}$, com alvo $< 300\text{ LOC}$).

### Censo Quantitativo de Arquivos (`tests/`):
- **Total de Arquivos Analisados**: 40 arquivos Python.
- **Volume Total de Código**: 5.495 linhas de código (LOC).
- **Média por Arquivo**: 137,4 LOC (excelente granularidade atômica).
- **Violações Mecânicas do Teto ($\ge 500\text{ LOC}$)**: **0 (ZERO) arquivos**.
- **Zona de Alerta Vermelha ($450 \text{ a } 499\text{ LOC}$)**: **1 arquivo** (2,5% do total).
- **Zona Amarela de Atenção ($300 \text{ a } 449\text{ LOC}$)**: **0 arquivos**.
- **Zona Verde Segura ($< 300\text{ LOC}$)**: **39 arquivos** (97,5% do total).

---

## 🚨 2. DIAGNÓSTICO DA ZONA VERMELHA ($450 - 499\text{ LOC}$)

| Arquivo | LOC | Testes Internos | Diagnóstico & Domínios Acumulados |
|---|:---:|:---:|---|
| **`tests/test_dialogs_i18n.py`** | **493** | 13 testes unitários de internacionalização | **Risco Imediato (a 7 LOC do teto de 500).** Acumula testes de re-tradução dinâmica de diálogos modais de sistema (Dock settings, Floating toolbar, Theme, Render, Cursores, Atalhos, Telemetria, Menubar) E testes de ferramentas do canvas / plugins (Secondary Toolbar, Submenus de Formas/Transformações, Painel de Geometria e Diálogo de Snapping/Curvilínea). |

---

## ⚠️ 3. DIAGNÓSTICO QUALITATIVO & POLUIÇÃO DE WARNINGS

### Anomalia 1: Risco Iminente de Ruptura em `test_dialogs_i18n.py`
O arquivo `test_dialogs_i18n.py` possui 493 linhas. Qualquer inclusão de um novo diálogo ou ferramenta no estúdio empurraria o arquivo instantaneamente para a violação do teto de 500 LOC. Além disso, ele viola a separação de domínio testando diálogos centrais do sistema operacional juntamente com opções secundárias de pintura vetorial e geometria 3D.

### Anomalia 2: Falsos Positivos de Descoberta no Pytest (`PytestCollectionWarning`)
Durante cada execução de testes, o pytest emite warnings:
```
PytestCollectionWarning: cannot collect test class 'TestReportDialog' because it has a __init__ constructor
PytestCollectionWarning: cannot collect test class 'TestRunnerThread' because it has a __init__ constructor
```
Isso ocorre porque as classes UI de relatório de testes iniciam com o prefixo `Test*`. A convenção canônica do pytest exige definir explicitamente `__test__ = False` em classes que não sejam casos de teste para manter a suíte 100% livre de ruído.

### Anomalia 3: Ausência de Guardrail Automatizado de Teto de LOC nos Testes de Invariantes
O arquivo `tests/test_arccc_architecture_invariants.py` já valida isolamento entre plugins, ausência de imports diretos de C++ e contratos de backend, mas ainda não possui um teste automatizado contínuo que impeça a inclusão de arquivos $\ge 500\text{ LOC}$ em qualquer diretório do projeto (`ui/`, `plugins/`, `tests/`).

---

## 🎯 4. METAS ESTRUTURAIS DE ELEVAÇÃO DA CAMADA 6

1. **Descomprimir `test_dialogs_i18n.py` (493 LOC $\rightarrow$ ~260 LOC)**:
   - Extrair a suíte de ferramentas e réguas para `tests/test_toolbars_geometry_i18n.py` (~235 LOC).
   - Ambos os arquivos passarão a residir confortavelmente na **Zona Verde Segura (< 300 LOC)**.
2. **Eliminar 100% dos Warnings de Coleta**:
   - Anotar `TestReportDialog` e `TestRunnerThread` com `__test__ = False`.
3. **Implantar Guardrail CI de Teto Estrito de LOC**:
   - Adicionar `test_05_strict_loc_ceiling_compliance` em `test_arccc_architecture_invariants.py` para garantir perenemente que nenhum arquivo Python do repositório ultrapasse 500 LOC.
4. **Homologação e Paridade Multi-Workspace**:
   - Executar suíte completa de testes e manter sincronização idêntica entre Primary e Mirror.
