# 🧪 Suíte de Testes Automatizados e Qualidade

O Lumenia possui uma malha rigorosa de testes automatizados com **647 testes unitários e de integração** (mais 10 subtests parametrizados), cobrindo todas as camadas críticas do sistema.

---

## 🚀 1. Executando os Testes

### Execução Completa da Suíte:
```powershell
python -m pytest
```
Tempo médio de execução: ~3m30s para os 647 testes (209.45s no último run completo, com rebuild nativo).

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

O leitor **nunca causa segmentation fault ou crash não tratado**, rejeitando os dados corrompidos com exceções limpas `DocumentFormatError`.\n