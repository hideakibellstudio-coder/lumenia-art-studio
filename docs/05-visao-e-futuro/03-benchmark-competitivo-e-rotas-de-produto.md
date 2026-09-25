# Benchmark competitivo e rotas de produto

> **Documento direcionador da branch `feature/evolucao-produto`.**
> Reescrito em 2026-09-22. A versão de 2026-09-21 listava 15 "lacunas" sem
> conferir o código: 5 delas já existiam (total ou parcialmente) e 3 eram
> piores que lacunas -- a interface **promete** e não faz nada. Esta versão
> classifica cada item pelo que o código faz hoje, com evidência, e reordena o
> trabalho por esse critério.
> Relacionados: `01-visao-estrategica.md`, `../01-correcao-da-base/01-pendencias-atuais.md`.

---

## 1. Regras deste documento

1. **Nenhum item entra como "lacuna" sem busca no código.** Antes de escrever
   "falta X", procure (Navigator `navigator_search`/`navigator_context`, ou
   `grep`). Se o motor já tem o algoritmo, a tarefa é ligar a UI a ele -- nunca
   reimplementar (Lei do Leito do Rio nº 2).
2. **A interface não promete o que o motor não faz.** Item de menu, opção de
   combo ou nome de painel sem comportamento real é defeito, não lacuna, e vem
   antes de qualquer feature nova (Rota 0).
3. **Um rio por vez**, do início ao fim, com teste de ponta a ponta.
4. **Números medidos, não adjetivos.** "725 testes" e "100% Zona Verde" já
   foram escritos aqui sem medição e estavam errados. Cite o comando e a data.

Legenda de status: **EXISTE** · **PARCIAL** · **PROMESSA FALSA** (a UI oferece,
nada acontece) · **NÃO EXISTE** · **DECISÃO** (depende de escolha de produto).

---

## 2. O que a branch entregou até 2026-09-22 (fora das rotas originais)

Nenhum dos 15 itens do documento anterior foi feito; o trabalho foi para:

| Entrega | Commits |
|---|---|
| Gravação de traços / timelapse (MP4 via ffmpeg do sistema, ou ZIP), marca d'água, 24/30/60 FPS, barra flutuante, guias na captura | `e2a325b` → `dd52e75` |
| Cursores: chevron de precisão, anel tracejado da borracha, alto contraste "camaleão", inversão para destros | `3aeadd1`, `b77bb60` |
| Pan com Espaço + clique | `334a709` |
| Escala da interface 80–200% (reativa em barras e abas) | `1538b0f`, `f4cb66b` |
| Tela cheia F11, menus Exibir/Janela, catálogo de atalhos | `50652a8` |

Observação: o MP4 depende de `ffmpeg` no PATH do usuário -- o instalador não o
traz, então para a maioria dos artistas a exportação cai em ZIP. Decidir se o
instalador passa a incluir o ffmpeg (dezenas de MB; exige escolher um build
de licença compatível, LGPL em vez de GPL) ou se a UI deve
dizer claramente por que o MP4 não aparece.

---

## 3. Estado real de cada item (verificado no código em 2026-09-22)

### Rio 1 — Traço e pincel
| Item | Status | Evidência |
|---|---|---|
| Afunilamento (tapering) | **EXISTE** | `stroke_taper_enabled` (soltura) e `inkerParams.taperSmoothing` ("entrada/saída") em `BrushProfile.hpp`; checkbox no painel avançado. Falta só validar com artista se a entrada precisa de controle próprio. |
| Curva de pressão | **PARCIAL** | `ui/core/screens/curve_window.py` edita curvas Bézier de tamanho/fluxo por pressão e velocidade, por pincel. Falta a **calibração global do artista** (mão leve/pesada) com área de teste. |
| Mistura úmida / coleta de cor | **PARCIAL** | Existe em motores específicos (`smudge.color_pickup`, `marker.solvent_wetness`, motor aquarela). Não existe coleta de cor para o pincel comum. |
| Esc descarta o traço em andamento | **NÃO EXISTE** | Esc só cancela a transformação (`input_router.py`). |
| Prévia do pincel no painel | **CORRIGIDO em 2026-09-22** | A função nativa `render_stroke_preview` tinha sumido na decomposição do facade de 2026-08-25; o painel mostrava uma aproximação vetorial havia 4 semanas. Restaurada em `StrokePreviewRenderer.cpp`. |

### Rio 2 — Câmera, viewport e ambiente
| Item | Status | Evidência |
|---|---|---|
| Modo "canvas limpo" (Tab) | **NÃO EXISTE** | F11 (tela cheia) cobre parte; esconder painéis com uma tecla, não. |
| Enquadrar / zerar rotação | **EXISTE** (via menu) | Exibir → Ajustar à Tela, Resetar Rotação. Duplo clique no canvas é usado para fechar o laço, então não serve de atalho aqui. |
| Aviso rápido "Desfazer: Traço" (toast) | **NÃO EXISTE** | Os itens Desfazer/Refazer já ficam cinza quando não há o que fazer (desde 2026-09-20). |

### Rio 3 — Camadas
| Item | Status | Evidência |
|---|---|---|
| Solo (Alt+clique no olho) | **NÃO EXISTE** | — |
| Renomear na própria linha | **EXISTE** | Duplo clique no nome abre um campo sobre a linha (`panel_rename_popup.py`). |
| Nova camada sem diálogo | **EXISTE** | `Ctrl+Shift+N` → `create_new_layer`, sem janela. |
| Mesclar abaixo em `Ctrl+E` | **DECISÃO** | Hoje `Ctrl+E` = Exportar e mesclar abaixo = `Ctrl+Shift+E`. Photoshop e Krita usam `Ctrl+E` para mesclar abaixo. Trocar ajuda quem vem deles e muda o que já está no catálogo de atalhos. |

### Rio 4 — Seleção e transformação
| Item | Status | Evidência |
|---|---|---|
| Expandir / Contrair / Suavizar seleção | **EXISTE** (2026-09-23) | `engine/core/selection/SelectionMorphology.cpp`: expandir/contrair por transformada de distância euclidiana exata (custo não depende do raio, borda antisserrilhada, esmaecido preservado) e suavizar por desfoque gaussiano (sigma = raio/2). Borda da tela não contrai. Entra no Desfazer (transação estrutural). `tests/test_selection_modify.py`. |
| Distorcer / perspectiva na Transformação | **EXISTE** (2026-09-23) | Modo "Distorcer" (painel e barra secundária): cada canto vai para onde é arrastado; lados movem dois cantos; o quad nunca dobra. Commit por homografia no motor (`TransformEngineDistort.cpp`), prévia por `QTransform.quadToQuad` -- o teste confere que os dois levam o mesmo ponto ao mesmo lugar. O laço de amostragem virou `transform/InverseMappedComposite.hpp`, compartilhado com o modo livre. `tests/test_transform_distort.py`. |
| Tolerância da varinha arrastando | **PARCIAL** | A tolerância existe como controle na barra de opções; ajustar arrastando sobre o canvas, não. |

### Rio 5 — Cor
| Item | Status | Evidência |
|---|---|---|
| Harmonias na roda | **EXISTE** (2026-09-23) | Complementar, análogas, tríade, complementar dividida e quadrado: marcas no anel da roda + amostras clicáveis; a regra é lembrada entre sessões (`color.harmony`). `ui/core/widgets/color_picker/harmony.py`, `tests/test_color_harmony.py`. |
| Trocar primária/secundária | **PARCIAL** | Clique no seletor sobreposto troca (`swap_colors`); a tecla `X` não existe. |
| Cores recentes | **PARCIAL** | `RecentColorsWidget` guarda a cor quando ela é escolhida na roda; não registra sozinho ao pintar. |

---

## 4. Ordem de trabalho

### Rota 0 — Cumprir o que a interface já promete — **CONCLUÍDA em 2026-09-23**
As três promessas falsas (Modificar seleção, Distorcer, Harmonias) viraram
funções reais -- decisão do dono do produto: "deixar de prometer e desenvolver
a função real". Ver as linhas da tabela acima.

### Rota C — Comercial (P0: bloqueia venda) — registrada em 2026-09-25
Do relatório de estado de 2026-09-25. O motor de pintura não é o gargalo; o
que impede vender é troca de arquivos e distribuição. A engenharia sem
feature que vem junto (build com MSVC, versão única, avisos de licença de
terceiros, registro de quedas) está em
`../01-correcao-da-base/01-pendencias-atuais.md`, "Próximas tasks".

| # | Item | Status | Evidência (2026-09-25) |
|---|---|---|---|
| C1 | Exportar PSD com camadas; depois importar | **NÃO EXISTE** | Só sai PNG/JPEG achatado. É o formato de entrega da indústria. |
| C2 | Assinatura digital do instalador | **NÃO EXISTE** | Sem ela o SmartScreen avisa "app desconhecido" para todo cliente. Exige certificado (custo). |
| C3 | Relatório de falhas | **PARCIAL** | Log rotativo e `sys.excepthook` existem; nada sai da máquina. Enviar exige consentimento (a EULA promete não coletar a arte). |
| C4 | Atualização automática | **NÃO EXISTE** | Cliente só atualiza baixando o instalador de novo. |
| C5 | Licença e canal de venda | **DECISÃO** | Sem ativação, loja nem página. |
| C6 | ffmpeg | **DECISÃO** | Embutir no instalador ou explicar na UI (seção 2). |

### Rota 1 — Ganhos rápidos (pouco código, uso diário)
Tecla `X` para trocar cores · `Esc` descarta o traço em andamento · cores
recentes registradas ao pintar · Solo de camada · aviso rápido de
Desfazer/Refazer · `Tab` para canvas limpo. *Conferido em 2026-09-25: nenhum
dos seis foi feito.*

### Rota 2 — Médio prazo
Calibração global de pressão (reaproveitar `curve_window` + curva global
aplicada antes das curvas por pincel) · tolerância da varinha arrastando.

### Rota 3 — Motor
Coleta de cor (mistura úmida) para o pincel comum · pipeline de cor 16-bit
(`02-pipeline-de-cor-16bit.md`) -- **adiado por decisão (2026-09-23)**: mexe no
formato de tile, compositor, desfazer e arquivo; fica para depois da Rota 1.

### Pendência de distribuição
ffmpeg no instalador (ver seção 2). Agora é o item C6 da Rota C.

### Paridade e posicionamento (registrados em 2026-09-25)
- **P1, paridade com Krita, Clip Studio e Photoshop:** máscara de camada (só
  existe máscara de recorte), camada de texto editável (hoje o texto vira
  pixels), ferramenta de gradiente, recorte (crop).
- **P2, posicionamento (DECISÃO):** animação, vetor e quadrinhos são o
  terreno do Clip Studio. Disputar, ou ficar no nicho "pintura rápida e leve,
  sem assinatura", como o SAI.

Ordem recomendada: build com MSVC verificado → C1 a C4 → qualidade dirigida
(pendências) → Rota 1 → P1.

---

## 5. Definição de pronto de cada item
- Caminho completo UI → `EngineBackend` → motor, sem `hasattr` novo
  (`tests/test_river_ratchets.py` barra guardas não aprovadas).
- Algoritmo no C++ quando for processamento de pixels; Python só liga.
- Teste que falha sem a mudança e passa com ela.
- Chaves de tradução nos 4 idiomas (`tests/test_i18n_keys_exist.py`).
- Nenhum arquivo ≥ 450 linhas; suíte completa verde; `navigator_verify` sem
  aumento de achados.
