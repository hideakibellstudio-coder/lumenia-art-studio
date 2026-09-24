# 🧪 Suíte de Testes Automatizados e Qualidade

A contagem de testes muda a cada sessão; a fonte é o próprio pytest:
`python -m pytest --collect-only -q`. (Este documento dizia "647"; em
2026-09-22 eram 762; em 2026-09-23, 796.)

---

## 🚀 1. Executando os Testes

### Execução Completa da Suíte:
```powershell
python -m pytest
```
Tempo da suíte completa em 2026-09-22: ~110 s no Windows de desenvolvimento
(antes ~369 s; a queda veio de `tests/conftest.py` descartar janelas órfãs
entre módulos — `test_theme_system.py` sozinho levava ~220 s).

### Execução de Suítes Segmentadas:

- **Gestão de Cor LittleCMS (F-006)**:
  ```powershell
  python -m pytest tests/test_color_management_cms.py
  ```
  *9 testes em ~0.8s: valida transformações, perfis customizados, embutimento LMN e exportação.*

- **Histórico, Paginação e I/O de Falhas (F-009)**:
  ```powershell
  python -m pytest tests/test_history_io_failures.py
  ```
  *Valida disco cheio, truncamento de blocos e rollback seguro de memória.*

- **Formato de Arquivo LMN v2 e Migrações (F-001/F-013)**:
  ```powershell
  python -m pytest tests/test_document_v2.py tests/test_persistence_failures.py
  ```

- **Geometria, Resize e Canvas (F-004)**:
  ```powershell
  python -m pytest tests/test_geometry_history.py
  ```

- **Contratos de Build e Portabilidade (F-016)**:
  ```powershell
  python -m pytest tests/test_portable_build_contract.py
  ```

---

## 🛡️ 2. Fuzzing e Testes de Resiliência

O leitor de arquivos de projeto `.lmn` passa por testes de fuzzing determinístico (`tests/test_persistence_failures.py`), que injetam:
- Bytes aleatórios em headers ZIP.
- Arquivos corrompidos ou incompletos.
- Manifestos JSON com chaves ausentes, tipos incorretos ou referências circulares.
- Payloads de pixels com dimensões divergentes do cabeçalho.

O leitor **nunca causa segmentation fault ou crash não tratado**, rejeitando os dados corrompidos com exceções limpas `DocumentFormatError`.

---

## ⏳ 3. Portão de Sessão Longa e Detecção de Vazamentos (Gate P4)

A estabilidade de um aplicativo de pintura digital (como demonstrado pela literatura de engenharia do Krita e Blender) exige validação de longo curso para garantir que sessões prolongadas de trabalho não degradem a performance nem esgotem os recursos do sistema operacional.

No ambiente Windows/Qt, vazamentos clássicos decorrem de acúmulo de **GDI Objects** (limite rígido do Windows de 10.000 por processo), handles de SO órfãos e crescimento linear irrestrito de memória privada.

### 🎯 Critérios Formais de Aceitação do Gate P4

| Recurso Monitorado | Critério de Aprovação | Justificativa Técnica |
| :--- | :--- | :--- |
| **GDI Objects** (`GetGuiResources`) | **$\Delta \text{GDI} == 0$** (Tolerância Zero) | Vazamentos de `QPainter`, `QPixmap`, `HDC` causam travamento catastrófico no Windows. Devem estabilizar imediatamente após carregar a UI. |
| **OS Handles** (`GetProcessHandleCount`) | **crescimento $\le 5$** (queda não reprova) | Protege contra vazamento de threads, pipes ou eventos de sincronização. |
| **Memória Privada (Platô Estável)** | **Drift $\le 0.05$ MB/100 ciclos OU crescimento não significativo** (limite inferior do IC 95% da inclinação $\le 0$) | Com a aplicação inteira no ar, o alocador oscila ±1–3 MB entre amostras; o teto sozinho reprovaria ruído. Vazamento = inclinação acima do teto E estatisticamente positiva. (Revisado em 2026-09-22.) |

### 🧭 3.0 Qual script mede o quê (2026-09-22)

| Script | O que exercita | Serve para |
|---|---|---|
| `scripts/soak_full_session.py` | **MainWindow real** (offscreen) com plugins; traço + repaint do canvas, desfazer/refazer, criar/remover camadas pelo `LocalLayerManager`, salvar `.lmn`, abrir/fechar um 2º documento (MDI). Padrão: 3000 ciclos, aquecimento 1800. | **O gate de sessão longa.** |
| `scripts/run_soak_test.py` | Só o caminho do pincel nativo, **sem nenhum widget**, 1 documento, desfazer limitado a 30 passos. | Smoke test rápido do motor. Não prova ausência de vazamento na aplicação: o platô é garantido pelo anel de desfazer e GDI = 0 é trivial sem janelas. |

Medição de referência (2026-09-22, cenário completo, 2400 ciclos): a memória
privada sobe devagar até ~1800 ciclos (caches enchendo, curva que achata) e
fica plana depois (+0,05 ± 0,06 MB/100 ciclos entre 1800 e 2400). Handles e GDI
estáveis. Por isso o aquecimento padrão é 1800.

### 🤖 3.1 Bateria Automatizada Headless (`run_soak_test.py`)

Simula centenas de ciclos de pintura contínua, interpolação de pressão, variações de cor/tamanho/opacidade e ciclos de desfazer/refazer em modo offscreen (smoke test do motor, ver 3.0):

```powershell
# Execução padrão (350 ciclos, warmup de 180 ciclos, amostragem a cada 25):
python scripts/run_soak_test.py

# Execução profunda com exportação de telemetria CSV:
python scripts/run_soak_test.py --cycles 1000 --warmup 200 --output-csv soak_report.csv
```
*O script calcula automaticamente a regressão linear na fase pós-aquecimento e retorna código de saída `0` (Aprovado) ou `1` (Reprovado).*

### 🎨 3.2 Monitoramento e Análise de Sessão Real com Artista (`monitor_session.ps1`)

Para validação em sessões manuais de desenho:
1. **Durante a pintura:** Deixe o monitor rodando em um terminal em segundo plano:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/monitor_session.ps1 -IntervalSeconds 60
   ```
2. **Pós-sessão (Laudo Automático):** Avalie o arquivo CSV gerado contra os critérios do Gate:
   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/monitor_session.ps1 -Analyze "$env:USERPROFILE\lumenia_session.csv"
   ```
   *O analisador descarta o primeiro quartil de tempo (aquecimento), calcula o drift de MB/hora e emite o veredicto formal de estabilidade.*
\n