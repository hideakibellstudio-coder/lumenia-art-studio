# Estado de encerramento da auditoria

O relatório original registra o estado encontrado em 09/09/2026. Esta matriz
acompanha o que foi corrigido sem confundir mitigação com implementação completa.

## Ordem de execução acordada em 10/09

A numeração identifica os achados; a gravidade P0/P1 do relatório é a original,
antes das correções. A fila abaixo considera o risco residual e as dependências.
Até aqui a execução alternou entre blocos sem uma fila registrada. A sequência
recente foi histórico estrutural (F-005), geometria (F-004) e buffers (F-007).

| Ordem | Achados | Objetivo de encerramento |
|---|---|---|
| 1 | F-009 | Paginação e restauração de histórico resistentes a falhas, sem aplicação parcial ou falso sucesso. |
| 2 | F-001 + F-013 | Persistir os estados/recursos restantes do documento com schema e migração. |
| 3 | F-002 + F-003 + F-005 | Fechar entradas fora de transações e validar identidade/hierarquia sistematicamente. |
| 4 | F-006 | Unificar política de cor, ICC e armazenamento de alta profundidade. |
| 5 | F-010 + F-011 | Capacidades explícitas e efeito verificável dos controles e ferramentas. |
| 6 | F-012 + F-014 | Lifecycle/rollback de plugins e contexto de atalhos. |
| 7 | F-015 + F-016 | Consolidar robustez, benchmarks e build/distribuição reproduzíveis. |

F-004, F-007 e F-008 estão corrigidos no escopo registrado. Os testes do F-015
acompanham todos os blocos. Mudanças nesta fila devem ser explicadas e registradas.

Em 11/09, F-006, F-010, F-011, F-012 e F-014 receberam as correções delimitadas
no status. A próxima posição da fila é **7 — F-015 + F-016**, sem alteração da
ordem acordada.

Nesta posição, a malha de qualidade e o build compatível foram reforçados. Os
gates restantes de distribuição e qualidade de release continuam registrados
nos limites de F-015/F-016, sem serem tratados como concluídos por testes locais.

## Correções desta rodada

- `.lmn`: reconstrução dos tipos de camada, incluindo grupo/filtro no índice zero;
  restauração de hierarquia, blend, seleção ativa e locks após carregar pixels.
- A reabertura verifica os pixels restaurados e descarta o novo documento se houver falha.
- Importar uma imagem cria um documento não salvo, sem usar a imagem original como caminho `.lmn`.
- Salvamento falha se o motor/payload estiver indisponível; arquivo completo é validado antes da substituição.
- Backup `.lmn.bak` guarda a geração anterior válida; manifesto e tamanhos ZIP são validados antes de alocar payloads.
- Configuração usa temporários exclusivos, fsync, backup, recuperação e sinal de falha visível na barra de status.
- Leitura/escrita de configuração não expõe listas/dicionários mutáveis; tipos estruturais inválidos são ignorados no carregamento.
- Recuperação periódica de documentos sujos, respeitando pinceladas em andamento, com trava por sessão e oferta de reabertura.
- Conteúdo do canvas marca o documento como alterado; Sair passa pelo fechamento com confirmação.
- Smudge da barra secundária usa `set_brush_param`; curva de potência de pressão altera a LUT nativa.
- `dispatch` executa comandos canônicos e rejeita tipos não suportados.
- Atalhos têm catálogo/registro central, aplicação no startup e no diálogo, desativação e validação de conflitos.
- Eliminadas duplicidades Ctrl+R/F12; preferências de undo são carregadas na criação do backend.
- Testes usam perfil temporário, separado das preferências/recovery do usuário real.
- Scratch disk e histórico paginado agora tratam offset zero como válido, validam tamanho/checksum dos blocos, preservam buffers em RAM até a gravação completa e abortam undo/redo corrompido sem mover o passo nem aplicar pixels parciais.

## Pendências que impedem declarar a auditoria inteira encerrada

| Achado | Situação e trabalho restante |
|---|---|
| F-001 | Corrigido para os recursos atuais do documento: LMN v2 conserva pixels, seleção de 8 bits, textura incorporada do papel com parâmetros/LUT, perfil atual, câmera, guias e simetria. Painel de papel atualiza o Document; troca de abas não substitui textura nem herda guias. Recovery considera backup válido e sessão encerrada abruptamente. Limites do formato registrados em DOCUMENT_FORMAT_V2.md; ICC real e pixels de alta profundidade continuam no F-006. |
| F-002 | **Corrigido no escopo do relatório.** Projeção Document ↔ motor é comparada antes e depois de cada `DocumentHistory` transaction; divergências locais fora do fluxo são rejeitadas no próximo comando e no salvamento. Menus, painel, delegate, filtros e drop usam o mesmo guard, com rollback completo em cancelamento/falha. |
| F-003 | **Corrigido no escopo do relatório.** APIs locais resolvem somente UID inteiro positivo (booleanos/índices ambíguos são rejeitados); `validate_integrity` verifica unicidade, ativo, pais, ciclos e grupos. `flatten_group` retorna sucesso real e achatar imagem tem guarda de progresso. |
| F-004 | Resolvido nesta fase: resize, crop com offset e image-resize com reamostragem aplicam-se na mesma instância nativa, preservando histórico anterior, seleção e contexto MDI; undo/redo restaura dimensões, pixels e seleção. |
| F-005 | **Corrigido no escopo do relatório.** Assinatura estrutural nativa inclui grupo/filtro/pai por índice e é validada junto aos snapshots COW/UID do `DocumentHistory`; operações estruturais de menu/painel/drop, previews de filtro e cancelamentos usam uma única linha de histórico. Permutações, merge, duplicate, flatten e rollback passaram no gate estrutural. |
| F-006 | Em andamento: os 14 IDs, metadados e transformações têm fonte única em `ColorProfileManager` C++; display, LOD e prévia Qt usam o mesmo buffer/transformador nativo, e IDs desconhecidos são rejeitados. Restam ICC arbitrário com intents/embutimento e armazenamento RGBA16/float; Deep Color atual melhora a composição, mas quantiza e persiste RGBA8. |
| F-007 | Resolvido em 10/09: todos os buffers dos bindings exportam snapshots imutáveis com proprietário Python; imagens de seleção/transformação também são independentes. Referências a parâmetros retêm a fachada. Entradas de pixels/texturas validam comprimento e limites antes do acesso nativo. Custo dos snapshots em documentos grandes permanece no gate de desempenho F-015. |
| F-008 | Resolvido nesta fase: `PaintEngineFacade` mantém geração global monotônica e invalida o mipmap em mutações de conteúdo, camadas, composição, seleção aplicada, transformações, canvas e traços. |
| F-009 | Resolvido em 10/09: escrita em scratch é transacional por passo, leitura valida tamanho e checksum, `setEnabled(false)` não destrói blocos existentes, e undo/redo aborta falhas de I/O/corrupção sem alterar pixels, IDs ou contabilização. A UI mostra falha real de histórico em vez de “Nada a desfazer/refazer”. Recuperação após morte do processo continua no bloco F-001/F-013, pois scratch é armazenamento temporário de sessão. |
| F-010 | Corrigido no escopo atual: `EngineBackend`, Aladyn e WGPU publicam capacidades efetivas; exportação, render e diagnóstico consultam esse contrato. Recursos não implementados continuam declarados como indisponíveis. |
| F-011 | Corrigido no escopo atual: schema central valida parâmetros de todas as ferramentas configuráveis; ambos os caminhos de UI usam chaves canônicas e os 33 presets chegam ao perfil nativo. |
| F-012 | Corrigido no escopo atual: manifesto versionado declara API mínima, dependências, permissões e integridade SHA-256 opcional; promoção inválida vai para quarentena. Ativação resolve dependências, compensa falhas e sempre executa cleanup. Painéis usam IDs explícitos e desconectam slots ao sair. Assinatura com chave confiável e sandbox de código externo pertencem ao trabalho de distribuição F-016. |
| F-013 | Corrigido no escopo desta fase: migrações explícitas LMN v0 → v1 → v2, tipos/dimensões/recursos validados e versões futuras rejeitadas. Configuração tem schema_version, normaliza perfis legados para IDs inteiros e aliases de velocidade/atraso; alterações inválidas de render são rejeitadas atomicamente. Configuração de versão futura não pode ser sobrescrita. Seleção do diálogo de gavetas usa itemData também ao carregar. |
| F-014 | Corrigido no escopo atual: o catálogo declara contexto de janela/canvas, edição textual recebe prioridade, comandos locais do canvas não são capturados por ações globais e o `InputRouter` usa o mapa efetivo após remapeamento ou desativação. |
| F-015 | Parcialmente corrigido: o runner Pytest tem cortes explícitos `smoke`, `contract`, `integration` e `stress`; o benchmark JSON mede startup, criação, traço, composição, LOD e memória nativa. O leitor `.lmn` recebe fuzz determinístico de truncamentos, bytes não-ZIP e mutações de manifesto. A suíte completa mede 81,35% de cobertura por ramos em `ui/core/document` e o CI exige 80%. Cobertura de mutação, corpus ampliado e gates de regressão de desempenho continuam abertos. |
| F-016 | Parcialmente corrigido: build C++20 usa `scalar` por padrão e AVX2 apenas sob escolha explícita; CI Windows 3.11–3.13 recompila, mede e testa o binário novo. `requirements-dev.lock` fixa toda a árvore Windows com hashes das rodas aceitas e o binário recebe metadados/sha256. O build portátil declara todos os recursos e gera manifesto SHA-256; o Inno não tem mais caminhos absolutos. Ainda faltam executar o release com instalador/assinatura e selecionar automaticamente a variante SIMD. |

Testes automáticos não substituem validação com tablets reais, múltiplos monitores,
DPI alto ou distribuição em uma máquina limpa. Esses gates continuam abertos.

## Validação da rodada

- Build MSVC C++20/PyBind11 com `--force`: concluído.
- `python tests/run_all_tests.py` em 10/09 após F-009: **suíte executiva completa aprovada sem falhas**, incluindo ownership/validação de buffers, conversão de textura, undo/redo geométrico, integração estrutural com o motor, falhas de scratch disk/histórico e encerramento sem suprimir falhas de limpeza.
- `python -m pytest tests/test_history_io_failures.py -q -o addopts=''`: **11 testes aprovados**, cobrindo I/O real, corrupção, truncamento, purge, disco cheio simulado e mensagem de falha de histórico.
- `git diff --check`: sem erros de whitespace; avisos de conversão LF/CRLF.
- A meta de execução inferior a 15 segundos do playbook de QA continua não atendida.
- Em 11/09, `scripts/build_native.py --simd scalar --force` recompilou a extensão
  com MSVC 14.44/C++20 sem `/arch:AVX2` e gravou `build/native-build.json` com
  o SHA-256 do artefato. Em seguida, `python tests/run_all_tests.py` foi aprovado
  integralmente sobre esse binário, incluindo as novas medições e a seleção de
  suítes F-015/F-016.
- Em 11/09, `python tests/run_all_tests.py --coverage` passou integralmente e
  registrou 81,35% de cobertura por ramos em `ui/core/document`; o CI passa a
  exigir o mínimo de 80% nesse limite de alto risco.

## Ferramentas e presets verificáveis — F-011 — 2026-09-10

- `ui.core.tool_settings` é a única fonte para defaults, tipos, limites e
  chaves canônicas de balde, conta-gotas, seleções, transformação, smudge,
  formas e texto. Eventos legados são lidos uma única vez e não voltam a ser
  propagados.
- Balde usa apenas `expand_px`; seleção usa `feather_px`/`aa`; transformação
  altera o controlador que efetivamente executa o commit. Varinha, seleção e
  transformação do painel lateral passaram a emitir seus sinais ao workspace.
- Formas e texto recebem configurações validadas antes de atualizar os seus
  controladores. Valores desconhecidos, tipos inválidos e valores fora da faixa
  mantêm o estado anterior válido.
- Presets agora aplicam também `min_size_percent` e `min_opacity_percent`. A
  matriz executa as 33 receitas, verifica o mini-motor e cada propriedade nativa
  publicada; a curva de pressão é comparada diretamente na LUT nativa.
- Contratos com spies verificam o encaminhamento de balde, conta-gotas,
  varinha, seleção retangular e transformação até as chamadas do backend.
