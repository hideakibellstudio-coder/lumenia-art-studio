# 📄 Modelo de Documento e Histórico Transacional

A integridade do documento do artista é a prioridade número um do Lumenia Art Studio. Para garantir que nenhuma arte seja corrompida por travamentos de hardware, exceções de memória ou interrupções, o sistema adota um modelo transacional estrito.

---

## 📐 1. Estrutura do Documento (`ui/core/document/document.py`)

A classe `Document` representa o estado completo da tela:
- **Metadados**: `uid`, `name`, `width`, `height`, `format_version`.
- **Árvore de Camadas**: `layer_manager: LocalLayerManager`.
- **Histórico Transacional**: `history: DocumentHistory`.
- **Canvas & Papel**: `paper_color`, `paper_visible`, `paper_texture_id`, `paper_texture_enabled`.
- **Guias & Simetria**: `guide_state`, `sym_state`.
- **Perfil de Cor ICC**: `color_profile_id`, `color_profile_name`, `color_profile_icc_bytes`, `soft_proof_state`.
- **Câmera Viewport**: `zoom`, `pan_x`, `pan_y`, `rotation`.

---

## 🌳 2. Gerenciador de Camadas Local (`LocalLayerManager`)

Localizado em `ui/core/document/layer_manager.py`:
- Modela nós de camada como instâncias de `LocalLayer` (`ui/core/document/local_layer.py`).
- **Identificadores Imutáveis**: Toda camada recebe um `uid` único (inteiro positivo crescente) no momento da criação, preservado por toda a vida útil do documento.
- **Validação de Integridade Estrutural**: O método `validate_integrity()` audita:
  - Unicidade dos UIDs.
  - Consistência de referências pai/filho (grupos).
  - Ausência de ciclos na árvore de camadas.
  - Existência válida da camada ativa selecionada.

---

## ⏪ 3. Histórico Transacional & Scratch Disk Paginado

Localizado em `ui/core/document/history.py`:
- **Projeção C++ $\leftrightarrow$ Python**: O método `bind_projection_identities(backend)` garante que para cada camada Python exista uma camada C++ correspondente com o exato mesmo UID e parâmetros. Se houver qualquer divergência de estrutura, a transação é abortada antes de causar corrupção de estado.
- **Scratch Disk Paginado**:
  - Passos de desfazer/refazer que envolvem buffers de alta resolução são paginados em blocos binários em disco temporário.
  - Cada bloco armazena tamanho e checksum de integridade.
  - O offset zero é tratado rigorosamente como válido.
  - Em caso de falha de I/O ou disco cheio, o sistema aborta o passo de forma limpa, preserva os buffers em memória RAM e emite notificação explícita na interface ("Falha ao gravar histórico: disco cheio").\n