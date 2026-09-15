# 📚 Documentação Técnica — Lumenia Art Studio & Aladyn Engine

Bem-vindo à documentação técnica oficial e unificada do **Lumenia Art Studio** e do motor de pintura nativo **ALADYN ENGINE**.

Esta documentação foi integralmente reescrita e alinhada com o estado real, atual e testado do código-fonte, servindo como referência canônica para arquitetura, contratos, especificações de formato, gestão de cor e rotinas de compilação.

---

## 🗺️ Mapa de Navegação da Documentação

### 🏛️ 1. Arquitetura e Engenharia de Software
- [**ARCcC Framework (`architecture/ARCcC_FRAMEWORK.md`)**](architecture/ARCcC_FRAMEWORK.md): Princípios da Componentização Atômica Recursiva por Contrato, teto estrito de complexidade ($\le 450$ linhas de código por arquivo), desacoplamento por mixins e invariantes estruturais.
- [**Visão Geral do Sistema (`architecture/SYSTEM_OVERVIEW.md`)**](architecture/SYSTEM_OVERVIEW.md): Arquitetura macro em camadas, Shell Qt (PySide6), orquestração MDI multi-documento e ciclo de vida da aplicação.
- [**ALADYN Engine & PyBind11 Bridge (`architecture/ALADYN_ENGINE_AND_BRIDGE.md`)**](architecture/ALADYN_ENGINE_AND_BRIDGE.md): Motor C++20 de alto desempenho, `PaintEngineFacade`, `LayerStack`, `StrokeOrchestrator`, estabilização dinâmica de traço e contratos de ligação via PyBind11.
- [**Modelo de Documento e Histórico (`architecture/DOCUMENT_MODEL.md`)**](architecture/DOCUMENT_MODEL.md): Estrutura de dados `Document`, gerenciamento de camadas `LocalLayerManager`, histórico transacional atômico, scratch disk paginado e vinculação de identidades nativas.
- [**Subsistema de Plugins (`architecture/PLUGIN_SUBSYSTEM.md`)**](architecture/PLUGIN_SUBSYSTEM.md): Arquitetura extensível, descoberta dinâmica, manifesto de permissões, isolamento de workspaces e governança de ativação/rollback.

### 📐 2. Especificações Formais
- [**Especificação do Container LMN (`specifications/LMN_CONTAINER_SPEC.md`)**](specifications/LMN_CONTAINER_SPEC.md): Especificação completa do formato de arquivo nativo `.lmn` (versão 2+), estrutura ZIP, schema do `manifest.json`, migrações (v0 $	o$ v1 $	o$ v2), compressão de payloads e tolerância a falhas.
- [**Sistema de Gestão de Cor LittleCMS (`specifications/COLOR_MANAGEMENT_SPEC.md`)**](specifications/COLOR_MANAGEMENT_SPEC.md): Integração com LittleCMS 2.18, suporte a perfis ICC arbitrários externos, pipeline de Soft-Proofing (CMYK/RGB), alerta de gamut, exportação com metadados e blueprint da transição para 16-bit/float.

### 🛠️ 3. Guias Práticos
- [**Guia do Desenvolvedor (`guides/DEVELOPER_GUIDE.md`)**](guides/DEVELOPER_GUIDE.md): Configuração de ambiente de desenvolvimento no Windows, dependências, convenções de código e fluxo de trabalho com o ARCcC Navigator.
- [**Testes Automatizados e Qualidade (`guides/TESTING_AND_QUALITY.md`)**](guides/TESTING_AND_QUALITY.md): Como executar os 390 testes automatizados, suítes de regressão de histórico/I/O, fuzzing do leitor de arquivos e benchmarks de renderização.
- [**Compilação e Distribuição Comercial (`guides/BUILD_AND_RELEASE.md`)**](guides/BUILD_AND_RELEASE.md): Compilação do motor C++20 via MSVC, geração do executável autônomo portátil via Nuitka, assinatura/manifesto SHA-256 e geração do instalador oficial Inno Setup.

### 📋 4. Governança e Auditoria
- [**Relatório de Encerramento das Auditorias (`audit/AUDIT_CLOSURE_REPORT.md`)**](audit/AUDIT_CLOSURE_REPORT.md): Matriz executiva de resolução definitiva das 16 não-conformidades de auditoria (F-001 a F-016), evidenciando testes e garantias arquiteturais.

---

## ⚡ Números e Métricas da Base de Código

- **Linguagens**: C++20 (Motor de renderização) e Python 3.11+ / PySide6 (UI, Orquestração e Ferramentas).
- **Cobertura de Testes**: **390/390 testes aprovados (100% GREEN)**.
- **Zona Vermelha de Complexidade**: **0 arquivos com $\ge 450$ linhas de código**.
- **Performance de Traço**: Latência $< 1.5\text{ms}$ por evento de entrada com estabilização cinemática ativa.
- **Formato de Arquivo**: Container ZIP seguro com integridade transacional e recovery em background.\n